"""Tests for concrete YoLink device classes and online detection."""

import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

from yolink.device import YoLinkDevice, YoLinkDeviceMode
from yolink.device_feature import DeviceFeature
from yolink.device_net_type import DeviceNetType
from yolink.devices import (
    DEVICE_TYPE_CLASSES,
    YoLinkMultiOutlet,
    YoLinkSwitch,
    YoLinkTHSensor,
    create_device,
)
from yolink.devices.thermostat import ThermostatState
from yolink.model import BRDP


def make_device(device_type: str, model: str | None = "YS0000-UC") -> YoLinkDevice:
    device = YoLinkDeviceMode(
        deviceId="device-id",
        name="Device",
        token="token",
        type=device_type,
        modelName=model,
    )
    return create_device(device, object())


class DeviceClassTest(unittest.TestCase):
    def test_current_network_type_tracks_reports(self) -> None:
        device = make_device("WaterMeterController", "YS5009-UC")
        self.assertIsNone(device.current_net_type)
        device.resolve_message({"loraInfo": {"devNetType": "A"}})
        self.assertEqual(device.current_net_type, "A")
        device.resolve_message({})
        self.assertEqual(device.current_net_type, "A")
        device.resolve_message({"loraInfo": {"devNetType": "D"}})
        self.assertEqual(device.current_net_type, "D")

    def test_battery_support(self) -> None:
        for device_type, expected in (
            ("DoorSensor", True),
            ("THSensor", True),
            ("WaterMeterMultiController", True),
            ("SpeakerHub", False),
            ("Outlet", False),
        ):
            with self.subTest(device_type=device_type):
                self.assertIs(make_device(device_type).support_battery(), expected)

    def test_model_specific_features(self) -> None:
        for device_type, model, present, absent in (
            (
                "MultiOutlet",
                "YS6803-UC",
                DeviceFeature.POWER,
                DeviceFeature.HUMIDITY,
            ),
            (
                "Outlet",
                "YS6614-EC",
                DeviceFeature.POWER,
                DeviceFeature.HUMIDITY,
            ),
            (
                "WaterMeterController",
                "YS5007-UC",
                DeviceFeature.WATER_METER,
                DeviceFeature.VALVE,
            ),
            (
                "WaterMeterController",
                "YS5018-EC",
                DeviceFeature.WATER_FLOW,
                DeviceFeature.ESTIMATED_TEMPERATURE,
            ),
        ):
            with self.subTest(device_type=device_type, model=model):
                device = make_device(device_type, model)
                self.assertTrue(device.supports_any_feature(present))
                self.assertFalse(device.supports_any_feature(absent))

    def test_water_meter_temperature_and_flow(self) -> None:
        for model in ("YS5018", "YS5018-UC", "YS5018-EC", "YS5018-CN"):
            with self.subTest(model=model):
                features = make_device(
                    "WaterMeterController", model
                ).supported_features()
                self.assertIn(DeviceFeature.WATER_TEMPERATURE, features)
                self.assertIn(DeviceFeature.WATER_FLOW, features)

    def test_supports_any_feature(self) -> None:
        device = make_device("THSensor", "YS8004-UC")

        self.assertTrue(
            device.supports_any_feature(
                DeviceFeature.HUMIDITY, DeviceFeature.TEMPERATURE
            )
        )
        self.assertFalse(
            device.supports_any_feature(
                DeviceFeature.HUMIDITY, DeviceFeature.WATER_FLOW
            )
        )
        self.assertFalse(device.supports_any_feature())

    def test_speaker_hub_feature(self) -> None:
        self.assertTrue(
            make_device("SpeakerHub").supports_any_feature(DeviceFeature.SPEAKER_HUB)
        )
        self.assertFalse(
            make_device("Hub").supports_any_feature(DeviceFeature.SPEAKER_HUB)
        )

    def test_outlet_power_monitoring(self) -> None:
        for device_type in ("Outlet", "MultiOutlet"):
            for model in ("YS6602", "YS6614", "YS6803"):
                for suffix in ("", "-UC", "-EC", "-CN"):
                    with self.subTest(
                        device_type=device_type, model=model, suffix=suffix
                    ):
                        device = make_device(device_type, f"{model}{suffix}")
                        self.assertTrue(
                            device.supports_any_feature(DeviceFeature.POWER)
                        )
            self.assertFalse(
                make_device(device_type, "YS6801-UC").supports_any_feature(
                    DeviceFeature.POWER
                )
            )

    def test_multi_outlet_count(self) -> None:
        for model, outlet_count, has_usb in (
            ("YS6801-UC", 4, True),
            ("YS6803-UC", 2, False),
        ):
            with self.subTest(model=model):
                device = make_device("MultiOutlet", model)
                self.assertIsInstance(device, YoLinkMultiOutlet)
                self.assertEqual(device.outlet_count, outlet_count)
                self.assertIs(device.has_usb_ports, has_usb)

    def test_temperature_only_models(self) -> None:
        for model in ("YS8004", "YS8008", "YS8014", "YS8017"):
            for suffix in ("", "-UC", "-EC", "-CN"):
                with self.subTest(model=model, suffix=suffix):
                    sensor = make_device("THSensor", f"{model}{suffix}")
                    self.assertEqual(
                        sensor.supported_features()
                        & {DeviceFeature.TEMPERATURE, DeviceFeature.HUMIDITY},
                        {DeviceFeature.TEMPERATURE},
                    )

    def test_other_temperature_models(self) -> None:
        for model in ("YS8003-UC", "YS8005-EC", None):
            with self.subTest(model=model):
                sensor = make_device("THSensor", model)
                self.assertEqual(
                    sensor.supported_features()
                    & {DeviceFeature.TEMPERATURE, DeviceFeature.HUMIDITY},
                    {DeviceFeature.TEMPERATURE, DeviceFeature.HUMIDITY},
                )

    def test_mode_switching_is_specific_to_supported_water_meters(self):
        for device_type, supported_model, other_model in (
            ("WaterMeterController", "YS5009", "YS5029"),
            ("WaterMeterMultiController", "YS5029", "YS5009"),
        ):
            for suffix in ("", "-UC", "-EC", "-CN"):
                with self.subTest(device_type=device_type, suffix=suffix):
                    self.assertTrue(
                        make_device(
                            device_type, f"{supported_model}{suffix}"
                        ).is_support_mode_switching()
                    )
                    self.assertFalse(
                        make_device(
                            device_type, f"{other_model}{suffix}"
                        ).is_support_mode_switching()
                    )
            self.assertFalse(
                make_device(device_type, "YS5008-UC").is_support_mode_switching()
            )

    @patch("yolink.device.datetime", wraps=datetime)
    def test_siren_offline_state_and_timeout(self, clock):
        now = datetime(2026, 11, 17, tzinfo=timezone.utc)
        clock.now.return_value = now
        for model in ("YS7103-UC", "YS7104-UC"):
            with self.subTest(model=model):
                siren = make_device("Siren", model)
                siren.update_last_report_at(now)
                siren.resolve_message({"state": "off"}, "Report")
                self.assertFalse(siren.is_online())
                siren.resolve_message({"battery": 4}, "Report")
                self.assertFalse(siren.is_online())
                siren.resolve_message({"state": "normal"}, "StatusChange")
                self.assertTrue(siren.is_online())
                clock.now.return_value = now + timedelta(seconds=siren.keepalive_time)
                self.assertFalse(siren.is_online())
                clock.now.return_value = now

    def test_device_model_uses_api_aliases_and_normalizes_parent(self):
        model = YoLinkDeviceMode(
            deviceId="id",
            name="Name",
            token="token",
            type="Switch",
            modelName="YS5709-EC",
            parentDeviceId="null",
            serviceZone="eu_1",
            appEui="0000005709",
        )
        self.assertEqual(
            (model.id, model.name, model.token, model.type),
            ("id", "Name", "token", "Switch"),
        )
        self.assertIsNone(model.parent_id)
        self.assertEqual(model.model_dump(by_alias=True)["deviceId"], "id")
        device = create_device(model, object())
        self.assertIsInstance(device, YoLinkSwitch)
        self.assertEqual(device.model, "YS5709")
        self.assertEqual(device.endpoint.name, "EU")

    def test_device_message_parsers(self):
        sensor = make_device("THSensor")
        data = {
            "records": [{"time": 1, "temperature": 10}, {"time": 2, "temperature": 20}]
        }
        sensor.resolve_message(data)
        self.assertEqual(data["temperature"], 20)

        sprinkler = make_device("Sprinkler")
        sprinkler.resolve_message({"state": {"mode": "auto"}})
        report = {"event": "start"}
        sprinkler.resolve_message(report, event_type="waterReport")
        self.assertEqual(
            report, {"event": "start", "state": {"mode": "auto"}, "valve": True}
        )

        remote = make_device("SmartRemoter")
        event = {"event": {"keyMask": 4}}
        remote.resolve_message(event, event_type="Alert")
        self.assertEqual(event["event"]["keyMask"], 3)
        remote.resolve_message(event, "Report")
        self.assertIsNone(event["event"])

        base = YoLinkDevice(
            YoLinkDeviceMode(
                deviceId="id", name="x", token="t", type="WaterDepthSensor"
            ),
            object(),
        )
        depth = {"waterDepth": 500}
        base.resolve_message(depth)
        self.assertEqual(depth["waterDepth"], 500)
        make_device("WaterDepthSensor").resolve_message(depth)
        self.assertEqual(depth["waterDepth"], 2.5)

    def test_factory_creates_every_registered_device_subclass(self):
        for device_type, device_class in DEVICE_TYPE_CLASSES.items():
            with self.subTest(device_type=device_type):
                self.assertIsInstance(make_device(device_type), device_class)

    def test_factory_skips_unknown_type(self):
        with self.assertLogs("yolink.devices.factory", level="WARNING") as logs:
            device = make_device("Unknown")
        self.assertIsNone(device)
        self.assertIn(
            "Unsupported YoLink device type: Unknown, name: Device, ID: device-id",
            logs.output[0],
        )

    @patch("yolink.device.datetime", wraps=datetime)
    def test_online_timeout_uses_device_type_and_model(self, mock_datetime):
        now = datetime(2026, 11, 17, 12, tzinfo=timezone.utc)
        mock_datetime.now.return_value = now
        class_c_switch = make_device("Switch", "YS5706-UC")
        class_d_switch = make_device("Switch", "YS5709-UC")
        th_sensor = make_device("THSensor", "YS8003-UC")

        self.assertIsInstance(class_c_switch, YoLinkSwitch)
        self.assertIsInstance(class_d_switch, YoLinkSwitch)
        self.assertIsInstance(th_sensor, YoLinkTHSensor)
        for device, timeout in (
            (class_c_switch, 1),
            (class_d_switch, 9),
            (th_sensor, 3),
        ):
            with self.subTest(timeout=timeout):
                self.assertFalse(device.is_online())
                device.update_last_report_at(now - timedelta(hours=timeout))
                self.assertFalse(device.is_online())
                device.update_last_report_at(
                    now - timedelta(hours=timeout) + timedelta(seconds=1)
                )
                self.assertTrue(device.is_online())

    def test_class_e_timeout(self):
        device = make_device("Switch")
        device.class_mode = DeviceNetType.E
        self.assertEqual(device.keepalive_time, 3600)

    @patch("yolink.device.datetime", wraps=datetime)
    def test_online_accepts_api_time_formats(self, mock_datetime):
        now = datetime(2026, 11, 17, 12, tzinfo=timezone.utc)
        mock_datetime.now.return_value = now
        for report_at in (
            "2026-11-17T11:30:00.000Z",
            now.timestamp() - 1800,
            (now.timestamp() - 1800) * 1000,
        ):
            with self.subTest(report_at=report_at):
                device = make_device("Outlet", "YS6604-UC")
                device.update_last_report_at(report_at)
                self.assertTrue(device.is_online())
        device = make_device("Outlet", "YS6604-UC")
        device.update_last_report_at("invalid")
        self.assertFalse(device.is_online())


