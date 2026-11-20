"""YoLink device implementation."""

from ..client_request import ClientRequest
from ..const import CLASS_C_KEEPALIVE_TIME
from ..device import YoLinkDevice
from ..device_feature import DeviceFeature
from ..device_net_type import DeviceNetType
from ..model import BRDP


class YoLinkDimmer(YoLinkDevice):
    """YoLink dimmer."""

    _supported_features = frozenset({DeviceFeature.DIMMER})

    def get_net_type(self) -> DeviceNetType:
        """Return the device network class."""
        return DeviceNetType.C

    @property
    def keepalive_time(self) -> int:
        """Return the device keepalive timeout in seconds."""
        return CLASS_C_KEEPALIVE_TIME

    async def set_state(self, state: str, brightness: float | None = None) -> BRDP:
        """Set the light state and optionally set brightness as a percentage."""
        params: dict[str, str | float] = {"state": state}
        if brightness is not None:
            params["brightness"] = brightness
        return await self.call_device(ClientRequest("setState", params))
