"""YoLink device implementation."""

from __future__ import annotations

from decimal import ROUND_DOWN, Decimal
from typing import Any

from ..client_request import ClientRequest
from ..device import YoLinkDevice
from ..device_feature import DeviceFeature
from ..device_net_type import DeviceNetType
from ..model import BRDP
from ..unit_helper import UnitOfVolume, VolumeConverter


class YoLinkWaterMeterController(YoLinkDevice):
    """YoLink water meter controller."""

    _supports_battery = True
    _supported_features = frozenset(
        {
            DeviceFeature.WATER_METER,
            DeviceFeature.LEAK,
        }
    )

    def supported_features(self) -> frozenset[DeviceFeature]:
        """Return the declared water measurements for this model."""
        features = super().supported_features()
        if not self.model.startswith("YS5007"):
            features |= {DeviceFeature.VALVE}
        if self.model == "YS5018":
            features |= {DeviceFeature.WATER_TEMPERATURE, DeviceFeature.WATER_FLOW}
        return features

    def is_support_mode_switching(self) -> bool:
        """Return whether the water meter supports mode switching."""
        return self.model == "YS5009"

    def get_net_type(self) -> DeviceNetType:
        """Return the device network class."""
        return DeviceNetType.A if self.model == "YS5007" else DeviceNetType.D

    def _resolve_message(
        self, data: dict[str, Any] | None, event_type: str | None = None
    ) -> None:
        """Resolve this device's message in place."""
        if data is not None and ((meter_state := data.get("state")) is not None):
            meter_step_factor: int = 10
            # for some reason meter value can't be read
            meter_value = meter_state.get("meter")
            if meter_value is not None:
                meter_unit = UnitOfVolume.GALLONS
                if (meter_attrs := data.get("attributes")) is not None:
                    if self.model_name is not None and self.model_name.startswith(
                        "YS5009"
                    ):
                        meter_step_factor = (
                            1 / (_meter_step_factor / (1000 * 100))
                            if (
                                _meter_step_factor := meter_attrs.get("meterStepFactor")
                            )
                            is not None
                            else 10
                        )
                    else:
                        meter_step_factor = (
                            _meter_step_factor
                            if (
                                _meter_step_factor := meter_attrs.get("meterStepFactor")
                            )
                            is not None
                            else 10
                        )
                    meter_unit = (
                        UnitOfVolume(_meter_unit)
                        if (_meter_unit := meter_attrs.get("meterUnit")) is not None
                        else UnitOfVolume.GALLONS
                    )
                _meter_reading = None
                if meter_step_factor < 0:
                    _meter_reading = meter_value * abs(meter_step_factor)
                else:
                    _meter_reading = meter_value / meter_step_factor
                meter_value = VolumeConverter.convert(
                    _meter_reading, meter_unit, UnitOfVolume.CUBIC_METERS
                )
                data["meter_reading"] = float(
                    Decimal(meter_value).quantize(
                        Decimal(".00000"), rounding=ROUND_DOWN
                    )
                )
            data["valve_state"] = meter_state["valve"]

    async def set_valve(self, opened: bool) -> BRDP:
        """Open or close the valve."""
        return await self.call_device(
            ClientRequest("setState", {"valve": "open" if opened else "close"})
        )
