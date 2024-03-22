"""YoLink cloud message resolver."""

from typing import Any
from math import log2
from decimal import Decimal, ROUND_DOWN

from .unit_helper import UnitOfVolume, VolumeConverter


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
    if msg_data is not None:
        depth_value = msg_data.get("waterDepth")
        if depth_value is not None:
            # default range settings if range and desity was not set.
            dev_range = 5
            dev_density = 1
            if (
                dev_attrs is not None
                and (range_attrs := dev_attrs.get("range")) is not None
            ):
                dev_range = range_attrs["range"]
                dev_density = range_attrs["density"]
            msg_data["waterDepth"] = round(
                (dev_range * (depth_value / 1000)) / dev_density, 2
            )
    return msg_data


def water_meter_sensor_message_resolver(msg_data: dict[str, Any]) -> dict[str, Any]:
    """WaterMeterController message resolve."""
    if (meter_state := msg_data.get("state")) is None:
        return msg_data
    meter_step_factor: int = 10
    # for some reason meter value can't be read
    meter_value: int = meter_state.get("meter")
    if meter_value is not None:
        meter_unit = UnitOfVolume.GALLONS
        if (meter_attrs := msg_data.get("attributes")) is not None:
            meter_step_factor = (
                _meter_step_factor
                if (_meter_step_factor := meter_attrs.get("meterStepFactor"))
                is not None
                else 10
            )
            meter_unit = (
                UnitOfVolume(_meter_unit)
                if (_meter_unit := meter_attrs.get("meterUnit")) is not None
                else UnitOfVolume.GALLONS
            )
        meter_value = VolumeConverter.convert(
            meter_value / meter_step_factor, meter_unit, UnitOfVolume.CUBIC_METERS
        )
        msg_data["meter_reading"] = float(
            Decimal(meter_value).quantize(Decimal(".000"), rounding=ROUND_DOWN)
        )
    msg_data["valve_state"] = meter_state["valve"]
    return msg_data
