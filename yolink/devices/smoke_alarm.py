"""YoLink device implementation."""

from ..device import YoLinkDevice
from ..device_feature import DeviceFeature
from ..device_net_type import DeviceNetType


class YoLinkSmokeAlarm(YoLinkDevice):
    """YoLink smoke alarm."""

    _supports_battery = True
    _supported_features = frozenset(
        {
            DeviceFeature.ESTIMATED_TEMPERATURE,
            DeviceFeature.SMOKE,
        }
    )

    def get_net_type(self) -> DeviceNetType:
        """Return the device network class."""
        return DeviceNetType.A
