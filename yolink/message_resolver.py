"""YoLink cloud message resolver."""

from typing import Any
from math import log2
from .device import YoLinkDevice


def door_sensor_message_resolver(
    device: YoLinkDevice, msg_data: dict[str, Any]
) -> tuple[YoLinkDevice, dict[str, Any]] | list[tuple[YoLinkDevice, dict[str, Any]]]:
    """Door Sensor message resolver."""
    if paired_device := device.get_paired_device() is not None:
        resolved_msg = []
        resolved_msg.append((device, msg_data))
        resolved_msg.append((paired_device, msg_data))
        return resolved_msg
    return tuple(device, msg_data)


def smart_remoter_message_resolver(
    device: YoLinkDevice, msg_data: dict[str, Any]
) -> tuple[YoLinkDevice, dict[str, Any]] | list[tuple[YoLinkDevice, dict[str, Any]]]:
    """SmartRemoter message resolver"""
    if btn_press_event := msg_data.get("event") is not None:
        key_mask = btn_press_event["keyMask"]
        button_sequence = int(log2(key_mask)) + 1
        # replace with button sequence
        msg_data["keyMask"] = button_sequence
        return tuple(device, msg_data)
    return tuple(device, msg_data)
