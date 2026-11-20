"""YoLink device implementation."""

from __future__ import annotations

from typing import Any

from ..device import YoLinkDevice
from ..device_feature import DeviceFeature
from ..device_net_type import DeviceNetType


class YoLinkSoilThcSensor(YoLinkDevice):
    """YoLink soil temperature, humidity, and conductivity sensor."""

    _supports_battery = True
    _supported_features = frozenset(
        {
            DeviceFeature.TEMPERATURE,
            DeviceFeature.HUMIDITY,
            DeviceFeature.CONDUCTIVITY,
        }
    )

    def get_net_type(self) -> DeviceNetType:
        """Return the device network class."""
        return DeviceNetType.D if "YS8006" in self.model else DeviceNetType.A

    def _resolve_message(
        self, data: dict[str, Any] | None, event_type: str | None = None
    ) -> None:
        """Resolve this device's message in place."""
        if data is not None and ((state := data.get("state")) is not None):
            data["temperature"] = state.get("temperature")
            data["humidity"] = state.get("humidity")
            data["conductivity"] = state.get("conductivity")
