"""YoLink home manager."""
from __future__ import annotations
from typing import Any
from .auth_mgr import YoLinkAuthMgr
from .client import YoLinkClient
from .device import YoLinkDevice, YoLinkDeviceMode
from .exception import YoLinkClientError
from .message_listener import MessageListener
from .model import BRDP
from .mqtt_client import YoLinkMqttClient


class YoLinkHome:
    """YoLink home manager."""

    def __init__(self) -> None:
        """Init YoLink Home Manager."""
        self._home_devices: dict[str, YoLinkDevice] = {}
        self._http_client: YoLinkClient = None
        self._mqtt_client: YoLinkMqttClient = None
        self._message_listener: MessageListener = None

    async def async_setup(
        self, auth_mgr: YoLinkAuthMgr, listener: MessageListener
    ) -> None:
        """Init YoLink home."""
        if not auth_mgr:
            raise YoLinkClientError("-1001", "setup failed, auth_mgr is required!")
        if not listener:
            raise YoLinkClientError(
                "-1002", "setup failed, message listener is required!"
            )
        self._http_client = YoLinkClient(auth_mgr)
        home_info: BRDP = await self.async_get_home_info()
        # load home devices
        await self.async_load_home_devices()
        # setup yolink mqtt connection
        self._message_listener = listener
        self._mqtt_client = YoLinkMqttClient(auth_mgr, self._home_devices)
        await self._mqtt_client.connect(home_info.data["id"], self._message_listener)

    async def async_unload(self) -> None:
        """Unload YoLink home."""
        self._home_devices = {}
        self._http_client = None
        await self._mqtt_client.disconnect()
        self._message_listener = None
        self._mqtt_client = None

    async def async_get_home_info(self, **kwargs: Any) -> BRDP:
        """Get home general information."""
        return await self._http_client.execute(
            {"method": "Home.getGeneralInfo"}, **kwargs
        )

    async def async_load_home_devices(self, **kwargs: Any) -> dict[str, YoLinkDevice]:
        """Get home devices."""
        response: BRDP = await self._http_client.execute(
            {"method": "Home.getDeviceList"}, **kwargs
        )
        for _device in response.data["devices"]:
            self._home_devices[_device["deviceId"]] = YoLinkDevice(
                YoLinkDeviceMode(**_device), self._http_client
            )
        return self._home_devices

    def get_devices(self) -> list[YoLinkDevice]:
        """Get home devices."""
        return self._home_devices.values()

    def get_device(self, device_id: str) -> YoLinkDevice | None:
        """Get home device via device id."""
        return self._home_devices.get(device_id)
