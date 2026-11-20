"""YoLink device implementation."""

from ..client_request import ClientRequest
from ..const import CLASS_C_KEEPALIVE_TIME
from ..device import YoLinkDevice
from ..device_feature import DeviceFeature
from ..device_net_type import DeviceNetType
from ..model import BRDP


class YoLinkGarageDoor(YoLinkDevice):
    """YoLink garage door controller."""

    _supported_features = frozenset({DeviceFeature.GARAGE_DOOR})

    def get_net_type(self) -> DeviceNetType:
        """Return the device network class."""
        return DeviceNetType.C

    @property
    def keepalive_time(self) -> int:
        """Return the device keepalive timeout in seconds."""
        return CLASS_C_KEEPALIVE_TIME

    async def toggle(self) -> BRDP:
        """Toggle the garage door."""
        return await self.call_device(ClientRequest("toggle", {}))
