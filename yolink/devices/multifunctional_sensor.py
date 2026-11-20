"""YoLink device implementation."""

from ..device import YoLinkDevice
from ..device_feature import DeviceFeature
from ..device_net_type import DeviceNetType


class YoLinkMultifunctionalSensor(YoLinkDevice):
    """YoLink multifunctional sensor."""

    _supports_battery = True
    _supported_features = frozenset(
        {
            DeviceFeature.TEMPERATURE,
            DeviceFeature.CO_CONCENTRATION,
        }
    )

    def get_net_type(self) -> DeviceNetType:
        """Return the device network class."""
        return DeviceNetType.A
