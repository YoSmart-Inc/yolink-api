"""YoLink device capabilities."""

from enum import Enum


class DeviceFeature(str, Enum):
    """Capabilities a YoLink device can expose."""

    TEMPERATURE = "temperature"
    ESTIMATED_TEMPERATURE = "estimated_temperature"
    WATER_TEMPERATURE = "water_temperature"
    HUMIDITY = "humidity"
    CONDUCTIVITY = "conductivity"
    WATER_DEPTH = "water_depth"
    WATER_METER = "water_meter"
    CO_CONCENTRATION = "co_concentration"
    POWER = "power"
    SIGNAL_STRENGTH = "signal_strength"

    CO = "co"
    SMOKE = "smoke"
    MOTION = "motion"
    VIBRATION = "vibration"
    DOOR = "door"
    LEAK = "leak"
    WATER_FLOW = "water_flow"
    POWER_FAILURE = "power_failure"
    BEEP = "beep"
    VOLUME = "volume"
    MUTE = "mute"

    VALVE = "valve"
    SIREN = "siren"
    SPEAKER_HUB = "speaker_hub"
    THERMOSTAT = "thermostat"
    OUTLET = "outlet"
    SWITCH = "switch"
    DIMMER = "dimmer"
    LOCK = "lock"
    FINGER = "finger"
    GARAGE_DOOR = "garage_door"
