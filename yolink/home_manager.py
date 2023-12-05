"""YoLink home manager."""
from __future__ import annotations
import logging
from typing import Any
from .auth_mgr import YoLinkAuthMgr
from .client import YoLinkClient
from .const import (
    Endpoints,
    YOLINK_API_MQTT_BROKER,
    YOLINK_API_MQTT_BROKER_EU,
    YOLINK_API_MQTT_BROKER_PORT,
)
from .device import YoLinkDevice, YoLinkDeviceMode
from .exception import YoLinkInitializationError
from .message_listener import MessageListener
from .model import BRDP
from .mqtt_client import YoLinkMqttClient

_LOGGER = logging.getLogger(__name__)


class YoLinkHome:
    """YoLink home manager."""

    def __init__(self) -> None:
        """Init YoLink Home Manager."""
        self._home_devices: dict[str, YoLinkDevice] = {}
        self._http_client: YoLinkClient = None
        self._endpoints: set[Endpoints] = set()
        self._mqtt_clients: dict[Endpoints, YoLinkMqttClient] = {}
        self._message_listener: MessageListener = None

    async def async_setup(
        self, auth_mgr: YoLinkAuthMgr, listener: MessageListener
    ) -> None:
        """Init YoLink home."""
        _LOGGER.info("setting up yolink homeassistant integration.")
        if not auth_mgr:
            raise YoLinkInitializationError("setting up failed, auth_mgr is required!")
        if not listener:
            raise YoLinkInitializationError(
                "setting up failed, message listener is required!"
            )
        self._http_client = YoLinkClient(auth_mgr)
        home_info: BRDP = await self.async_get_home_info()
        # load home devices
        _LOGGER.info("loading devices from yolink.")
        await self.async_load_home_devices()
        _LOGGER.info("%d devices have been loaded.", len(self._home_devices))
        # setup yolink mqtt connection
        self._message_listener = listener
        for endpoint in self._endpoints:
            _LOGGER.info("[%s] setting up mqtt client.", endpoint.name)
            endpoint_host = (
                YOLINK_API_MQTT_BROKER_EU
                if endpoint == Endpoints.EU
                else YOLINK_API_MQTT_BROKER
            )
            endpoint_mqtt_client = YoLinkMqttClient(
                endpoint,
                endpoint_host,
                YOLINK_API_MQTT_BROKER_PORT,
                auth_mgr,
                self._home_devices,
            )
            await endpoint_mqtt_client.connect(
                home_info.data["id"], self._message_listener
            )
            _LOGGER.info("[%s] mqtt client connected.", endpoint.name)
            self._mqtt_clients[endpoint] = endpoint_mqtt_client

    async def async_unload(self) -> None:
        """Unload YoLink home."""
        self._home_devices = {}
        self._http_client = None
        for endpoint, mqtt_client in self._mqtt_clients.items():
            _LOGGER.info("[%s] mqtt connection shutting down.", endpoint.name)
            mqtt_client.disconnect()
            _LOGGER.info("[%s] mqtt client disconnected.", endpoint.name)
        self._mqtt_clients = None
        self._endpoints = None
        self._message_listener = None

    async def async_get_home_info(self, **kwargs: Any) -> BRDP:
        """Get home general information."""
        return await self._http_client.execute(
            endpoint=Endpoints.US, bsdp={"method": "Home.getGeneralInfo"}, **kwargs
        )

    async def async_load_home_devices(self, **kwargs: Any) -> dict[str, YoLinkDevice]:
        """Get home devices."""
        response: BRDP = await self._http_client.execute(
            endpoint=Endpoints.US, bsdp={"method": "Home.getDeviceList"}, **kwargs
        )
        for _device in response.data["devices"]:
            yolink_device = YoLinkDevice(YoLinkDeviceMode(**_device), self._http_client)
            self._endpoints.add(yolink_device.endpoint)
            self._home_devices[_device["deviceId"]] = yolink_device
        return self._home_devices

    def get_devices(self) -> list[YoLinkDevice]:
        """Get home devices."""
        return self._home_devices.values()

    def get_device(self, device_id: str) -> YoLinkDevice | None:
        """Get home device via device id."""
        return self._home_devices.get(device_id)
