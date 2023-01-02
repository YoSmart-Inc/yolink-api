"""YoLink Device."""
from __future__ import annotations
import abc

from .client import YoLinkClient
from .model import BRDP, BSDPHelper
from .const import (
    ATTR_DEVICE_ID,
    ATTR_DEVICE_NAME,
    ATTR_DEVICE_TOKEN,
    ATTR_DEVICE_TYPE,
    ATTR_DEVICE_PARENT_ID,
)
from .client_request import ClientRequest
from .home_manager import HomeManager


class YoLinkDevice(metaclass=abc.ABCMeta):
    """YoLink Device."""

    def __init__(self, device_info: dict, client: YoLinkClient) -> None:
        self.device_id: str = device_info[ATTR_DEVICE_ID]
        self.device_name: str = device_info[ATTR_DEVICE_NAME]
        self.device_net_token: str = device_info[ATTR_DEVICE_TOKEN]
        self.device_type: str = device_info[ATTR_DEVICE_TYPE]
        self.parent_id: str = device_info[ATTR_DEVICE_PARENT_ID]
        self._client: YoLinkClient = client

    async def __invoke(self, method: str, params: dict | None) -> BRDP:
        """Invoke device."""
        bsdp_helper = BSDPHelper(
            self.device_id,
            self.device_net_token,
            f"{self.device_type}.{method}",
        )
        if params is not None:
            bsdp_helper.add_params(params)
        return await self._client.execute(bsdp_helper.build())

    async def get_state(self) -> BRDP:
        """Call *.getState with device to request realtime state data."""
        return await self.__invoke("getState", None)

    async def fetch_state(self) -> BRDP:
        """Call *.fetchState with device to fetch state data."""
        return await self.__invoke("fetchState", None)

    async def call_device(self, request: ClientRequest) -> BRDP:
        """Device invoke."""
        return await self.__invoke(request.method, request.params)

    def get_paired_device(self) -> YoLinkDevice | None:
        """Get device paired device."""
        if self.parent_id is None or self.parent_id == "null":
            return None
        return HomeManager().get_home_device(self.parent_id)
