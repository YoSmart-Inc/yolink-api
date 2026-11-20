"""YoLink device implementation."""

from ..const import CLASS_C_KEEPALIVE_TIME
from ..device import YoLinkDevice
from ..device_net_type import DeviceNetType
from .outlet import SetStateMixin


class YoLinkMultiOutlet(SetStateMixin, YoLinkDevice):
    """YoLink multi-outlet device."""

    @property
    def outlet_count(self) -> int:
        """Return the number of controllable AC outlets."""
        return 4 if self.model.startswith("YS6801") else 2

    @property
    def has_usb_ports(self) -> bool:
        """Return whether the outlet has controllable USB ports."""
        return self.model.startswith("YS6801")

    def get_net_type(self) -> DeviceNetType:
        """Return the device network class."""
        return DeviceNetType.C

    @property
    def keepalive_time(self) -> int:
        """Return the device keepalive timeout in seconds."""
        return CLASS_C_KEEPALIVE_TIME
