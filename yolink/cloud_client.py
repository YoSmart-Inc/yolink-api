"""YoLink home manager."""

from __future__ import annotations

import logging
from typing import Any

from .abstract_client import YoLinkClinet
from .auth_mgr import YoLinkAuthMgr
from .const import ATTR_DEVICE_WATER_DEPTH_SENSOR
from .device import YoLinkDevice, YoLinkDeviceMode
from .devices import create_device
from .endpoint import Endpoint, Endpoints
from .exception import (
    YoLinkApiCode,
    YoLinkClientError,
    YoLinkConfigError,
    YoLinkError,
)
from .http_client import YoLinkHttpClient
from .message_listener import MessageListener
from .model import BRDP
from .mqtt_client import YoLinkMqttClient

_LOGGER = logging.getLogger(__name__)

has_external_data_devices = [ATTR_DEVICE_WATER_DEPTH_SENSOR]


class YoLinkCloudClinet(YoLinkClinet):
    """YoLink home manager."""

    def __init__(self, auth_mgr: YoLinkAuthMgr) -> None:
        """Init YoLink Home Manager."""
        if not auth_mgr:
            raise YoLinkConfigError("setup failed, auth_mgr is required!")
        self._auth_mgr = auth_mgr
        self._home_devices: dict[str, YoLinkDevice] = {}
        self._http_client: YoLinkHttpClient
        self._endpoints: dict[str, Endpoint] = {}
        self._mqtt_clients: dict[str, YoLinkMqttClient] = {}
        self._message_listener: MessageListener

    async def async_setup(self, listener: MessageListener) -> None:
        """Init YoLink home."""
        if not listener:
            raise YoLinkConfigError("setup failed, message listener is required!")
        self._http_client = YoLinkHttpClient(self._auth_mgr)
        home_info: BRDP = await self.async_get_home_info()
        # load home devices
        await self.async_load_home_devices()
        # setup yolink mqtt connection
        self._message_listener = listener
        # setup yolink mqtt clients
        for endpoint in self._endpoints.values():
            endpoint_mqtt_client = YoLinkMqttClient(
                auth_manager=self._auth_mgr,
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
        _LOGGER.info("Unloading YoLink home: mqtt_clients=%s", len(self._mqtt_clients))
        self._home_devices = {}
        self._http_client = None  # type: ignore
        for client in self._mqtt_clients.values():
            await client.disconnect()
        self._message_listener = None  # type: ignore
        self._mqtt_clients = {}
        _LOGGER.info("YoLink home unloaded")

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
            device
            for device_data in response.data["devices"]
            if (
                device := create_device(
                    YoLinkDeviceMode(**device_data), self._http_client
                )
            )
            is not None
        ]
        await self._async_sync_eu_tokens(devices, **kwargs)
        loaded_devices: dict[str, YoLinkDevice] = {}
        for device in devices:
            if device.type in has_external_data_devices:
                await self._async_load_external_data(device)
            loaded_devices[device.id] = device

        self._home_devices.clear()
        self._home_devices.update(loaded_devices)
        for device in devices:
            self._endpoints[device.endpoint.name] = device.endpoint

        _LOGGER.debug("Loaded home devices: count=%s", len(self._home_devices))
        return self._home_devices

    async def _async_sync_eu_tokens(
        self, devices: list[YoLinkDevice], **kwargs: Any
    ) -> None:
        """Synchronize EU tokens, retaining original tokens when unavailable."""
        eu_devices = [
            device for device in devices if device.endpoint == Endpoints.EU.value
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
        except (YoLinkError, KeyError, TypeError, ValueError) as err:
            _LOGGER.warning(
                "Failed to sync EU device tokens; keeping existing tokens for %s devices: "
                "error=%s code=%s",
                len(eu_devices),
                type(err).__name__,
                getattr(err, "code", None),
            )
            return

        for device in eu_devices:
            if token := tokens.get(device.id):
                device.token = token
            else:
                _LOGGER.warning(
                    "EU token unavailable for device %s; keeping its original token",
                    device.id,
                )

    async def _async_load_external_data(self, device: YoLinkDevice) -> None:
        """Load settings needed to interpret device data."""
        try:
            response = await device.get_external_data()
            device.attrs = response.data.get("extData")
        except YoLinkError as err:
            if (
                isinstance(err, YoLinkClientError)
                and err.code == YoLinkApiCode.UNSUPPORTED_METHOD
            ):
                _LOGGER.debug(
                    "[%s] getExternalData is not supported: device=%s type=%s",
                    device.endpoint.name,
                    device.id,
                    device.type,
                )
                return
            if device.endpoint != Endpoints.EU.value:
                raise
            _LOGGER.warning(
                "[EU] Failed to load external data: device=%s type=%s error=%s code=%s",
                device.id,
                device.type,
                type(err).__name__,
                getattr(err, "code", None),
            )

    def get_devices(self) -> list[YoLinkDevice]:
        """Get home devices."""
        return list(self._home_devices.values())

    def get_device(self, device_id: str) -> YoLinkDevice | None:
        """Get home device via device id."""
        return self._home_devices.get(device_id)
