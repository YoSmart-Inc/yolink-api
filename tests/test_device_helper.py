"""Tests for device network classes and online timeouts."""

import unittest

from yolink.device import YoLinkDeviceMode
from yolink.device_net_type import DeviceNetType
from yolink.devices import create_device

CASES = [
    # Class A devices inherited from DeviceBloc in the app.
    ("LeakSensor", "YS7903-UC", "A", 9 * 3600),
    ("DoorSensor", "YS7704-UC", "A", 9 * 3600),
    ("MotionSensor", "YS7804-UC", "A", 9 * 3600),
    ("PowerFailureAlarm", "YS7106-UC", "A", 9 * 3600),
    ("VibrationSensor", "YS7201-UC", "A", 9 * 3600),
    ("SmartRemoter", "YS3604-UC", "A", 9 * 3600),
    ("WaterDepthSensor", "YS7905-UC", "A", 9 * 3600),
    ("SmokeAlarm", "YS7A12-UC", "A", 9 * 3600),
    ("Sprinkler", "YS4102-UC", "A", 9 * 3600),
    # Class A devices with model-specific Class D variants.
    ("COSmokeSensor", "YS7A01-UC", "A", 9 * 3600),
    ("COSmokeSensor", "YS7A02-UC", "D", 9 * 3600),
    ("SoilThcSensor", "YS8009-UC", "A", 9 * 3600),
    ("SoilThcSensor", "YS8006-UC", "D", 9 * 3600),
    ("MultiCapsLeakSensor", "YS7986-UC", "A", 9 * 3600),
    ("MultiCapsLeakSensor", "YS8006-UC", "D", 9 * 3600),
    # THSensor has an explicit three-hour override for every model.
    ("THSensor", "YS8003-UC", "A", 3 * 3600),
    ("THSensor", "YS8006-UC", "D", 3 * 3600),
    ("THSensorV2", "YS8003-UC", "A", 3 * 3600),
    # Fixed Class C devices.
    ("Outlet", "YS6604-UC", "C", 3600),
    ("MultiOutlet", "YS6801-UC", "C", 3600),
    ("Thermostat", "YS4002-UC", "C", 3600),
    ("GarageDoor", "YS4906-UC", "C", 3600),
    ("Dimmer", "YS5707-UC", "C", 3600),
    # Class C devices with model-specific Class D variants.
    ("Manipulator", "YS4908-UC", "C", 3600),
    ("Manipulator", "YS4909-UC", "D", 9 * 3600),
    ("Manipulator", "YS5012-UC", "D", 9 * 3600),
    ("Switch", "YS5706-UC", "C", 3600),
    ("Switch", "YS5709-UC", "D", 9 * 3600),
    ("Siren", "YS7103-UC", "C", 3600),
    ("Siren", "YS7104-UC", "D", 9 * 3600),
    ("Siren", "YS7107-UC", "D", 9 * 3600),
    # Fixed Class D device types.
    ("Finger", "YS4908-UC", "D", 9 * 3600),
    ("Lock", "YS7606-UC", "D", 9 * 3600),
    ("LockV2", "YS7616-UC", "D", 9 * 3600),
    ("SprinklerV2", "YS4103-UC", "D", 9 * 3600),
    ("MultifunctionalSensor", "Unknown", "A", 9 * 3600),
    # Water meter controller model branches.
    ("WaterMeterController", "YS5007-UC", "A", 9 * 3600),
    ("WaterMeterController", "YS5009-UC", "A", 9 * 3600),
    ("WaterMeterMultiController", "YS5029-UC", "A", 9 * 3600),
    ("WaterMeterMultiController", "YS5007-UC", "D", 9 * 3600),
    ("WaterMeterMultiController", "YS5009-UC", "D", 9 * 3600),
    ("WaterMeterController", "YS5008-UC", "D", 9 * 3600),
    # Hub behavior.
    ("Hub", "YS1603-UC", "Hub", 3600),
    ("SpeakerHub", "YS1604-UC", "Hub", 3600),
]


class TestDeviceNetworkClass(unittest.TestCase):
    def test_device_network_class_and_keepalive(self):
        for device_type, model, net_type, keepalive in CASES:
            with self.subTest(device_type=device_type, model=model):
                device = create_device(
                    YoLinkDeviceMode(
                        deviceId="id",
                        name="device",
                        token="token",
                        type=device_type,
                        modelName=model,
                    ),
                    None,
                )
                self.assertEqual(device.class_mode, net_type)
                self.assertEqual(device.net_type, net_type)
                if net_type is not None:
                    self.assertIs(device.class_mode, DeviceNetType(net_type))
                    self.assertIs(device.net_type, DeviceNetType(net_type))
                self.assertEqual(device.keepalive_time, keepalive)
