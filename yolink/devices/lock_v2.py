"""YoLink device implementation."""

from ..client_request import ClientRequest
from ..device import YoLinkDevice
from ..device_feature import DeviceFeature
from ..device_net_type import DeviceNetType
from ..model import BRDP


class YoLinkLockV2(YoLinkDevice):
    """YoLink lock V2."""

    _supports_battery = True
    _supported_features = frozenset({DeviceFeature.LOCK})

    def get_net_type(self) -> DeviceNetType:
        """Return the device network class."""
        return DeviceNetType.D

    async def lock(self) -> BRDP:
        """Lock the device."""
        return await self.call_device(
            ClientRequest("setState", {"state": {"lock": "locked"}})
        )

    async def unlock(self) -> BRDP:
        """Unlock the device."""
        return await self.call_device(
            ClientRequest("setState", {"state": {"lock": "unlocked"}})
        )
