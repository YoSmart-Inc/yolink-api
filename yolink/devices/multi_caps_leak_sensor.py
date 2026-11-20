"""YoLink device implementation."""

from ..device import YoLinkDevice
from ..device_feature import DeviceFeature
from ..device_net_type import DeviceNetType


class YoLinkMultiCapsLeakSensor(YoLinkDevice):
    """YoLink multi-capability leak sensor."""

    _supports_battery = True
    _supported_features = frozenset(
        {
            DeviceFeature.TEMPERATURE,
            DeviceFeature.HUMIDITY,
            DeviceFeature.LEAK,
        }
    )

    def get_net_type(self) -> DeviceNetType:
        """Return the device network class."""
        return DeviceNetType.D if "YS8006" in self.model else DeviceNetType.A
