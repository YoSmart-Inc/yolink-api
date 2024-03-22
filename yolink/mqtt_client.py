"""YoLink mqtt client."""

import asyncio
import logging
from typing import Any
import aiomqtt

try:
    from pydantic.v1 import ValidationError
except ImportError:
    from pydantic import ValidationError

from .auth_mgr import YoLinkAuthMgr
from .const import (
    ATTR_DEVICE_SMART_REMOTER,
    ATTR_DEVICE_WATER_DEPTH_SENSOR,
    ATTR_DEVICE_WATER_METER_CONTROLLER,
)
from .device import YoLinkDevice
from .message_listener import MessageListener
from .model import BRDP
from .message_resolver import (
    smart_remoter_message_resolve,
    water_depth_sensor_message_resolve,
    water_meter_sensor_message_resolver,
)

_LOGGER = logging.getLogger(__name__)


class YoLinkMqttClient:
    """YoLink mqtt client."""

    def __init__(
        self,
        auth_manager: YoLinkAuthMgr,
        endpoint: str,
        broker_host: str,
        broker_port: int,
        home_devices: dict[str, YoLinkDevice],
    ) -> None:
        self._auth_mgr = auth_manager
        self._endpoint = endpoint
        self._broker_host = broker_host
        self._broker_port = broker_port
        self._home_topic = None
        self._message_listener = None
        self._home_devices = home_devices
        self._running = False
        self._listener_task = None

    async def connect(self, home_id: str, listener: MessageListener) -> None:
        """Connect to yolink mqtt broker."""
        self._home_topic = f"yl-home/{home_id}/+/report"
        self._message_listener = listener
        self._listener_task = asyncio.create_task(self._listen())

    async def _listen(self):
        # check and fresh access token
        await self._auth_mgr.check_and_refresh_token()
        reconnect_interval = 5
        self._running = True
        while self._running:
            try:
                async with aiomqtt.Client(
                    hostname=self._broker_host,
                    port=self._broker_port,
                    username=self._auth_mgr.access_token(),
                    password="",
                    keepalive=50,
                ) as client:
                    _LOGGER.info(
                        "[%s] connecting to yolink mqtt broker.", self._endpoint
                    )
                    await client.subscribe(self._home_topic)
                    _LOGGER.info("[%s] yolink mqtt client connected.", self._endpoint)
                    async for message in client.messages:
                        self._process_message(message)
            except aiomqtt.MqttError as mqtt_err:
                _LOGGER.error(
                    "[%s] yolink mqtt client disconnected!",
                    self._endpoint,
                    exc_info=True,
                )
                await asyncio.sleep(reconnect_interval)
                if isinstance(mqtt_err, aiomqtt.MqttCodeError):
                    if mqtt_err.rc in [4, 5]:
                        _LOGGER.error(
                            "[%s] token expired or invalid, acquire new one.",
                            self._endpoint,
                        )
                        await self._auth_mgr.check_and_refresh_token()
            except Exception:
                _LOGGER.error("[%s] unexcept exception:", self._endpoint, exc_info=True)

    async def disconnect(self) -> None:
        """UnRegister listener"""
        if self._listener_task is None:
            return
        self._listener_task.cancel()
        self._listener_task = None
        self._running = False

    def _process_message(self, msg) -> None:
        """Mqtt on message."""
        _LOGGER.debug(
            "Received message on %s%s: %s",
            msg.topic,
            " (retained)" if msg.retain else "",
            msg.payload[0:8192],
        )
        keys = str(msg.topic).split("/")
        if len(keys) == 4 and keys[3] == "report":
            try:
                device_id = keys[2]
                msg_data = BRDP.parse_raw(msg.payload.decode("UTF-8"))
                if msg_data.event is None:
                    return
                msg_event = msg_data.event.split(".")
                msg_type = msg_event[len(msg_event) - 1]
                if msg_type not in ["Report", "Alert", "StatusChange", "getState"]:
                    return
                device = self._home_devices.get(device_id)
                if device is None:
                    return
                paired_device_id = device.get_paired_device_id()
                if paired_device_id is not None:
                    paired_device = self._home_devices.get(paired_device_id)
                    if paired_device is None:
                        return
                    # post current device state to paired device
                    paired_device_state = {"state": msg_data.data.get("state")}
                    self.__resolve_message(paired_device, paired_device_state)
                self.__resolve_message(device, msg_data.data)
            except ValidationError:
                # ignore invalidate message
                _LOGGER.debug("Message invalidate.")

    def __resolve_message(self, device: YoLinkDevice, msg_data: dict[str, Any]) -> None:
        """Resolve device message."""
        if device.device_type == ATTR_DEVICE_SMART_REMOTER:
            msg_data = smart_remoter_message_resolve(msg_data)
        if device.device_type == ATTR_DEVICE_WATER_DEPTH_SENSOR:
            msg_data = water_depth_sensor_message_resolve(msg_data, device.device_attrs)
        if device.device_type == ATTR_DEVICE_WATER_METER_CONTROLLER:
            msg_data = water_meter_sensor_message_resolver(msg_data)
        self._message_listener.on_message(device, msg_data)
