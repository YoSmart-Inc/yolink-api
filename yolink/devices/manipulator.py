"""YoLink device implementation."""

from ..const import CLASS_C_KEEPALIVE_TIME
from ..device import YoLinkDevice
from ..device_net_type import DeviceNetType
from .outlet import SetStateMixin


class YoLinkManipulator(SetStateMixin, YoLinkDevice):
    """YoLink manipulator."""

    _supports_battery = True

    def get_net_type(self) -> DeviceNetType:
        """Return the device network class."""
        return (
            DeviceNetType.D
            if any(
                model in self.model
                for model in ("YS4909", "YS5001", "YS5002", "YS5003", "YS5012")
            )
            else DeviceNetType.C
        )

    @property
    def keepalive_time(self) -> int:
        """Return the device keepalive timeout in seconds."""
        if self.class_mode in (DeviceNetType.C, DeviceNetType.E):
            return CLASS_C_KEEPALIVE_TIME
        return super().keepalive_time
