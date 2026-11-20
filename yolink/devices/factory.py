"""Concrete YoLink device class registry and factory."""

import logging

from ..http_client import YoLinkHttpClient
from ..const import (
    ATTR_DEVICE_CO_SMOKE_SENSOR,
    ATTR_DEVICE_DIMMER,
    ATTR_DEVICE_DOOR_SENSOR,
    ATTR_DEVICE_FINGER,
    ATTR_DEVICE_HUB,
    ATTR_DEVICE_LEAK_SENSOR,
    ATTR_DEVICE_LOCK,
    ATTR_DEVICE_LOCK_V2,
    ATTR_DEVICE_MANIPULATOR,
    ATTR_DEVICE_MOTION_SENSOR,
    ATTR_DEVICE_MULTI_CAPS_LEAK_SENSOR,
    ATTR_DEVICE_MULTI_FUNCTIONAL_SENSOR,
    ATTR_DEVICE_MULTI_OUTLET,
    ATTR_DEVICE_MULTI_WATER_METER_CONTROLLER,
    ATTR_DEVICE_OUTLET,
    ATTR_DEVICE_POWER_FAILURE_ALARM,
    ATTR_DEVICE_SIREN,
    ATTR_DEVICE_SMART_REMOTER,
    ATTR_DEVICE_SMOKE_ALARM,
    ATTR_DEVICE_SOIL_TH_SENSOR,
    ATTR_DEVICE_SPEAKER_HUB,
    ATTR_DEVICE_SPRINKLER,
    ATTR_DEVICE_SPRINKLER_V2,
    ATTR_DEVICE_SWITCH,
    ATTR_DEVICE_TH_SENSOR,
    ATTR_DEVICE_TH_SENSOR_V2,
    ATTR_DEVICE_THERMOSTAT,
    ATTR_DEVICE_VIBRATION_SENSOR,
    ATTR_DEVICE_WATER_DEPTH_SENSOR,
    ATTR_DEVICE_WATER_METER_CONTROLLER,
    ATTR_GARAGE_DOOR_CONTROLLER,
)
from ..device import YoLinkDevice, YoLinkDeviceMode
from .co_smoke_sensor import YoLinkCOSmokeSensor
from .dimmer import YoLinkDimmer
from .door_sensor import YoLinkDoorSensor
from .finger import YoLinkFinger
from .garage_door import YoLinkGarageDoor
from .hub import YoLinkHub
from .leak_sensor import YoLinkLeakSensor
from .lock import YoLinkLock
from .lock_v2 import YoLinkLockV2
from .manipulator import YoLinkManipulator
from .motion_sensor import YoLinkMotionSensor
from .multi_caps_leak_sensor import YoLinkMultiCapsLeakSensor
from .multi_outlet import YoLinkMultiOutlet
from .multifunctional_sensor import YoLinkMultifunctionalSensor
from .outlet import YoLinkOutlet
from .power_failure_alarm import YoLinkPowerFailureAlarm
from .siren import YoLinkSiren
from .smart_remoter import YoLinkSmartRemoter
from .smoke_alarm import YoLinkSmokeAlarm
from .soil_thc_sensor import YoLinkSoilThcSensor
from .speaker_hub import YoLinkSpeakerHub
from .sprinkler import YoLinkSprinkler
from .sprinkler_v2 import YoLinkSprinklerV2
from .switch import YoLinkSwitch
from .th_sensor import YoLinkTHSensor
from .th_sensor_v2 import YoLinkTHSensorV2
from .thermostat import YoLinkThermostat
from .vibration_sensor import YoLinkVibrationSensor
from .water_depth_sensor import YoLinkWaterDepthSensor
from .water_meter_controller import YoLinkWaterMeterController
from .water_meter_multi_controller import YoLinkWaterMeterMultiController

_LOGGER = logging.getLogger(__name__)

DEVICE_TYPE_CLASSES: dict[str, type[YoLinkDevice]] = {
    ATTR_DEVICE_DOOR_SENSOR: YoLinkDoorSensor,
    ATTR_DEVICE_TH_SENSOR: YoLinkTHSensor,
    ATTR_DEVICE_TH_SENSOR_V2: YoLinkTHSensorV2,
    ATTR_DEVICE_MOTION_SENSOR: YoLinkMotionSensor,
    ATTR_DEVICE_MULTI_OUTLET: YoLinkMultiOutlet,
    ATTR_DEVICE_LEAK_SENSOR: YoLinkLeakSensor,
    ATTR_DEVICE_MULTI_CAPS_LEAK_SENSOR: YoLinkMultiCapsLeakSensor,
    ATTR_DEVICE_VIBRATION_SENSOR: YoLinkVibrationSensor,
    ATTR_DEVICE_OUTLET: YoLinkOutlet,
    ATTR_DEVICE_SIREN: YoLinkSiren,
    ATTR_DEVICE_LOCK: YoLinkLock,
    ATTR_DEVICE_MANIPULATOR: YoLinkManipulator,
    ATTR_DEVICE_CO_SMOKE_SENSOR: YoLinkCOSmokeSensor,
    ATTR_DEVICE_SWITCH: YoLinkSwitch,
    ATTR_DEVICE_THERMOSTAT: YoLinkThermostat,
    ATTR_DEVICE_DIMMER: YoLinkDimmer,
    ATTR_GARAGE_DOOR_CONTROLLER: YoLinkGarageDoor,
    ATTR_DEVICE_SMART_REMOTER: YoLinkSmartRemoter,
    ATTR_DEVICE_POWER_FAILURE_ALARM: YoLinkPowerFailureAlarm,
    ATTR_DEVICE_HUB: YoLinkHub,
    ATTR_DEVICE_SPEAKER_HUB: YoLinkSpeakerHub,
    ATTR_DEVICE_FINGER: YoLinkFinger,
    ATTR_DEVICE_WATER_DEPTH_SENSOR: YoLinkWaterDepthSensor,
    ATTR_DEVICE_WATER_METER_CONTROLLER: YoLinkWaterMeterController,
    ATTR_DEVICE_MULTI_WATER_METER_CONTROLLER: YoLinkWaterMeterMultiController,
    ATTR_DEVICE_LOCK_V2: YoLinkLockV2,
    ATTR_DEVICE_SOIL_TH_SENSOR: YoLinkSoilThcSensor,
    ATTR_DEVICE_SPRINKLER: YoLinkSprinkler,
    ATTR_DEVICE_SPRINKLER_V2: YoLinkSprinklerV2,
    ATTR_DEVICE_SMOKE_ALARM: YoLinkSmokeAlarm,
    ATTR_DEVICE_MULTI_FUNCTIONAL_SENSOR: YoLinkMultifunctionalSensor,
}


def create_device(
    device: YoLinkDeviceMode, client: YoLinkHttpClient
) -> YoLinkDevice | None:
    """Create the concrete class for a YoLink device type."""
    if (device_class := DEVICE_TYPE_CLASSES.get(device.type)) is None:
        _LOGGER.warning(
            "Unsupported YoLink device type: %s, name: %s, ID: %s",
            device.type,
            device.name,
            device.id,
        )
        return None
    return device_class(device, client)