class SirenStateTest(unittest.IsolatedAsyncioTestCase):
    async def test_fetched_and_realtime_state_update_power_status(self):
        siren = make_device("Siren", "YS7104-UC")
        siren._client = AsyncMock()
        siren._client.execute.return_value = BRDP(
            code="000000",
            data={
                "reportAt": datetime.now(timezone.utc).isoformat(),
                "state": {"state": "off"},
            },
        )
        await siren.fetch_state()
        self.assertFalse(siren.is_online())
        siren._client.execute.return_value = BRDP(
            code="000000", data={"state": "normal"}
        )
        await siren.get_state()
        self.assertTrue(siren.is_online())


class ThermostatControlTest(unittest.IsolatedAsyncioTestCase):
    async def test_fetch_state_tracks_newest_report_time(self):
        device = make_device("Switch")
        self.assertIsNone(device.last_report_at)
        device._client = AsyncMock()
        device._client.execute.side_effect = [
            BRDP(code="000000", data={"reportAt": "2026-01-02T00:00:00Z", "state": {}}),
            BRDP(code="000000", data={"reportAt": "2026-01-01T00:00:00Z", "state": {}}),
            BRDP(code="000000", data={"reportAt": "invalid", "state": {}}),
        ]
        await device.fetch_state()
        expected = datetime(2026, 1, 2, tzinfo=timezone.utc)
        self.assertEqual(device.last_report_at, expected)
        await device.fetch_state()
        await device.fetch_state()
        self.assertEqual(device.last_report_at, expected)

    async def test_outlet_style_set_state(self):
        for device_type in ("Outlet", "MultiOutlet", "Switch", "Manipulator"):
            with self.subTest(device_type=device_type):
                device = make_device(device_type)
                response = BRDP(code="000000", data={})
                device._client = AsyncMock()
                device._client.execute.return_value = response
                self.assertIs(await device.set_state("open"), response)
                request = device._client.execute.await_args.kwargs["bsdp"]
                self.assertEqual(request["method"], f"{device_type}.setState")
                self.assertEqual(request["params"], {"state": "open"})
                self.assertIs(await device.set_state("close", 2), response)
                request = device._client.execute.await_args.kwargs["bsdp"]
                self.assertEqual(request["params"], {"state": "close", "chs": 4})

    async def test_commands_return_response_and_send_expected_parameters(self):
        device = make_device("Thermostat")
        response = BRDP(code="000000", data={})
        device._client = AsyncMock()
        device._client.execute.return_value = response

        self.assertIs(
            await device.set_state(ThermostatState(lowTemp=68, mode="heat")), response
        )
        request = device._client.execute.await_args.kwargs["bsdp"]
        self.assertEqual(request["method"], "Thermostat.setState")
        self.assertEqual(request["params"], {"lowTemp": 68.0, "mode": "heat"})

        self.assertIs(await device.set_eco("on"), response)
        request = device._client.execute.await_args.kwargs["bsdp"]
        self.assertEqual(request["method"], "Thermostat.setECO")
        self.assertEqual(request["params"], {"mode": "on"})


