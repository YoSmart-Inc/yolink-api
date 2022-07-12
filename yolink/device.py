"""YoLink Device."""
from __future__ import annotations
import abc

from .client import YoLinkClient
from .model import BRDP, BSDPHelper
from .const import ATTR_DEVICE_ID, ATTR_DEVICE_NAME, ATTR_DEVICE_TOKEN, ATTR_DEVICE_TYPE, ATTR_DEVICE_PARENT_ID


class YoLinkDevice(metaclass=abc.ABCMeta):
    """YoLink Device."""

    def __init__(self, device_info: dict, client: YoLinkClient) -> None:
        self.device_id = device_info[ATTR_DEVICE_ID]
        self.device_name = device_info[ATTR_DEVICE_NAME]
        self.device_net_token = device_info[ATTR_DEVICE_TOKEN]
        self.device_type = device_info[ATTR_DEVICE_TYPE]
        self.parent_id = device_info[ATTR_DEVICE_PARENT_ID]
        self.client = client

    async def call_device_http_api(self, method: str, params: dict | None) -> BRDP:
        """Call device API."""
        bsdp_helper = BSDPHelper(
            self.device_id,
            self.device_net_token,
            f"{self.device_type}.{method}",
        )
        if params is not None:
            bsdp_helper.addParams(params)
        return await self.client.call_yolink_api(bsdp_helper.build())

    async def get_state_with_api(self) -> BRDP:
        """Call *.getState with device to request realtime state data."""
        return await self.call_device_http_api("getState", None)

    async def fetch_state_with_api(self) -> BRDP:
        """Call *.fetchState with device to fetch state data."""
        return await self.call_device_http_api("fetchState", None)
