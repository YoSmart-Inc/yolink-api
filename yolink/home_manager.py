"""YoLink home manager."""

import threading
from typing import Any
from .device import YoLinkDevice
from .client import YoLinkClient
from .auth_mgr import YoLinkAuthMgr
from .model import BRDP
from .mqtt_client import YoLinkMqttClient
from .message_listener import MessageListener
from .exception import YoLinkClientError


class HomeManager:
    """YoLink home manager."""

    _instance = None
    _lock = threading.Lock()
    _home_devices: dict[str, YoLinkDevice] = {}
    _http_client: YoLinkClient = None
    _mqtt_client: YoLinkMqttClient = None
    _message_listener: MessageListener = None

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
        return cls._instance

    async def async_setup(
        self, auth_mgr: YoLinkAuthMgr, listener: MessageListener
    ) -> None:
        """Init YoLink home."""
        if not auth_mgr:
            raise YoLinkClientError("-1", "auth_mgr is required")
        if not listener:
            raise YoLinkClientError("-2", "listener is required")
        self._http_client = YoLinkClient(auth_mgr)
        home_info: BRDP = await self.async_get_home_info()
        self._message_listener = listener
        self._mqtt_client = YoLinkMqttClient(auth_mgr)
        self._mqtt_client.connect(home_info.data["id"], self._message_listener)

    async def async_unload(self) -> None:
        """Unload YoLink home."""
        self._home_devices = {}
        self._http_client = None
        self._mqtt_client.disconnect()
        self._message_listener = None
        self._mqtt_client = None

    async def async_get_home_info(self, **kwargs: Any) -> BRDP:
        """Get home general information."""
        return await self._http_client.execute(
            {"method": "Home.getGeneralInfo"}, **kwargs
        )

    async def async_get_home_devices(self, **kwargs: Any) -> list[YoLinkDevice]:
        """Get home devices."""
        with self._lock:
            response: BRDP = await self._http_client.execute(
                {"method": "Home.getDeviceList"}, **kwargs
            )
            for _device in response.data["devices"]:
                self._home_devices[_device.device_id] = YoLinkDevice(
                    _device, self._http_client
                )
        return self._home_devices.values()

    def get_home_device(self, device_id: str) -> YoLinkDevice | None:
        """Get home device by device id."""
        return self._home_devices.get(device_id)
