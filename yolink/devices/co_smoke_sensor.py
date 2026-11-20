"""YoLink device implementation."""

from ..device import YoLinkDevice
from ..device_feature import DeviceFeature
from ..device_net_type import DeviceNetType


class YoLinkCOSmokeSensor(YoLinkDevice):
    """YoLink CO and smoke sensor."""

    _supports_battery = True
    _supported_features = frozenset(
        {
            DeviceFeature.ESTIMATED_TEMPERATURE,
            DeviceFeature.CO,
            DeviceFeature.SMOKE,
        }
    )

    def get_net_type(self) -> DeviceNetType:
        """Return the device network class."""
        return DeviceNetType.D if "YS7A02" in self.model else DeviceNetType.A
