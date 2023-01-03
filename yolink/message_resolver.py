"""YoLink cloud message resolver."""

from typing import Any
from math import log2


def smart_remoter_message_resolver(msg_data: dict[str, Any]) -> dict[str, Any]:
    """SmartRemoter message resolver"""
    btn_press_event = msg_data.get("event")
    if btn_press_event is not None:
        key_mask = btn_press_event["keyMask"]
        button_sequence = int(log2(key_mask)) + 1
        # replace with button sequence
        msg_data["event"]["keyMask"] = button_sequence
    return msg_data
