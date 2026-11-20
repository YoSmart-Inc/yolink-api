"""YoLink device implementation."""

from ..device import YoLinkDevice
from ..device_feature import DeviceFeature
from ..device_net_type import DeviceNetType


class YoLinkDoorSensor(YoLinkDevice):
    """YoLink door sensor."""

    _supports_battery = True
    _supported_features = frozenset({DeviceFeature.DOOR})

    def get_net_type(self) -> DeviceNetType:
        """Return the device network class."""
        return DeviceNetType.A
