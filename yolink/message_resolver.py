"""YoLink cloud message resolver."""

from typing import Any
from math import log2


def smart_remoter_message_resolve(msg_data: dict[str, Any]) -> dict[str, Any]:
    """SmartRemoter message resolve."""
    btn_press_event = msg_data.get("event")
    if btn_press_event is not None:
        key_mask = btn_press_event["keyMask"]
        button_sequence = 0 if key_mask == 0 else (int(log2(key_mask)) + 1)
        # replace with button sequence
        msg_data["event"]["keyMask"] = button_sequence
    return msg_data


def water_depth_sensor_message_resolve(
    msg_data: dict[str, Any], dev_attrs: dict[str, Any]
) -> dict[str, Any]:
    """WaterDepthSensor message resolve."""
    if msg_data is not None and dev_attrs is not None:
        depth_value = msg_data.get("waterDepth")
        if depth_value is not None:
            dev_range = dev_attrs["range"]["range"]
            dev_density = dev_attrs["range"]["density"]
            msg_data["waterDepth"] = round(
                (dev_range * (depth_value / 1000)) / dev_density, 2
            )
    return msg_data
