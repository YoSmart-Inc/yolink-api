"""YoLink Device."""

from __future__ import annotations
import abc
from typing import Optional, Any
from datetime import datetime, timezone

from pydantic import BaseModel, Field, field_validator
from tenacity import RetryError

from .client import YoLinkClient
from .endpoint import Endpoint, Endpoints
from .model import BRDP, BSDPHelper
from .const import (
    ATTR_DEVICE_ID,
    ATTR_DEVICE_NAME,
    ATTR_DEVICE_TOKEN,
    ATTR_DEVICE_TYPE,
    ATTR_DEVICE_MODEL_NAME,
    ATTR_DEVICE_PARENT_ID,
    ATTR_DEVICE_SERVICE_ZONE,
    DEVICE_MODELS_SUPPORT_MODE_SWITCHING,
)
from .client_request import ClientRequest
from .message_resolver import resolve_message
from .device_helper import get_net_type, get_keepalive_time
from time import time


class YoLinkDeviceMode(BaseModel):
    """YoLink Device Mode."""

    device_id: str = Field(alias=ATTR_DEVICE_ID)
    device_name: str = Field(alias=ATTR_DEVICE_NAME)
    device_token: str = Field(alias=ATTR_DEVICE_TOKEN)
    device_type: str = Field(alias=ATTR_DEVICE_TYPE)
    device_model_name: str = Field(alias=ATTR_DEVICE_MODEL_NAME, default=None)
    device_parent_id: Optional[str] = Field(alias=ATTR_DEVICE_PARENT_ID, default=None)
    device_service_zone: Optional[str] = Field(
        alias=ATTR_DEVICE_SERVICE_ZONE, default=None
    )

    @field_validator("device_parent_id")
    @classmethod
    def check_parent_id(cls, val: Optional[str]) -> Optional[str]:
        """Checking and replace parent id."""
        if val == "null":
            val = None
        return val


class YoLinkDevice(metaclass=abc.ABCMeta):
    """YoLink device."""

    def __init__(self, device: YoLinkDeviceMode, client: YoLinkClient) -> None:
        self.device_id: str = device.device_id
        self.device_name: str = device.device_name
        self.device_token: str = device.device_token
        self.device_type: str = device.device_type
        self.device_model_name: str = device.device_model_name
        self.device_attrs: dict | None = None
        self.parent_id: str = device.device_parent_id
        self._client: YoLinkClient = client

        self._state: dict | None = {}
        self.device_model: str = (
            device.device_model_name.split("-")[0]
            if device.device_model_name is not None
            else ""
        )
        if device.device_service_zone is not None:
            self.device_endpoint: Endpoint = (
                Endpoints.EU.value
                if device.device_service_zone.startswith("eu_")
                else Endpoints.US.value
            )
        else:
            if device.device_model_name is not None:
                self.device_endpoint: Endpoint = (
                    Endpoints.EU.value
                    if device.device_model_name.endswith("-EC")
                    else Endpoints.US.value
                )
            else:
                self.device_endpoint: Endpoint = Endpoints.US.value
        self.class_mode: str = get_net_type(self.device_type, self.device_model)

    async def __invoke(self, method: str, params: dict | None, **kwargs: Any) -> BRDP:
        """Invoke device."""
        try:
            bsdp_helper = BSDPHelper(
                self.device_id,
                self.device_token,
                f"{self.device_type}.{method}",
            )
            if params is not None:
                bsdp_helper.add_params(params)
            return await self._client.execute(
                url=self.device_endpoint.url, bsdp=bsdp_helper.build(), **kwargs
            )
        except RetryError as err:
            raise err.last_attempt.result()

    async def get_state(self) -> BRDP:
        """Call *.getState with device to request realtime state data."""
        return await self.__invoke("getState", None)

    async def fetch_state(self) -> BRDP:
        """Call *.fetchState with device to fetch state data."""
        # call_method: str = "getState" if self.is_hub else "fetchState"
        # options = {"timeout": 4} if call_method == "fetchState" else {}
        if self.is_hub:
            return BRDP(
                code="000000",
                desc="success",
                method="fetchState",
                data={},
            )
        state_brdp: BRDP = await self.__invoke("fetchState", None)
        resolve_message(self, state_brdp.data.get("state"), None)
        return state_brdp

    async def get_external_data(self) -> BRDP:
        """Call *.getExternalData to get device settings."""
        return await self.__invoke("getExternalData", None)

    async def call_device(self, request: ClientRequest) -> BRDP:
        """Device invoke."""
        return await self.__invoke(request.method, request.params)

    @property
    def is_hub(self) -> bool:
        """Check if the device is a Hub device."""
        return self.device_type in ["Hub", "SpeakerHub"]

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
        return self.device_model_name in DEVICE_MODELS_SUPPORT_MODE_SWITCHING

    def is_online(self, data: dict[str, Any]) -> bool:
        """Check if the device is online.
        Not for Hub devices.
        """
        if data is None:
            return False
        if self.is_hub and data.get("online") is not None:
            return data.get("online")
        last_report_at: Optional[int] = data.get("reportAt")
        if last_report_at is None:
            return False
        keepalive_time = get_keepalive_time(self)
        if keepalive_time <= 0:
            return False
        last_report_at_ts = datetime.strptime(
            last_report_at, "%Y-%m-%dT%H:%M:%S.%fZ"
        ).replace(tzinfo=timezone.utc)
        return (int(time.time()) - last_report_at_ts) <= keepalive_time
