"""Common interface for YoLink connections."""

from abc import ABC, abstractmethod

from .device import YoLinkDevice
from .message_listener import MessageListener


class YoLinkClinet(ABC):
    """Interface shared by cloud and local connections."""

    @abstractmethod
    async def async_setup(self, listener: MessageListener) -> None:
        """Set up yolink client."""

    @abstractmethod
    async def async_unload(self) -> None:
        """Unload the client."""

    @abstractmethod
    def get_devices(self) -> list[YoLinkDevice]:
        """Return the loaded devices."""

    @abstractmethod
    def get_device(self, device_id: str) -> YoLinkDevice | None:
        """Return a loaded device by ID, or None if it is unknown."""
