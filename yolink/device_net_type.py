"""Network classes used by YoLink devices."""

from enum import Enum


class DeviceNetType(str, Enum):
    """Supported device network classes."""

    A = "A"
    C = "C"
    D = "D"
    E = "E"
    HUB = "Hub"
