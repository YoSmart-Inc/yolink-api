"""YoLink home manager."""

from __future__ import annotations

import logging
from asyncio import TimeoutError as AsyncTimeoutError
from typing import Any

from tenacity import RetryError

from .auth_mgr import YoLinkAuthMgr
from .client import YoLinkClient
from .const import ATTR_DEVICE_WATER_DEPTH_SENSOR
from .device import YoLinkDevice, YoLinkDeviceMode
from .endpoint import Endpoint, Endpoints
from .exception import YoLinkClientError, YoLinkUnSupportedMethodError
from .message_listener import MessageListener
from .model import BRDP
from .mqtt_client import YoLinkMqttClient

_LOGGER = logging.getLogger(__name__)

has_external_data_devices = [ATTR_DEVICE_WATER_DEPTH_SENSOR]


class YoLinkHome:
    """YoLink home manager."""

    def __init__(self) -> None:
        """Init YoLink Home Manager."""
        self._home_devices: dict[str, YoLinkDevice] = {}
        self._http_client: YoLinkClient
        self._endpoints: dict[str, Endpoint] = {}
        self._mqtt_clients: dict[str, YoLinkMqttClient] = {}
        self._message_listener: MessageListener

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
        # setup yolink mqtt clients
        for endpoint in self._endpoints.values():
            endpoint_mqtt_client = YoLinkMqttClient(
                auth_manager=auth_mgr,
                endpoint=endpoint,
                broker_host=endpoint.mqtt_broker_host,
                broker_port=endpoint.mqtt_broker_port,
                devices=self._home_devices,
            )
            await endpoint_mqtt_client.connect(
                f"yl-home/{home_info.data['id']}/+/report", self._message_listener
            )
            self._mqtt_clients[endpoint.name] = endpoint_mqtt_client

    async def async_unload(self) -> None:
        """Unload YoLink home."""
        self._home_devices = {}
        self._http_client = None  # type: ignore
        for endpoint, client in self._mqtt_clients.items():
            _LOGGER.info(
                "[%s] shutting down yolink mqtt client.",
                endpoint,
            )
            await client.disconnect()
            _LOGGER.info(
                "[%s] yolink mqtt client disconnected.",
                endpoint,
            )
        self._message_listener = None  # type: ignore
        self._mqtt_clients = {}

    async def async_get_home_info(self, **kwargs: Any) -> BRDP:
        """Get home general information."""
        return await self._http_client.execute(
            url=Endpoints.US.value.url,  # type: ignore
            bsdp={"method": "Home.getGeneralInfo"},
            **kwargs,
        )

    async def async_load_home_devices(self, **kwargs: Any) -> dict[str, YoLinkDevice]:
        """Get home devices."""
        response: BRDP = await self._http_client.execute(
            url=Endpoints.US.value.url,  # type: ignore
            bsdp={"method": "Home.getDeviceList"},
            **kwargs,
        )
        devices = [
            YoLinkDevice(YoLinkDeviceMode(**device), self._http_client)
            for device in response.data["devices"]
        ]
        await self._async_sync_eu_tokens(devices, **kwargs)
        loaded_devices: dict[str, YoLinkDevice] = {}
        for device in devices:
            if device.device_type in has_external_data_devices:
                await self._async_load_external_data(device)
            loaded_devices[device.device_id] = device

        for device_id in self._home_devices.keys() - loaded_devices.keys():
            del self._home_devices[device_id]
        self._home_devices.update(loaded_devices)
        for device in devices:
            self._endpoints[device.device_endpoint.name] = device.device_endpoint

        return self._home_devices

    async def _async_sync_eu_tokens(
        self, devices: list[YoLinkDevice], **kwargs: Any
    ) -> None:
        """Synchronize EU tokens, retaining original tokens when unavailable."""
        eu_devices = [
            device for device in devices if device.device_endpoint == Endpoints.EU.value
        ]
        if not eu_devices:
            return

        try:
            response = await self._http_client.execute(
                url=Endpoints.EU.value.url,
                bsdp={"method": "Home.getDeviceList"},
                **kwargs,
            )
            tokens = {}
            for item in response.data["devices"]:
                if not isinstance(item, dict):
                    _LOGGER.warning("Ignoring invalid EU device list entry")
                    continue
                device_id = item.get("deviceId")
                token = item.get("token")
                if (
                    not isinstance(device_id, str)
                    or not device_id
                    or not isinstance(token, str)
                    or not token
                ):
                    _LOGGER.warning(
                        "Ignoring EU device list entry with invalid ID or token"
                    )
                    continue
                tokens[device_id] = token
        except (
            YoLinkClientError,
            TimeoutError,
            AsyncTimeoutError,
            RetryError,
            KeyError,
            TypeError,
            ValueError,
        ):
            _LOGGER.warning(
                "Failed to sync EU device tokens; keeping existing tokens",
                exc_info=True,
            )
            tokens = {}

        for device in eu_devices:
            if token := tokens.get(device.device_id):
                device.device_token = token
            else:
                _LOGGER.warning(
                    "EU token unavailable for device %s; keeping its original token",
                    device.device_id,
                )

    async def _async_load_external_data(self, device: YoLinkDevice) -> None:
        """Load settings needed to interpret device data."""
        try:
            response = await device.get_external_data()
            device.device_attrs = response.data.get("extData")
        except YoLinkUnSupportedMethodError:
            _LOGGER.debug(
                "getExternalData is not supported for: %s", device.device_type
            )
        except (YoLinkClientError, TimeoutError, AsyncTimeoutError, RetryError):
            if device.device_endpoint != Endpoints.EU.value:
                raise
            _LOGGER.warning(
                "Failed to load external data for EU device %s",
                device.device_id,
                exc_info=True,
            )

    def get_devices(self) -> list[YoLinkDevice]:
        """Get home devices."""
        return list(self._home_devices.values())

    def get_device(self, device_id: str) -> YoLinkDevice | None:
        """Get home device via device id."""
        return self._home_devices.get(device_id)
