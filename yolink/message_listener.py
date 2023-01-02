"""YoLink message pushing listener."""
from abc import ABCMeta, abstractmethod
from typing import Any, Callable
from .const import ATTR_DEVICE_DOOR_SENSOR, ATTR_DEVICE_SMART_REMOTER
from .device import YoLinkDevice
from .home_manager import HomeManager
from .model import BRDP
from .message_resolver import (
    door_sensor_message_resolver,
    smart_remoter_message_resolver,
)


class MessageListener(metaclass=ABCMeta):
    """Home message listener."""

    def on_message_receive(self, message: tuple[str, BRDP]) -> None:
        """On YoLink cloud message received."""
        device_id = message[0]
        msg_data = message[1]
        if msg_data.event is None:
            return
        msg_event = msg_data.event.split(".")
        msg_type = msg_event(len(msg_event) - 1)
        if msg_type not in ["Report", "Alert", "StatusChange", "getState"]:
            return
        if _device := HomeManager().get_home_device(device_id) is None:
            return
        message_resolver = None
        if _device.device_type == ATTR_DEVICE_DOOR_SENSOR:
            message_resolver = door_sensor_message_resolver
        if _device.device_type == ATTR_DEVICE_SMART_REMOTER:
            message_resolver = smart_remoter_message_resolver
        self.__resolve_message(_device, msg_data.data, message_resolver)

    def __resolve_message(
        self,
        device: YoLinkDevice,
        msg_data: dict[str, Any],
        messsage_resolver: Callable[
            [YoLinkDevice, dict[str, Any]],
            tuple[
                YoLinkDevice, dict[str, Any] | list[tuple[YoLinkDevice, dict[str, Any]]]
            ],
        ],
    ) -> None:
        """Resolve message."""
        if messsage_resolver is None:
            self.on_message(device, msg_data)
        else:
            resolved_msg = messsage_resolver(device, msg_data)
            if isinstance(resolved_msg, tuple):
                self.on_message(resolved_msg[0], resolved_msg[1])
            elif isinstance(resolved_msg, list):
                for resolved_msg_item in resolved_msg:
                    self.on_message(resolved_msg_item[0], resolved_msg_item[1])

    @abstractmethod
    def on_message(self, device: YoLinkDevice, msg_data: dict[str, Any]) -> None:
        """On device message receive."""
