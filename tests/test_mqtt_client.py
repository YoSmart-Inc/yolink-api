"""Tests for MQTT message handling."""

import asyncio
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from yolink.device import YoLinkDeviceMode
from yolink.devices import create_device
from yolink.endpoint import Endpoints
from yolink.model import DeviceMessage
from yolink.mqtt_client import YoLinkMqttClient


class MqttMessageHandlingTest(unittest.IsolatedAsyncioTestCase):
    def test_device_message_parses_mqtt_envelope(self):
        message = DeviceMessage.model_validate_json(
            b'{"event":"THSensor.Report","time":1794827145820,'
            b'"msgid":"1794827141272","deviceId":"sensor",'
            b'"data":{"temperature":29.4}}'
        )
        self.assertEqual(message.device_id, "sensor")
        self.assertEqual(message.time, 1794827145820)
        self.assertEqual(message.msgid, "1794827141272")
        self.assertEqual(message.data, {"temperature": 29.4})

    def test_mqtt_timestamp_updates_last_report(self):
        device = create_device(
            YoLinkDeviceMode(
                deviceId="source", name="device", token="token", type="THSensor"
            ),
            None,
        )
        client = YoLinkMqttClient(
            None, Endpoints.US.value, "localhost", 1883, {"source": device}
        )
        message = SimpleNamespace(
            topic="yl-home/home/source/report",
            retain=False,
            payload=b'{"event":"THSensor.Report","time":1794827145820,"data":{"temperature":29.4}}',
        )
        client._process_message(message)
        self.assertEqual(
            device.last_report_at, datetime.fromtimestamp(1794827145.820, timezone.utc)
        )

    def test_mqtt_report_time_updates_source_before_listener(self):
        device = create_device(
            YoLinkDeviceMode(
                deviceId="source", name="device", token="token", type="Switch"
            ),
            None,
        )
        observed = []
        client = YoLinkMqttClient(
            None, Endpoints.US.value, "localhost", 1883, {"source": device}
        )
        client._message_listener = SimpleNamespace(
            on_message=lambda dev, data: observed.append(dev.last_report_at)
        )
        message = SimpleNamespace(
            topic="yl-home/home/source/report",
            retain=False,
            payload=b'{"event":"Switch.Report","data":{"state":"on","reportAt":"2026-01-02T00:00:00Z"}}',
        )
        client._process_message(message)
        self.assertIsNotNone(device.last_report_at)
        self.assertEqual(observed, [device.last_report_at])

    def test_paired_device_forwarding(self):
        calls = []
        source = SimpleNamespace(get_paired_device_id=lambda: "paired")
        paired = SimpleNamespace()
        client = YoLinkMqttClient(
            None,
            Endpoints.US.value,
            "localhost",
            1883,
            {"source": source, "paired": paired},
        )
        client._message_listener = SimpleNamespace(
            on_message=lambda device, data: calls.append((device, data))
        )
        message = SimpleNamespace(
            topic="yl-home/home/source/report",
            retain=False,
            payload=b'{"event":"Switch.Report","data":{"state":"on"}}',
        )
        client._process_message(message)
        self.assertEqual(calls, [(paired, {"state": "on"}), (source, {"state": "on"})])

        calls.clear()
        del client._devices["paired"]
        client._process_message(message)
        self.assertEqual(calls, [(source, {"state": "on"})])

        calls.clear()
        source.get_paired_device_id = lambda: None
        client._process_message(message)
        self.assertEqual(calls, [(source, {"state": "on"})])

    async def test_disconnect_propagates_caller_cancellation_during_cleanup(self):
        started = asyncio.Event()
        cleanup_started = asyncio.Event()
        finish_cleanup = asyncio.Event()

        async def listen():
            started.set()
            try:
                await asyncio.Event().wait()
            finally:
                cleanup_started.set()
                await finish_cleanup.wait()

        client = YoLinkMqttClient(None, Endpoints.US.value, "localhost", 1883, {})
        with patch.object(client, "_listen", side_effect=listen):
            await client.connect("topic", object())
            listener_task = client._listener_task
            await started.wait()
            disconnect_task = asyncio.create_task(client.disconnect())
            await cleanup_started.wait()
            disconnect_task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await disconnect_task
            self.assertIs(client._listener_task, listener_task)
            self.assertFalse(listener_task.done())
            finish_cleanup.set()
            with self.assertRaises(asyncio.CancelledError):
                await listener_task
            await client.disconnect()
            self.assertIsNone(client._listener_task)

    async def test_connect_is_idempotent_and_disconnect_waits_for_cleanup(self):
        started = asyncio.Event()
        cleaned_up = asyncio.Event()
        starts = 0

        async def listen():
            nonlocal starts
            starts += 1
            started.set()
            try:
                await asyncio.Event().wait()
            finally:
                await asyncio.sleep(0)
                cleaned_up.set()

        client = YoLinkMqttClient(None, Endpoints.US.value, "localhost", 1883, {})
        listener = object()
        with patch.object(client, "_listen", side_effect=listen):
            await client.connect("topic", listener)
            await started.wait()
            task = client._listener_task
            await client.connect("topic", listener)
            self.assertIs(client._listener_task, task)
            self.assertEqual(starts, 1)
            with self.assertLogs("yolink.mqtt_client", level="WARNING"):
                await client.connect("another-topic", listener)
            self.assertIs(client._listener_task, task)
            self.assertEqual(client._topic, "topic")
            await client.disconnect()
            self.assertTrue(cleaned_up.is_set())
            self.assertTrue(task.done())
            self.assertIsNone(client._listener_task)
            await client.connect("another-topic", listener)
            self.assertIsNot(client._listener_task, task)
            await client.disconnect()

    async def test_bad_message_and_listener_error_do_not_interrupt_subscription(self):
        received = asyncio.Event()
        calls = []
        device = SimpleNamespace(
            device_type="Switch", get_paired_device_id=lambda: None
        )
        payload = b'{"event":"Switch.Report","data":{"state":"on"}}'
        messages = [
            SimpleNamespace(
                topic="yl-home/home/device/report", retain=False, payload=data
            )
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

        client = YoLinkMqttClient(
            Auth(), Endpoints.US.value, "localhost", 1883, {"device": device}
        )
        with (
            patch("yolink.mqtt_client.Client", FakeClient),
            self.assertLogs("yolink.mqtt_client", level="WARNING") as logs,
        ):
            await client.connect("yl-home/home/+/report", Listener())
            task = client._listener_task
            try:
                await asyncio.wait_for(received.wait(), timeout=1)
                self.assertEqual(len(calls), 2)
                self.assertEqual(len(logs.records), 2)
                self.assertEqual(logs.records[0].levelname, "WARNING")
                self.assertIsNone(logs.records[0].exc_info)
                self.assertEqual(logs.records[1].levelname, "ERROR")
                self.assertIsNotNone(logs.records[1].exc_info)
            finally:
                await client.disconnect()
                with self.assertRaises(asyncio.CancelledError):
                    await task
