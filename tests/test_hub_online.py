"""Hub connectivity behavior based on network messages."""

import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from yolink.device import YoLinkDeviceMode
from yolink.devices import create_device
from yolink.endpoint import Endpoints
from yolink.model import BRDP
from yolink.mqtt_client import YoLinkMqttClient


def make_hub(device_type="Hub", model="YS1603-UC"):
    return create_device(
        YoLinkDeviceMode(
            deviceId="hub", name="Hub", token="token", type=device_type, modelName=model
        ),
        None,
    )


class HubOnlineTest(unittest.IsolatedAsyncioTestCase):
    async def test_get_state_updates_online(self):
        hub = make_hub()
        hub._client = AsyncMock()
        response = BRDP(code="000000", data={"online": True})
        hub._client.execute.return_value = response
        self.assertIs(await hub.get_state(), response)
        self.assertTrue(hub.is_online())
        self.assertEqual(
            hub._client.execute.await_args.kwargs["bsdp"]["method"], "Hub.getState"
        )

    async def test_fetch_uses_explicit_online_and_returns_response(self):
        for device_type in ("Hub", "SpeakerHub"):
            with self.subTest(device_type=device_type):
                hub = make_hub(device_type)
                response = BRDP(
                    code="000000",
                    data={
                        "online": False,
                        "reportAt": "2026-06-26T08:16:37.537Z",
                        "state": {
                            "online": False,
                            "networkInfo": {"ylgmq": {"connected": False}},
                        },
                    },
                )
                hub._client = AsyncMock()
                hub._client.execute.return_value = response
                self.assertIs(await hub.fetch_state(), response)
                self.assertFalse(hub.is_online())
                self.assertEqual(
                    hub.last_report_at,
                    datetime(2026, 6, 26, 8, 16, 37, 537000, tzinfo=timezone.utc),
                )
                self.assertEqual(
                    hub._client.execute.await_args.kwargs["bsdp"]["method"],
                    f"{device_type}.fetchState",
                )

    def test_network_info_and_lora_fallback(self):
        hub = make_hub()
        now = datetime(2026, 11, 17, tzinfo=timezone.utc)
        with patch("yolink.devices.hub.datetime", wraps=datetime) as clock:
            clock.now.return_value = now
            hub.update_last_report_at(now - timedelta(minutes=130))
            hub.resolve_message(
                {
                    "networkInfo": {
                        "ylgmq": {"connected": False},
                        "lora": {"signal": -60},
                    }
                },
                "Report",
            )
            self.assertFalse(hub.is_online())
            hub.update_last_report_at(now - timedelta(minutes=129))
            hub.resolve_message({}, "Report")
            self.assertTrue(hub.is_online())
            hub.resolve_message(
                {"networkInfo": {"ylgmq": {"connected": False}}}, "Report"
            )
            self.assertTrue(hub.is_online())

    def test_connected_and_siren_hub_explicit_offline(self):
        hub = make_hub()
        hub.resolve_message({"networkInfo": {"ylgmq": {"connected": True}}}, "Report")
        self.assertTrue(hub.is_online())
        siren_hub = make_hub("SpeakerHub", "YS1614-UC")
        siren_hub.resolve_message({}, "Report")
        self.assertTrue(siren_hub.is_online())
        siren_hub.resolve_message({"online": False}, "StatusChange")
        self.assertFalse(siren_hub.is_online())

    def test_mqtt_updates_hub_before_listener(self):
        hub = make_hub()
        seen = []
        mqtt = YoLinkMqttClient(
            None, Endpoints.US.value, "localhost", 1883, {"hub": hub}
        )
        mqtt._message_listener = SimpleNamespace(
            on_message=lambda device, data: seen.append(device.is_online())
        )
        mqtt._process_message(
            SimpleNamespace(
                topic="yl-home/home/hub/report",
                retain=False,
                payload=b'{"event":"Hub.StatusChange","data":{"online":false}}',
            )
        )
        self.assertEqual(seen, [False])
        mqtt._process_message(
            SimpleNamespace(
                topic="yl-home/home/hub/report",
                retain=False,
                payload=b'{"event":"Hub.Report","data":{"networkInfo":{"ylgmq":{"connected":true}}}}',
            )
        )
        self.assertEqual(seen, [False, True])
