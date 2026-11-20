"""Concrete YoLink device classes."""

from .co_smoke_sensor import YoLinkCOSmokeSensor
from .dimmer import YoLinkDimmer
from .door_sensor import YoLinkDoorSensor
from .factory import DEVICE_TYPE_CLASSES, create_device
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

__all__ = [
    "DEVICE_TYPE_CLASSES",
    "YoLinkCOSmokeSensor",
    "YoLinkDimmer",
    "YoLinkDoorSensor",
    "YoLinkFinger",
    "YoLinkGarageDoor",
    "YoLinkHub",
    "YoLinkLeakSensor",
    "YoLinkLock",
    "YoLinkLockV2",
    "YoLinkManipulator",
    "YoLinkMotionSensor",
    "YoLinkMultiCapsLeakSensor",
    "YoLinkMultiOutlet",
    "YoLinkMultifunctionalSensor",
    "YoLinkOutlet",
    "YoLinkPowerFailureAlarm",
    "YoLinkSiren",
    "YoLinkSmartRemoter",
    "YoLinkSmokeAlarm",
    "YoLinkSoilThcSensor",
    "YoLinkSpeakerHub",
    "YoLinkSprinkler",
    "YoLinkSprinklerV2",
    "YoLinkSwitch",
    "YoLinkTHSensor",
    "YoLinkTHSensorV2",
    "YoLinkThermostat",
    "YoLinkVibrationSensor",
    "YoLinkWaterDepthSensor",
    "YoLinkWaterMeterController",
    "YoLinkWaterMeterMultiController",
    "create_device",
]