class DeviceCommandsTest(unittest.IsolatedAsyncioTestCase):
    async def test_device_command_payloads(self) -> None:
        for device_type, command, args, kwargs, method, params in (
            (
                "Dimmer",
                "set_state",
                ("open", 40),
                {},
                "setState",
                {"state": "open", "brightness": 40},
            ),
            ("Dimmer", "set_state", ("close",), {}, "setState", {"state": "close"}),
            ("Finger", "toggle", (), {}, "toggle", {}),
            ("GarageDoor", "toggle", (), {}, "toggle", {}),
            (
                "Siren",
                "set_alarm",
                (False,),
                {},
                "setState",
                {"state": {"alarm": False}},
            ),
            ("SpeakerHub", "set_volume", (3,), {}, "setOption", {"volume": 3}),
            (
                "SpeakerHub",
                "play_audio",
                ("Hello",),
                {},
                "playAudio",
                {"message": "Hello", "repeat": 0},
            ),
            (
                "SpeakerHub",
                "play_audio",
                ("Hello",),
                {"repeat": 2, "volume": 0, "tone": "alert"},
                "playAudio",
                {"message": "Hello", "repeat": 2, "volume": 0, "tone": "Alert"},
            ),
            (
                "Sprinkler",
                "set_mode",
                ("manual",),
                {},
                "setState",
                {"state": {"mode": "manual"}},
            ),
            (
                "Sprinkler",
                "set_valve",
                (True,),
                {},
                "setManualWater",
                {"state": "start"},
            ),
            ("SprinklerV2", "set_valve", (False,), {}, "setState", {"running": False}),
            (
                "WaterMeterController",
                "set_valve",
                (True,),
                {},
                "setState",
                {"valve": "open"},
            ),
            (
                "WaterMeterMultiController",
                "set_valve",
                (1, False),
                {},
                "setState",
                {"valves": {"1": "close"}},
            ),
        ):
            with self.subTest(device_type=device_type, command=command, args=args):
                device = make_device(device_type)
                response = BRDP(code="000000", data={})
                device._client = AsyncMock()
                device._client.execute.return_value = response

                self.assertIs(await getattr(device, command)(*args, **kwargs), response)
                device._client.execute.assert_awaited_once()
                request = device._client.execute.await_args.kwargs["bsdp"]
                self.assertEqual(request["method"], f"{device_type}.{method}")
                self.assertEqual(request["params"], params)

    async def test_lock_and_unlock_commands(self) -> None:
        for device_type, locked, unlocked in (
            ("Lock", {"state": "lock"}, {"state": "unlock"}),
            ("LockV2", {"state": {"lock": "locked"}}, {"state": {"lock": "unlocked"}}),
        ):
            with self.subTest(device_type=device_type):
                device = make_device(device_type)
                response = BRDP(code="000000", data={})
                device._client = AsyncMock()
                device._client.execute.return_value = response

                self.assertIs(await device.lock(), response)
                lock_request = device._client.execute.await_args.kwargs["bsdp"]
                self.assertEqual(lock_request["method"], f"{device_type}.setState")
                self.assertEqual(lock_request["params"], locked)

                self.assertIs(await device.unlock(), response)
                unlock_request = device._client.execute.await_args.kwargs["bsdp"]
                self.assertEqual(unlock_request["method"], f"{device_type}.setState")
                self.assertEqual(unlock_request["params"], unlocked)
