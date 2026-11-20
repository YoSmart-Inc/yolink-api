"""YoLink mqtt client."""

import asyncio
import logging
from typing import Any

from aiomqtt import Client, MqttError, ProtocolVersion
from pydantic import ValidationError

from .auth_mgr import YoLinkAuthMgr
from .device import YoLinkDevice
from .endpoint import Endpoint
from .exception import YoLinkError
from .local_auth_mgr import YoLinkLocalAuthMgr
from .message_listener import MessageListener
from .model import DeviceMessage

_LOGGER = logging.getLogger(__name__)


class YoLinkMqttClient:
    """YoLink mqtt client."""

    def __init__(
        self,
        auth_manager: YoLinkAuthMgr,
        endpoint: Endpoint,
        broker_host: str,
        broker_port: int,
        devices: dict[str, YoLinkDevice],
    ) -> None:
        self._auth_mgr = auth_manager
        self._endpoint = endpoint
        self._broker_host = broker_host
        self._broker_port = broker_port
        self._topic = None
        self._devices = devices
        self._message_listener = None
        self._running = False
        self._listener_task = None

    async def connect(self, topic: str, listener: MessageListener) -> None:
        """Connect to yolink mqtt broker."""
        if self._listener_task is not None and not self._listener_task.done():
            if topic != self._topic or listener is not self._message_listener:
                _LOGGER.warning(
                    "[%s] MQTT client is already running; new settings were ignored",
                    self._endpoint.name,
                )
            return
        self._topic = topic
        self._message_listener = listener
        self._listener_task = asyncio.create_task(self._listen())

    async def _check_and_refresh_token(self) -> tuple[str, str]:
        """Check and refresh token."""
        new_token = await self._auth_mgr.check_and_refresh_token()
        if isinstance(self._auth_mgr, YoLinkLocalAuthMgr):
            return self._auth_mgr._client_id, new_token
        else:
            return new_token, ""

    async def _listen(self):
        """Listen to yolink mqtt broker."""
        reconnect_interval = 30
        self._running = True
        while self._running:
            try:
                _LOGGER.debug(
                    "[%s] Starting MQTT connection: host=%s port=%s",
                    self._endpoint.name,
                    self._broker_host,
                    self._broker_port,
                )
                username, password = await self._check_and_refresh_token()
                async with Client(
                    hostname=self._broker_host,
                    port=self._broker_port,
                    username=username,
                    password=password,
                    keepalive=60,
                    protocol=ProtocolVersion.V311,
                ) as client:
                    if self._topic is not None:
                        await client.subscribe(self._topic)
                    _LOGGER.info(
                        "[%s] MQTT connected: host=%s port=%s",
                        self._endpoint.name,
                        self._broker_host,
                        self._broker_port,
                    )
                    async for message in client.messages:
                        try:
                            self._process_message(message)
                        except Exception:
                            _LOGGER.exception(
                                "[%s] failed to process MQTT message on %s",
                                self._endpoint.name,
                                message.topic,
                            )
            except (MqttError, YoLinkError) as err:
                _LOGGER.warning(
                    "[%s] MQTT connection failed; reconnecting in %ss: "
                    "host=%s port=%s error=%s code=%s",
                    self._endpoint.name,
                    reconnect_interval,
                    self._broker_host,
                    self._broker_port,
                    type(err).__name__,
                    getattr(err, "code", None),
                )
                await asyncio.sleep(reconnect_interval)
            except Exception:
                _LOGGER.exception(
                    "[%s] Unexpected MQTT failure; reconnecting in %ss",
                    self._endpoint.name,
                    reconnect_interval,
                )
                await asyncio.sleep(reconnect_interval)

    async def disconnect(self) -> None:
        """UnRegister listener"""
        if self._listener_task is None:
            return
        _LOGGER.info(
            "[%s] Stopping MQTT listener: host=%s port=%s",
            self._endpoint.name,
            self._broker_host,
            self._broker_port,
        )
        task = self._listener_task
        self._running = False
        task.cancel()
        try:
            await asyncio.wait({task})
            if not task.cancelled():
                task.result()
        finally:
            if task.done() and self._listener_task is task:
                self._listener_task = None
        _LOGGER.info(
            "[%s] MQTT listener stopped: host=%s port=%s",
            self._endpoint.name,
            self._broker_host,
            self._broker_port,
        )

    def _is_message_acceptable(self, eventType: str | None) -> bool:
        """Check if the message is acceptable."""
        if eventType is None:
            return False
        if eventType == "THSensor.DataRecord":
            return True
        eventTypeList = [
            "Report",
            "Alert",
            "StatusChange",
            "getState",
            "setState",
            "DevEvent",
            "waterReport",  # Sprinkler
        ]
        for event in eventTypeList:
            if eventType.endswith(event):
                return True
        return False

    def _process_message(self, msg) -> None:
        """Mqtt on message."""
        keys = str(msg.topic).split("/")
        if len(keys) == 4 and keys[3] == "report":
            try:
                device_id = keys[2]
                message_payload = DeviceMessage.model_validate_json(
                    msg.payload.decode("UTF-8")
                )
                _LOGGER.debug(
                    "[%s] MQTT message: device=%s event=%s retained=%s",
                    self._endpoint.name,
                    device_id,
                    message_payload.event,
                    msg.retain,
                )
                if not self._is_message_acceptable(message_payload.event):
                    return
                msg_event = message_payload.event.split(".")
                event_type = msg_event[len(msg_event) - 1]
                device = self._devices.get(device_id)
                if device is None:
                    return
                if isinstance(device, YoLinkDevice):
                    report_at = message_payload.data.get("reportAt")
                    device.update_last_report_at(
                        report_at if report_at is not None else message_payload.time
                    )
                self._process_paired_device(device, message_payload.data, event_type)
                self.__resolve_message(device, message_payload.data, event_type)
            except (ValidationError, UnicodeDecodeError) as err:
                _LOGGER.warning(
                    "[%s] Ignoring invalid MQTT message: topic=%s error=%s",
                    self._endpoint.name,
                    msg.topic,
                    type(err).__name__,
                )

    def _process_paired_device(
        self, device: YoLinkDevice, data: dict[str, Any], event_type: str
    ) -> None:
        """Forward the state to the paired device, if one is configured."""
        paired_device_id = device.get_paired_device_id()
        if paired_device_id is None:
            return
        paired_device = self._devices.get(paired_device_id)
        if paired_device is None:
            return
        self.__resolve_message(paired_device, {"state": data.get("state")}, event_type)

    def __resolve_message(
        self, device: YoLinkDevice, data: dict[str, Any], event_type: str
    ) -> None:
        """Resolve device message."""
        if isinstance(device, YoLinkDevice):
            device.resolve_message(data, event_type)
        if self._message_listener is not None:
            self._message_listener.on_message(device, data)
