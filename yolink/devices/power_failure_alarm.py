"""YoLink device implementation."""

from ..device import YoLinkDevice
from ..device_feature import DeviceFeature
from ..device_net_type import DeviceNetType


class YoLinkPowerFailureAlarm(YoLinkDevice):
    """YoLink power failure alarm."""

    _supports_battery = True
    _supported_features = frozenset(
        {
            DeviceFeature.POWER_FAILURE,
            DeviceFeature.BEEP,
            DeviceFeature.VOLUME,
            DeviceFeature.MUTE,
        }
    )

    def get_net_type(self) -> DeviceNetType:
        """Return the device network class."""
        return DeviceNetType.A
