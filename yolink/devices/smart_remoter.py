"""YoLink device implementation."""

from __future__ import annotations

from math import log2
from typing import Any

from ..device import YoLinkDevice
from ..device_net_type import DeviceNetType


class YoLinkSmartRemoter(YoLinkDevice):
    """YoLink smart remote."""

    _supports_battery = True

    def get_net_type(self) -> DeviceNetType:
        """Return the device network class."""
        return DeviceNetType.A

    def _resolve_message(
        self, data: dict[str, Any] | None, event_type: str | None = None
    ) -> None:
        """Resolve this device's message in place."""
        if event_type is None:
            return
        if data is not None:
            btn_press_event = data.get("event")
            if btn_press_event is not None:
                if event_type == "Report":
                    data["event"] = None
                else:
                    key_mask = btn_press_event["keyMask"]
                    button_sequence = 0 if key_mask == 0 else (int(log2(key_mask)) + 1)
                    # replace with button sequence
                    data["event"]["keyMask"] = button_sequence
