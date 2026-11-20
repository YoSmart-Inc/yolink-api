"""YoLink device implementation."""

from ..const import CLASS_C_KEEPALIVE_TIME
from ..device import YoLinkDevice
from ..device_net_type import DeviceNetType
from .outlet import SetStateMixin


class YoLinkSwitch(SetStateMixin, YoLinkDevice):
    """YoLink switch."""

    def get_net_type(self) -> DeviceNetType:
        """Return the device network class."""
        return DeviceNetType.D if "YS5709" in self.model else DeviceNetType.C

    @property
    def keepalive_time(self) -> int:
        """Return the device keepalive timeout in seconds."""
        if self.class_mode in (DeviceNetType.C, DeviceNetType.E):
            return CLASS_C_KEEPALIVE_TIME
        return super().keepalive_time
