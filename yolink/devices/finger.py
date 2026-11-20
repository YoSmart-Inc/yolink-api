"""YoLink device implementation."""

from ..client_request import ClientRequest
from ..device import YoLinkDevice
from ..device_feature import DeviceFeature
from ..device_net_type import DeviceNetType
from ..model import BRDP


class YoLinkFinger(YoLinkDevice):
    """YoLink Finger garage door controller."""

    _supports_battery = True
    _supported_features = frozenset({DeviceFeature.FINGER})

    def get_net_type(self) -> DeviceNetType:
        """Return the device network class."""
        return DeviceNetType.D

    async def toggle(self) -> BRDP:
        """Toggle the garage door."""
        return await self.call_device(ClientRequest("toggle", {}))
