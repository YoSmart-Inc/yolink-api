"""YoLink device implementation."""

from __future__ import annotations

from typing import Any

from ..device import YoLinkDevice
from ..device_feature import DeviceFeature
from ..device_net_type import DeviceNetType


class YoLinkWaterDepthSensor(YoLinkDevice):
    """YoLink water depth sensor."""

    _supports_battery = True
    _supported_features = frozenset({DeviceFeature.WATER_DEPTH})

    def get_net_type(self) -> DeviceNetType:
        """Return the device network class."""
        return DeviceNetType.A

    def _resolve_message(
        self, data: dict[str, Any] | None, event_type: str | None = None
    ) -> None:
        """Resolve this device's message in place."""
        if data is not None:
            depth_value = data.get("waterDepth")
            if depth_value is not None:
                # default range settings if range and desity was not set.
                dev_range = 5
                dev_density = 1
                if (
                    self.attrs is not None
                    and (range_attrs := self.attrs.get("range")) is not None
                ):
                    dev_range = range_attrs["range"]
                    dev_density = range_attrs["density"]
                data["waterDepth"] = round(
                    (dev_range * (depth_value / 1000)) / dev_density, 3
                )
