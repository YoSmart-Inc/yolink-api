"""YoLink Local Hub Client."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlsplit

from aiohttp import ClientSession

from .abstract_client import YoLinkClinet
from .const import ATTR_DEVICE_WATER_DEPTH_SENSOR
from .device import YoLinkDevice, YoLinkDeviceMode
from .devices import create_device
from .endpoint import Endpoint
from .exception import (
    YoLinkApiCode,
    YoLinkClientError,
    YoLinkConfigError,
)
from .http_client import YoLinkHttpClient
from .local_auth_mgr import YoLinkLocalAuthMgr
from .message_listener import MessageListener
from .model import BRDP
from .mqtt_client import YoLinkMqttClient

_LOGGER = logging.getLogger(__name__)

has_external_data_devices = [ATTR_DEVICE_WATER_DEPTH_SENSOR]


class YoLinkLocalClinet(YoLinkClinet):
    """YoLink Local Hub client."""

    def __init__(
        self,
        session: ClientSession,
        host: str,
        net_id: str,
        client_id: str,
        client_secret: str,
        *,
        mqtt_port: int = 18080,
    ) -> None:
        """Init YoLink Local Hub Client."""
        parsed = urlsplit(host if "://" in host else f"http://{host}")
        try:
            port = parsed.port
        except ValueError as err:
            raise YoLinkConfigError("Invalid Local Hub HTTP port") from err
        if (
            parsed.scheme not in ("http", "https")
            or not parsed.hostname
            or parsed.path not in ("", "/")
        ):
            raise YoLinkConfigError("Invalid Local Hub host")
        hostname = parsed.hostname
        url_host = f"[{hostname}]" if ":" in hostname else hostname
        base_url = f"{parsed.scheme}://{url_host}:{port if port is not None else 1080}"
        self._session = session
        self._net_id: str = net_id
        self._client_id = client_id
        self._client_secret = client_secret
        self._endpoint = Endpoint(
            name="Local",
            host=hostname,
            url=f"{base_url}/open/yolink/v2/api",
            mqtt_host=hostname,
            mqtt_port=mqtt_port,
        )
        self._auth_mgr = YoLinkLocalAuthMgr(
            session=session,
            token_url=f"{base_url}/open/yolink/token",
            client_id=client_id,
            client_secret=client_secret,
        )
        self._devices: dict[str, YoLinkDevice] = {}
        self._http_client: YoLinkHttpClient | None = None
        self._mqtt_client = None
        self._message_listener: MessageListener | None = None

    async def authenticate(self) -> bool:
        """Authenticate to Local Hub."""
        return await self._auth_mgr.check_and_refresh_token() is not None

    async def async_setup(self, listener: MessageListener) -> None:
        """Init YoLink Local Hub Client."""
        if not listener:
            raise YoLinkConfigError("setup failed, message listener is required!")
        if self._mqtt_client is not None:
            await self._mqtt_client.disconnect()
            self._mqtt_client = None
        self._http_client = YoLinkHttpClient(self._auth_mgr)
        await self.async_load_devices()
        self._message_listener = listener
        self._mqtt_client = YoLinkMqttClient(
            auth_manager=self._auth_mgr,
            endpoint=self._endpoint,
            broker_host=self._endpoint.mqtt_broker_host,
            broker_port=self._endpoint.mqtt_broker_port,
            devices=self._devices,
        )
        await self._mqtt_client.connect(
            f"ylsubnet/{self._net_id}/+/report", self._message_listener
        )

    async def async_unload(self) -> None:
        """Unload the Local Hub client."""
        _LOGGER.info("[Local] Unloading Hub client: host=%s", self._endpoint.host)
        self._devices = {}
        self._http_client = None
        if self._mqtt_client is not None:
            await self._mqtt_client.disconnect()
            self._mqtt_client = None
        self._message_listener = None
        _LOGGER.info("[Local] Hub client unloaded: host=%s", self._endpoint.host)

    async def async_load_devices(self, **kwargs: Any) -> dict[str, YoLinkDevice]:
        """Get sub-net devices."""
        if self._http_client is None:
            raise YoLinkConfigError(
                "load devices failed, http client is not initialized!"
            )
        response: BRDP = await self._http_client.execute(
            self._endpoint.url, bsdp={"method": "Home.getDeviceList"}, **kwargs
        )
        loaded_devices: dict[str, YoLinkDevice] = {}
        for device_data in response.data["devices"]:
            device = create_device(YoLinkDeviceMode(**device_data), self._http_client)
            if device is None:
                continue
            device.endpoint = self._endpoint
            if device.type in has_external_data_devices:
                await self._async_load_external_data(device)
            loaded_devices[device.id] = device
        self._devices.clear()
        self._devices.update(loaded_devices)
        _LOGGER.debug("[Local] Loaded devices: count=%s", len(self._devices))
        return self._devices

    async def _async_load_external_data(self, device: YoLinkDevice) -> None:
        """Load settings needed to interpret device data."""
        try:
            response = await device.get_external_data()
            device.attrs = response.data.get("extData")
        except YoLinkClientError as err:
            if err.code != YoLinkApiCode.UNSUPPORTED_METHOD:
                raise
            _LOGGER.debug(
                "[Local] getExternalData is not supported: device=%s type=%s",
                device.id,
                device.type,
            )

    def get_devices(self) -> list[YoLinkDevice]:
        """Get Local Hub sub-net devices."""
        return list(self._devices.values())

    def get_device(self, device_id: str) -> YoLinkDevice | None:
        """Get Local Hub sub-net device via device id."""
        return self._devices.get(device_id)
