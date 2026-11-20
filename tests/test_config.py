"""Message conversion configuration behavior."""

import unittest
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from yolink.config import YoLinkConfig, config
from yolink.device import YoLinkDeviceMode
from yolink.devices import create_device
from yolink.endpoint import Endpoints
from yolink.model import BRDP
from yolink.mqtt_client import YoLinkMqttClient


def device(kind):
    return create_device(
        YoLinkDeviceMode(deviceId="id", name="device", token="token", type=kind), None
    )


class MessageConversionConfigTest(unittest.IsolatedAsyncioTestCase):
    def test_default_enabled(self):
        self.assertTrue(YoLinkConfig().enable_message_conversion)

    def test_sprinkler_skips_mode_cache_while_conversion_is_disabled(self):
        sprinkler = device("Sprinkler")
        with patch.object(config, "enable_message_conversion", False):
            sprinkler.resolve_message({"state": {"mode": "auto"}}, "Report")
        with patch.object(config, "enable_message_conversion", True):
            report = {"event": "start"}
            sprinkler.resolve_message(report, "waterReport")
        self.assertEqual(report["state"], {"mode": None})
        self.assertTrue(report["valve"])

    def test_disabled_leaves_all_conversion_payloads_unchanged(self):
        cases = {
            "THSensor": {"records": [{"time": 1, "temperature": 20}]},
            "SmartRemoter": {"event": {"keyMask": 4}},
            "SoilThcSensor": {"state": {"temperature": 20}},
            "Sprinkler": {
                "state": {"mode": "auto", "watering": {"left": 1, "total": 2}}
            },
            "SprinklerV2": {"state": {"running": True}},
            "WaterDepthSensor": {"waterDepth": 500},
            "WaterMeterController": {"state": {"meter": 100, "valve": "open"}},
            "WaterMeterMultiController": {"state": {"meters": {"0": 100, "1": 200}}},
        }
        with patch.object(config, "enable_message_conversion", False):
            for kind, original in cases.items():
                with self.subTest(kind=kind):
                    data = deepcopy(original)
                    device(kind).resolve_message(data, "Report")
                    self.assertEqual(data, original)

    async def test_disabled_fetch_preserves_raw_data_and_timestamp(self):
        sensor = device("WaterDepthSensor")
        response = BRDP(
            code="000000",
            data={"reportAt": "2026-01-02T00:00:00Z", "state": {"waterDepth": 500}},
        )
        sensor._client = AsyncMock()
        sensor._client.execute.return_value = response
        with patch.object(config, "enable_message_conversion", False):
            self.assertIs(await sensor.fetch_state(), response)
        self.assertEqual(response.data["state"], {"waterDepth": 500})
        self.assertIsNotNone(sensor.last_report_at)

    def test_disabled_mqtt_skips_device_parsing_but_updates_timestamp(self):
        hub = device("Hub")
        siren = device("Siren")
        received = []
        mqtt = YoLinkMqttClient(
            None, Endpoints.US.value, "localhost", 1883, {"id": hub}
        )
        mqtt._message_listener = SimpleNamespace(
            on_message=lambda dev, data: received.append(data)
        )
        with patch.object(config, "enable_message_conversion", False):
            mqtt._process_message(
                SimpleNamespace(
                    topic="yl-home/home/id/report",
                    retain=False,
                    payload=b'{"event":"Hub.Report","time":1794827145820,"data":{"online":true}}',
                )
            )
            siren.resolve_message({"state": "off"}, "Report")
        self.assertEqual(received, [{"online": True}])
        self.assertFalse(hub.is_online())
        self.assertIsNotNone(hub.last_report_at)
        self.assertEqual(siren._state, {})
