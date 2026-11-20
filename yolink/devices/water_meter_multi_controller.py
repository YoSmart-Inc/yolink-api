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


class YoLinkWaterMeterMultiController(YoLinkDevice):
    """YoLink multi-channel water meter controller."""

    _supports_battery = True
    _supported_features = frozenset(
        {
            DeviceFeature.WATER_METER,
            DeviceFeature.VALVE,
            DeviceFeature.LEAK,
        }
    )

    def is_support_mode_switching(self) -> bool:
        """Return whether the water meter supports mode switching."""
        return self.model == "YS5029"

    def get_net_type(self) -> DeviceNetType:
        """Return the device network class."""
        return DeviceNetType.D

    def _resolve_message(
        self, data: dict[str, Any] | None, event_type: str | None = None
    ) -> None:
        """Resolve this device's message in place."""
        if data is not None and ((meter_state := data.get("state")) is not None):
            meter_step_factor: int = 10
            meter_reading_values: dict = meter_state.get("meters")
            if meter_reading_values is not None:
                meter_unit = UnitOfVolume.GALLONS
                if (meter_attrs := data.get("attributes")) is not None:
                    if self.model_name is not None and self.model_name.startswith(
                        "YS5029"
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
                _meter_1_reading = None
                if meter_step_factor < 0:
                    _meter_1_reading = meter_reading_values["0"] * abs(
                        meter_step_factor
                    )
                else:
                    _meter_1_reading = meter_reading_values["0"] / meter_step_factor
                meter_reading_values["0"] = VolumeConverter.convert(
                    _meter_1_reading,
                    meter_unit,
                    UnitOfVolume.CUBIC_METERS,
                )
                _meter_2_reading = None
                if meter_step_factor < 0:
                    _meter_2_reading = meter_reading_values["1"] * abs(
                        meter_step_factor
                    )
                else:
                    _meter_2_reading = meter_reading_values["1"] / meter_step_factor
                meter_reading_values["1"] = VolumeConverter.convert(
                    _meter_2_reading,
                    meter_unit,
                    UnitOfVolume.CUBIC_METERS,
                )
                data["meter_1_reading"] = float(
                    Decimal(meter_reading_values["0"]).quantize(
                        Decimal(".00000"), rounding=ROUND_DOWN
                    )
                )
                data["meter_2_reading"] = float(
                    Decimal(meter_reading_values["1"]).quantize(
                        Decimal(".00000"), rounding=ROUND_DOWN
                    )
                )
            # for some reason meter value can't be read
            if (meter_valves := meter_state.get("valves")) is not None:
                data["valve_1_state"] = meter_valves["0"]
                data["valve_2_state"] = meter_valves["1"]

    async def set_valve(self, channel: int, opened: bool) -> BRDP:
        """Open or close the specified valve."""
        return await self.call_device(
            ClientRequest(
                "setState", {"valves": {str(channel): "open" if opened else "close"}}
            )
        )
