"""Verify useful log context without payloads or credentials."""

import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from aiohttp import ClientResponseError

from yolink.http_client import YoLinkHttpClient
from yolink.endpoint import Endpoints
from yolink.exception import YoLinkClientError, YoLinkTimeoutError
from yolink.cloud_client import YoLinkCloudClinet
from yolink.local_auth_mgr import YoLinkLocalAuthMgr
from yolink.local_client import YoLinkLocalClinet
from yolink.mqtt_client import YoLinkMqttClient


class LoggingTest(unittest.IsolatedAsyncioTestCase):
    async def test_unload_logs_start_before_disconnect_and_completion_only_on_success(
        self,
    ):
        for local in (False, True):
            for failed in (False, True):
                with self.subTest(local=local, failed=failed):
                    manager = (
                        YoLinkLocalClinet(None, "localhost", "net", "id", "secret")
                        if local
                        else YoLinkCloudClinet(Mock())
                    )
                    mqtt = AsyncMock()
                    if local:
                        manager._mqtt_client = mqtt
                    else:
                        manager._mqtt_clients = {"US": mqtt}

                    async def disconnect(failed=failed):
                        self.assertIn("Unloading", logs.records[0].getMessage())
                        if failed:
                            raise RuntimeError("cleanup failed")

                    mqtt.disconnect.side_effect = disconnect
                    with self.assertLogs("yolink", level="INFO") as logs:
                        if failed:
                            with self.assertRaises(RuntimeError):
                                await manager.async_unload()
                        else:
                            await manager.async_unload()
                    self.assertEqual(len(logs.records), 1 if failed else 2)
                    if not failed:
                        self.assertIn("unloaded", logs.records[-1].getMessage())

    async def test_mqtt_stop_does_not_log_success_when_cleanup_fails(self):
        for failed in (False, True):
            with self.subTest(failed=failed):
                started = asyncio.Event()

                async def listen(started=started, failed=failed):
                    started.set()
                    try:
                        await asyncio.Event().wait()
                    finally:
                        if failed:
                            raise RuntimeError("cleanup failed")

                client = YoLinkMqttClient(
                    None, Endpoints.US.value, "localhost", 1883, {}
                )
                client._listener_task = asyncio.create_task(listen())
                await started.wait()
                with self.assertLogs("yolink.mqtt_client", level="INFO") as logs:
                    if failed:
                        with self.assertRaises(RuntimeError):
                            await client.disconnect()
                    else:
                        await client.disconnect()
                self.assertIn("Stopping MQTT listener", logs.output[0])
                self.assertEqual(len(logs.records), 1 if failed else 2)
                self.assertIsNone(client._listener_task)
                if not failed:
                    self.assertIn("MQTT listener stopped", logs.output[-1])

    async def test_timeout_log_includes_error_on_last_attempt(self):
        client = YoLinkHttpClient(Mock())
        client.post = AsyncMock(side_effect=TimeoutError())
        with (
            self.assertLogs("yolink.http_client", level="DEBUG") as logs,
            self.assertRaises(YoLinkTimeoutError),
        ):
            await client.execute("https://example.test", {"method": "Hub.getState"})
        self.assertIn("API request started", logs.output[0])
        self.assertIn("API request finished", logs.output[-1])
        self.assertIn("error=YoLinkTimeoutError", logs.output[-1])

    async def test_api_retry_logs_context_without_sensitive_data(self):
        client = YoLinkHttpClient(Mock())
        client.post = AsyncMock()
        failed = Mock(status=200)
        failed.text = AsyncMock(
            return_value='{"code":"000101","desc":"response-secret"}'
        )
        success = Mock(status=200)
        success.text = AsyncMock(return_value='{"code":"000000","data":{}}')
        client.post.side_effect = [failed, success]
        with self.assertLogs("yolink.http_client", level="DEBUG") as logs:
            await client.execute(
                url="https://example.test?token=url-secret",
                bsdp={
                    "method": "Hub.getState",
                    "targetDevice": "hub-id",
                    "token": "device-secret",
                    "params": {"password": "params-secret"},
                },
                headers={"Authorization": "Bearer auth-secret"},
            )
        output = "\n".join(logs.output)
        for secret in (
            "url-secret",
            "device-secret",
            "params-secret",
            "auth-secret",
            "response-secret",
        ):
            self.assertNotIn(secret, output)
        self.assertIn("method=Hub.getState device=hub-id", output)
        self.assertIn("status=200 code=000101 elapsed=", output)
        self.assertIn("attempt=2/2 error=YoLinkClientError code=000101", output)
        self.assertIn("status=200 code=000000 elapsed=", output)
        self.assertEqual(sum(r.levelname == "WARNING" for r in logs.records), 1)
        self.assertTrue(all(r.exc_info is None for r in logs.records))

    async def test_final_api_error_is_propagated_without_duplicate_warning(self):
        client = YoLinkHttpClient(Mock())
        response = Mock(status=200)
        response.text = AsyncMock(return_value='{"code":"000101","desc":"failed"}')
        client.post = AsyncMock(return_value=response)
        with (
            self.assertLogs("yolink.http_client", level="WARNING") as logs,
            self.assertRaises(YoLinkClientError),
        ):
            await client.execute("https://example.test", {"method": "Hub.getState"})
        self.assertEqual(len(logs.records), 1)
        self.assertEqual(client.post.await_count, 2)

    async def test_mqtt_logs_metadata_and_validation_error_without_payload(self):
        client = YoLinkMqttClient(Mock(), Endpoints.US.value, "localhost", 1883, {})
        with self.assertLogs("yolink.mqtt_client", level="DEBUG") as logs:
            for payload in (
                b'{"event":"Switch.Report","data":{"token":"payload-secret"}}',
                b'{"event":"Switch.Report","data":"invalid-secret"}',
                b"\xff",
            ):
                client._process_message(
                    SimpleNamespace(
                        topic="yl-home/home/device/report",
                        payload=payload,
                        retain=False,
                    )
                )
        output = "\n".join(logs.output)
        self.assertIn("device=device event=Switch.Report retained=False", output)
        self.assertIn("error=ValidationError", output)
        self.assertIn("error=UnicodeDecodeError", output)
        self.assertNotIn("payload-secret", output)
        self.assertNotIn("invalid-secret", output)
        self.assertTrue(all(r.exc_info is None for r in logs.records))

    async def test_token_sync_failure_has_one_warning_for_all_devices(self):
        home = YoLinkCloudClinet(Mock())
        home._http_client = AsyncMock()
        home._http_client.execute.side_effect = YoLinkClientError("000103", "secret")
        devices = [
            SimpleNamespace(endpoint=Endpoints.EU.value, token="old") for _ in range(3)
        ]
        with self.assertLogs("yolink.cloud_client", level="WARNING") as logs:
            await home._async_sync_eu_tokens(devices)
        self.assertEqual(len(logs.records), 1)
        self.assertIn("3 devices", logs.output[0])
        self.assertIn("code=000103", logs.output[0])
        self.assertNotIn("secret", logs.output[0])
        self.assertTrue(all(d.token == "old" for d in devices))

    async def test_token_request_logs_status_without_response_body(self):
        session = Mock()
        response = Mock(status=401)
        response.raise_for_status.side_effect = ClientResponseError(
            request_info=Mock(), history=(), status=401
        )
        session.post = AsyncMock(return_value=response)
        auth = YoLinkLocalAuthMgr(session, "https://example.test", "id", "secret")
        with (
            self.assertLogs("yolink.local_auth_mgr", level="DEBUG") as logs,
            self.assertRaises(ClientResponseError),
        ):
            await auth._token_request()
        self.assertIn("status=401", logs.output[0])
        self.assertNotIn("secret", logs.output[0])
        response.json.assert_not_called()
