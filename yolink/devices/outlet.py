"""YoLink device implementation."""

from ..client_request import ClientRequest
from ..const import CLASS_C_KEEPALIVE_TIME
from ..device import YoLinkDevice
from ..device_feature import DeviceFeature
from ..device_net_type import DeviceNetType
from ..model import BRDP


class SetStateMixin:
    """Control devices with outlet-style state commands."""

    def supported_features(self: YoLinkDevice) -> frozenset[DeviceFeature]:
        """Return the capabilities available on this outlet."""
        features = super().supported_features()
        if self.model in {"YS6602", "YS6614", "YS6803"}:
            return features | {DeviceFeature.POWER}
        return features

    async def set_state(
        self: YoLinkDevice, state: str, plug_indx: int | None = None
    ) -> BRDP:
        """Set the state, optionally targeting one outlet."""
        params: dict[str, str | int] = {"state": state}
        if plug_indx is not None:
            params["chs"] = 1 << plug_indx
        return await self.call_device(ClientRequest("setState", params))


class YoLinkOutlet(SetStateMixin, YoLinkDevice):
    """YoLink outlet."""

    def get_net_type(self) -> DeviceNetType:
        """Return the device network class."""
        return DeviceNetType.C

    @property
    def keepalive_time(self) -> int:
        """Return the device keepalive timeout in seconds."""
        return CLASS_C_KEEPALIVE_TIME
