"""Const for YoLink Client."""

from typing import Final

OAUTH2_AUTHORIZE = "https://api.yosmart.com/oauth/v2/authorization.htm"
OAUTH2_TOKEN = "https://api.yosmart.com/open/yolink/token"

ATTR_DEVICE_ID = "deviceId"
ATTR_DEVICE_NAME = "name"
ATTR_DEVICE_TYPE = "type"
ATTR_DEVICE_TOKEN = "token"
ATTR_DEVICE_MODEL_NAME = "modelName"
ATTR_DEVICE_PARENT_ID = "parentDeviceId"
ATTR_DEVICE_SERVICE_ZONE = "serviceZone"

ATTR_DEVICE_MODEL_A = "A"
ATTR_DEVICE_MODEL_C = "C"
ATTR_DEVICE_MODEL_D = "D"

ATTR_DEVICE_DOOR_SENSOR = "DoorSensor"
ATTR_DEVICE_TH_SENSOR = "THSensor"
ATTR_DEVICE_MOTION_SENSOR = "MotionSensor"
ATTR_DEVICE_MULTI_OUTLET = "MultiOutlet"
ATTR_DEVICE_LEAK_SENSOR = "LeakSensor"
ATTR_DEVICE_VIBRATION_SENSOR = "VibrationSensor"
ATTR_DEVICE_OUTLET = "Outlet"
ATTR_DEVICE_SIREN = "Siren"
ATTR_DEVICE_LOCK = "Lock"
ATTR_DEVICE_MANIPULATOR = "Manipulator"
ATTR_DEVICE_CO_SMOKE_SENSOR = "COSmokeSensor"
ATTR_DEVICE_SWITCH = "Switch"
ATTR_DEVICE_THERMOSTAT = "Thermostat"
ATTR_DEVICE_DIMMER = "Dimmer"
ATTR_GARAGE_DOOR_CONTROLLER = "GarageDoor"
ATTR_DEVICE_SMART_REMOTER = "SmartRemoter"
ATTR_DEVICE_POWER_FAILURE_ALARM = "PowerFailureAlarm"
ATTR_DEVICE_HUB = "Hub"
ATTR_DEVICE_SPEAKER_HUB = "SpeakerHub"
ATTR_DEVICE_FINGER = "Finger"
ATTR_DEVICE_WATER_DEPTH_SENSOR = "WaterDepthSensor"
ATTR_DEVICE_WATER_METER_CONTROLLER = "WaterMeterController"
ATTR_DEVICE_MULTI_WATER_METER_CONTROLLER = "WaterMeterMultiController"
ATTR_DEVICE_LOCK_V2 = "LockV2"

UNIT_NOT_RECOGNIZED_TEMPLATE: Final = "{} is not a recognized {} unit."
