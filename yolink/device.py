"""YoLink Device."""

from __future__ import annotations

import abc
import logging
from datetime import datetime, timezone
from typing import Any, ClassVar

from pydantic import BaseModel, Field, field_validator

from .client_request import ClientRequest
from .config import config
from .const import (
    ATTR_DEVICE_APP_EUI,
    ATTR_DEVICE_ID,
    ATTR_DEVICE_MODEL_NAME,
    ATTR_DEVICE_NAME,
    ATTR_DEVICE_PARENT_ID,
    ATTR_DEVICE_SERVICE_ZONE,
    ATTR_DEVICE_TOKEN,
    ATTR_DEVICE_TYPE,
    ATTR_FIELD_LORA,
    KEEPALIVE_TIME,
)
from .datetime_helper import to_utc_datetime
from .device_feature import DeviceFeature
from .device_net_type import DeviceNetType
from .endpoint import Endpoint, Endpoints
from .http_client import YoLinkHttpClient
from .model import BRDP, BSDPHelper

_LOGGER = logging.getLogger(__name__)


class YoLinkDeviceMode(BaseModel):
    """YoLink Device Mode."""

    id: str = Field(alias=ATTR_DEVICE_ID)
    name: str = Field(alias=ATTR_DEVICE_NAME)
    token: str = Field(alias=ATTR_DEVICE_TOKEN)
    type: str = Field(alias=ATTR_DEVICE_TYPE)
    model_name: str | None = Field(alias=ATTR_DEVICE_MODEL_NAME, default=None)
    parent_id: str | None = Field(alias=ATTR_DEVICE_PARENT_ID, default=None)
    service_zone: str | None = Field(alias=ATTR_DEVICE_SERVICE_ZONE, default=None)
    app_eui: str | None = Field(alias=ATTR_DEVICE_APP_EUI, default=None)

    @field_validator("parent_id")
    @classmethod
    def check_parent_id(cls, val: str | None) -> str | None:
        """Checking and replace parent id."""
        if val == "null":
            val = None
        return val


class YoLinkDevice(metaclass=abc.ABCMeta):
    """YoLink device."""

    _supported_features: ClassVar[frozenset[DeviceFeature]] = frozenset()
    _supports_battery: ClassVar[bool] = False

    def __init__(self, device: YoLinkDeviceMode, client: YoLinkHttpClient) -> None:
        self.id: str = device.id
        self.name: str = device.name
        self.token: str = device.token
        self.type: str = device.type
        self.model_name: str | None = device.model_name
        self.attrs: dict | None = None
        self.parent_id: str | None = device.parent_id
        self._client: YoLinkHttpClient = client
        self.app_eui: str | None = device.app_eui
        self.last_report_at: datetime | None = None
        self.model: str = (
            device.model_name.split("-")[0] if device.model_name is not None else ""
        )
        if not self.model and self.app_eui is not None:
            self.model = f"YS{self.app_eui[6:10]}"
            self.model_name = self.model
        if device.service_zone is not None:
            self.endpoint: Endpoint = (
                Endpoints.EU.value
                if device.service_zone.startswith("eu_")
                else Endpoints.US.value
            )
        else:
            if device.model_name is not None:
                self.endpoint: Endpoint = (
                    Endpoints.EU.value
                    if device.model_name.endswith("-EC")
                    else Endpoints.US.value
                )
            else:
                self.endpoint: Endpoint = Endpoints.US.value
        self.class_mode: DeviceNetType | None = self.get_net_type()
        self.current_net_type: str | None = None

    async def __invoke(self, method: str, params: dict | None, **kwargs: Any) -> BRDP:
        """Invoke device."""
        bsdp_helper = BSDPHelper(
            self.id,
            self.token,
            f"{self.type}.{method}",
        )
        if params is not None:
            bsdp_helper.add_params(params)
        return await self._client.execute(
            url=self.endpoint.url, bsdp=bsdp_helper.build(), **kwargs
        )

    async def get_state(self) -> BRDP:
        """Call *.getState with device to request realtime state data."""
        response = await self.__invoke("getState", None)
        self.resolve_message(response.data, "getState")
        return response

    async def fetch_state(self) -> BRDP:
        """Call *.fetchState with device to fetch state data."""
        state_brdp: BRDP = await self.__invoke("fetchState", None)
        self.update_last_report_at(state_brdp.data.get("reportAt"))
        self.resolve_message(state_brdp.data.get("state"))
        return state_brdp

    async def get_external_data(self) -> BRDP:
        """Call *.getExternalData to get device settings."""
        return await self.__invoke("getExternalData", None)

    async def call_device(self, request: ClientRequest) -> BRDP:
        """Device invoke."""
        return await self.__invoke(request.method, request.params)

    def update_last_report_at(self, report_at: datetime | str | float | None) -> None:
        """Record a valid report time without replacing a newer one."""
        report_time = to_utc_datetime(report_at)
        if report_time is not None and (
            self.last_report_at is None or report_time > self.last_report_at
        ):
            self.last_report_at = report_time

    @property
    def is_hub(self) -> bool:
        """Check if the device is a Hub device."""
        return self.type in ["Hub", "SpeakerHub"]

    @property
    def paired_device_id(self) -> str | None:
        """Get device paired device id."""
        if self.parent_id is None or self.parent_id == "null":
            return None
        return self.parent_id

    def get_paired_device_id(self) -> str | None:
        """Get device paired device id."""
        if self.parent_id is None or self.parent_id == "null":
            return None
        return self.parent_id

    def is_support_mode_switching(self) -> bool:
        """Check if the device supports mode switching."""
        return False

    def support_battery(self) -> bool:
        """Return whether this device can report a battery level."""
        return self._supports_battery

    def supports_any_feature(self, *features: DeviceFeature) -> bool:
        """Return whether this device supports at least one requested capability."""
        return not self.supported_features().isdisjoint(features)

    def supported_features(self) -> frozenset[DeviceFeature]:
        """Return the capabilities declared for this device."""
        return self._supported_features | {DeviceFeature.SIGNAL_STRENGTH}

    @property
    def keepalive_time(self) -> int:
        """Get device keepalive time in seconds."""
        return KEEPALIVE_TIME

    def is_online(self) -> bool:
        """Check whether the latest device report is still within its timeout."""
        online = (
            self.last_report_at is not None
            and (datetime.now(timezone.utc) - self.last_report_at).total_seconds()
            < self.keepalive_time
        )
        _LOGGER.debug(
            "Device online status: name=%s id=%s type=%s online=%s "
            "last_report_at=%s keepalive=%ss",
            self.name,
            self.id,
            self.type,
            online,
            self.last_report_at,
            self.keepalive_time,
        )
        return online

    @property
    def net_type(self) -> DeviceNetType | None:
        """Return the network class."""
        return self.get_net_type()

    def get_net_type(self) -> DeviceNetType | None:
        """Return the network class for this device."""
        return None

    def resolve_message(
        self, data: dict[str, Any] | None, event_type: str | None = None
    ) -> None:
        """Update device data and apply message conversion when enabled."""
        if data is not None and (lora_info := data.get(ATTR_FIELD_LORA)) is not None:
            self.current_net_type = lora_info.get("devNetType")
        if config.enable_message_conversion:
            self._resolve_message(data, event_type)

    def _resolve_message(
        self, data: dict[str, Any] | None, event_type: str | None = None
    ) -> None:
        """Resolve device-specific message data in place."""
