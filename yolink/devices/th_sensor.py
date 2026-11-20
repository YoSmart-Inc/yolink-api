"""YoLink device implementation."""

from __future__ import annotations

from typing import Any

from ..device import YoLinkDevice
from ..device_feature import DeviceFeature
from ..device_net_type import DeviceNetType


class YoLinkTHSensor(YoLinkDevice):
    """YoLink temperature and humidity sensor."""

    _supports_battery = True
    _supported_features = frozenset({DeviceFeature.TEMPERATURE})

    def get_net_type(self) -> DeviceNetType:
        """Return the device network class."""
        return DeviceNetType.D if "YS8006" in self.model else DeviceNetType.A


    def supported_features(self) -> frozenset[DeviceFeature]:
        """Return the measurements available on this model."""
        features = super().supported_features()
        if self.model in {"YS8004", "YS8008", "YS8014", "YS8017"}:
            return features
        return features | {DeviceFeature.HUMIDITY}

    def _resolve_message(
        self, data: dict[str, Any] | None, event_type: str | None = None
    ) -> None:
        """Resolve this device's message in place."""
        if (
            data is not None
            and (records := data.get("records")) is not None
            and len(records) > 0
        ):
            sorted_records = sorted(
                records, key=lambda x: x.get("time", 0), reverse=True
            )
            data["temperature"] = (
                temperature
                if (temperature := sorted_records[0].get("temperature")) is not None
                else None
            )
            data["humidity"] = (
                humidity
                if (humidity := sorted_records[0].get("humidity")) is not None
                else None
            )
