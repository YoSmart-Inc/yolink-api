"""YoLink device implementation."""

from ..device import YoLinkDevice
from ..device_feature import DeviceFeature
from ..device_net_type import DeviceNetType


class YoLinkLeakSensor(YoLinkDevice):
    """YoLink leak sensor."""

    _supports_battery = True
    _supported_features = frozenset(
        {
            DeviceFeature.ESTIMATED_TEMPERATURE,
            DeviceFeature.LEAK,
        }
    )

    def get_net_type(self) -> DeviceNetType:
        """Return the device network class."""
        return DeviceNetType.A
