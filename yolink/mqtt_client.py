"""YoLink mqtt client."""

import asyncio
import logging
from typing import Any

from aiomqtt import Client, MqttError, ProtocolVersion
from pydantic import ValidationError

from .auth_mgr import YoLinkAuthMgr
from .device import YoLinkDevice
from .message_listener import MessageListener
from .model import BRDP
from .message_resolver import resolve_sub_message
from .endpoint import Endpoint
from .local_auth_mgr import YoLinkLocalAuthMgr

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
        self._topic = topic
        self._message_listener = listener
        self._listener_task = asyncio.create_task(self._listen())

    async def _listen(self):
        # check and fresh access token
        await self._auth_mgr.check_and_refresh_token()
        reconnect_interval = 30
        self._running = True
        _username = ""
        _password = ""
        if isinstance(self._auth_mgr, YoLinkLocalAuthMgr):
            _password = self._auth_mgr._client_secret
            _username = self._auth_mgr._client_id
        else:
            _username = self._auth_mgr.access_token()
        while self._running:
            try:
                async with Client(
                    hostname=self._broker_host,
                    port=self._broker_port,
                    username=_username,
                    password=_password,
                    keepalive=60,
                    protocol=ProtocolVersion.V311,
                ) as client:
                    _LOGGER.info(
                        "[%s] connecting to yolink mqtt broker.", self._endpoint.name
                    )
                    if self._topic is not None:
                        await client.subscribe(self._topic)
                        _LOGGER.info(
                            "[%s] yolink mqtt client connected.", self._endpoint.name
                        )
                    async for message in client.messages:
                        self._process_message(message)
            except MqttError:
                _LOGGER.error(
                    "[%s] yolink mqtt client disconnected!",
                    self._endpoint.name,
                    exc_info=True,
                )
                await asyncio.sleep(reconnect_interval)
                # validate token before reconnecting
                await self._auth_mgr.check_and_refresh_token()
            except Exception:
                _LOGGER.error(
                    "[%s] unexcept exception:", self._endpoint.name, exc_info=True
                )

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
                if msg_type not in [
                    "Report",
                    "Alert",
                    "StatusChange",
                    "getState",
                    "setState",
                    "DevEvent",
                    "waterReport",  # Sprinkler
                ]:
                    return
                device = self._devices.get(device_id)
                if device is None:
                    return
                paired_device_id = device.get_paired_device_id()
                if paired_device_id is not None:
                    paired_device = self._devices.get(paired_device_id)
                    if paired_device is None:
                        return
                    # post current device state to paired device
                    paired_device_state = {"state": msg_data.data.get("state")}
                    self.__resolve_message(paired_device, paired_device_state, msg_type)
                self.__resolve_message(device, msg_data.data, msg_type)
            except ValidationError:
                # ignore invalidate message
                _LOGGER.debug("Message invalidate.")

    def __resolve_message(
        self, device: YoLinkDevice, msg_data: dict[str, Any], msg_type: str
    ) -> None:
        """Resolve device message."""
        resolve_sub_message(device, msg_data, msg_type)
        if self._message_listener is not None:
            self._message_listener.on_message(device, msg_data)
