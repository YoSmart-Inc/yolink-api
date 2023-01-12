"""YoLink Device."""
from __future__ import annotations
import abc
from typing import Optional

from tenacity import RetryError
from pydantic import BaseModel, Field, validator

from .client import YoLinkClient
from .exception import YoLinkClientError
from .model import BRDP, BSDPHelper
from .const import (
    ATTR_DEVICE_ID,
    ATTR_DEVICE_NAME,
    ATTR_DEVICE_TOKEN,
    ATTR_DEVICE_TYPE,
    ATTR_DEVICE_PARENT_ID,
)
from .client_request import ClientRequest


class YoLinkDeviceMode(BaseModel):
    """YoLink Device Mode."""

    device_id: str = Field(alias=ATTR_DEVICE_ID)
    device_name: str = Field(alias=ATTR_DEVICE_NAME)
    device_token: str = Field(alias=ATTR_DEVICE_TOKEN)
    device_type: str = Field(alias=ATTR_DEVICE_TYPE)
    device_parent_id: Optional[str] = Field(alias=ATTR_DEVICE_PARENT_ID)

    @validator("device_parent_id")
    def check_parent_id(cls, val):
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
        self.parent_id: str = device.device_parent_id
        self._client: YoLinkClient = client

    async def __invoke(self, method: str, params: dict | None) -> BRDP:
        """Invoke device."""
        try:
            bsdp_helper = BSDPHelper(
                self.device_id,
                self.device_token,
                f"{self.device_type}.{method}",
            )
            if params is not None:
                bsdp_helper.add_params(params)
            return await self._client.execute(bsdp_helper.build())
        except RetryError as err:
            raise YoLinkClientError("-1003", "yolink client request failed!") from err

    async def get_state(self) -> BRDP:
        """Call *.getState with device to request realtime state data."""
        return await self.__invoke("getState", None)

    async def fetch_state(self) -> BRDP:
        """Call *.fetchState with device to fetch state data."""
        return await self.__invoke("fetchState", None)

    async def call_device(self, request: ClientRequest) -> BRDP:
        """Device invoke."""
        return await self.__invoke(request.method, request.params)

    def get_paired_device_id(self) -> str | None:
        """Get device paired device id."""
        if self.parent_id is None or self.parent_id == "null":
            return None
        return self.parent_id
