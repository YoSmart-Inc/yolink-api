"""Tests for MQTT message handling."""

import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from yolink.endpoint import Endpoints
from yolink.mqtt_client import YoLinkMqttClient


class MqttMessageHandlingTest(unittest.IsolatedAsyncioTestCase):
    async def test_bad_message_and_listener_error_do_not_interrupt_subscription(self):
        received = asyncio.Event()
        calls = []
        device = SimpleNamespace(
            device_type="Switch", get_paired_device_id=lambda: None
        )
        payload = b'{"event":"Switch.Report","data":{"state":"on"}}'
        messages = [
            SimpleNamespace(topic="yl-home/home/device/report", retain=False, payload=data)
            for data in (b"\xff", payload, payload)
        ]

        class FakeClient:
            def __init__(self, **kwargs):
                self.messages = self.iter_messages()

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return None

            async def subscribe(self, topic):
                pass

            async def iter_messages(self):
                for message in messages:
                    yield message
                await asyncio.Event().wait()

        class Auth:
            async def check_and_refresh_token(self):
                return "token"

        class Listener:
            def on_message(self, device, data):
                calls.append(data)
                if len(calls) == 1:
                    raise ValueError("listener error")
                received.set()

        client = YoLinkMqttClient(Auth(), Endpoints.US.value, "localhost", 1883, {"device": device})
        with (
            patch("yolink.mqtt_client.Client", FakeClient),
            self.assertLogs("yolink.mqtt_client", level="ERROR") as logs,
        ):
            await client.connect("yl-home/home/+/report", Listener())
            task = client._listener_task
            try:
                await asyncio.wait_for(received.wait(), timeout=1)
                self.assertEqual(len(calls), 2)
                self.assertEqual(len(logs.records), 2)
            finally:
                await client.disconnect()
                with self.assertRaises(asyncio.CancelledError):
                    await task
