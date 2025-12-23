"""YoLink Local Hub Client."""

from __future__ import annotations
import logging
from typing import Any
from .client import YoLinkClient
from .mqtt_client import YoLinkMqttClient
from .local_auth_mgr import YoLinkLocalAuthMgr
from .const import ATTR_DEVICE_WATER_DEPTH_SENSOR
from .device import YoLinkDevice, YoLinkDeviceMode
from .exception import YoLinkClientError, YoLinkUnSupportedMethodError
from .message_listener import MessageListener
from .model import BRDP
from .endpoint import Endpoint
from aiohttp import ClientSession

_LOGGER = logging.getLogger(__name__)

has_external_data_devices = [ATTR_DEVICE_WATER_DEPTH_SENSOR]


class YoLinkLocalHubClient:
    """YoLink Local Hub client."""

    def __init__(
        self,
        session: ClientSession,
        host: str,
        net_id: str,
        client_id: str,
        client_secret: str,
    ) -> None:
        """Init YoLink Local Hub Client."""
        self._session = session
        self._net_id: str = net_id
        self._client_id = client_id
        self._client_secret = client_secret
        self._endpoint = Endpoint(
            name="Local",
            host=host,
            url=f"http://{host}:1080/open/yolink/v2/api",
            mqtt_host=host,
            mqtt_port=18080,
        )
        self._auth_mgr = YoLinkLocalAuthMgr(
            session=session,
            token_url=f"http://{host}:1080/open/yolink/token",
            client_id=client_id,
            client_secret=client_secret,
        )
        self._devices: dict[str, YoLinkDevice] = {}
        self._http_client: YoLinkClient | None = None
        self._mqtt_client = None
        self._message_listener: MessageListener | None = None

    async def authenticate(self) -> bool:
        """Authenticate to Local Hub."""
        return await self._auth_mgr.check_and_refresh_token() is not None

    async def async_setup(self, listener: MessageListener) -> None:
        """Init YoLink Local Hub Client."""
        if not listener:
            raise YoLinkClientError(
                "-1002", "setup failed, message listener is required!"
            )
        self._http_client = YoLinkClient(self._auth_mgr)
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
        """Unload YoLink home."""
        self._devices = {}
        self._http_client = None
        if self._mqtt_client is not None:
            await self._mqtt_client.disconnect()
            _LOGGER.info(
                "Local Hub mqtt client disconnected.",
            )
            self._mqtt_client = None
        self._message_listener = None

    async def async_load_devices(self, **kwargs: Any) -> dict[str, YoLinkDevice]:
        """Get sub-net devices."""
        if self._http_client is None:
            raise YoLinkClientError(
                "-1004", "load devices failed, http client is not initialized!"
            )
        response: BRDP = await self._http_client.execute(
            self._endpoint.url, bsdp={"method": "Home.getDeviceList"}, **kwargs
        )
        for device_data in response.data["devices"]:
            device = YoLinkDevice(YoLinkDeviceMode(**device_data), self._http_client)
            device.device_endpoint = self._endpoint
            if device.device_type in has_external_data_devices:
                try:
                    dev_external_data_resp = await device.get_external_data()
                    device.device_attrs = dev_external_data_resp.data.get("extData")
                except YoLinkUnSupportedMethodError:
                    _LOGGER.debug(
                        "getExternalData is not supported for: %s",
                        device.device_type,
                    )
            self._devices[device.device_id] = device
        return self._devices

    def get_devices(self) -> list[YoLinkDevice]:
        """Get Local Hub sub-net devices."""
        return list(self._devices.values())

    def get_device(self, device_id: str) -> YoLinkDevice | None:
        """Get Local Hub sub-net device via device id."""
        return self._devices.get(device_id)
