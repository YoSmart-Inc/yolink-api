"""Tests for home device loading."""

import unittest
from unittest.mock import AsyncMock, Mock, patch

from yolink.endpoint import Endpoints
from yolink.exception import (
    YoLinkClientError,
    YoLinkConnectionError,
    YoLinkTimeoutError,
)
from yolink.cloud_client import YoLinkCloudClinet
from yolink.local_client import YoLinkLocalClinet
from yolink.model import BRDP


def device(device_id, zone, device_type="Switch"):
    return {
        "deviceId": device_id,
        "name": device_id,
        "token": f"original-{device_id}",
        "type": device_type,
        "serviceZone": zone,
    }


def response(devices):
    return BRDP(code="000000", data={"devices": devices})


class HomeDeviceLoadingTest(unittest.IsolatedAsyncioTestCase):
    async def test_skips_unsupported_device_type(self):
        home = YoLinkCloudClinet(Mock())
        home._http_client = AsyncMock()
        home._http_client.execute.return_value = response(
            [device("unknown", "us_1", "Unknown"), device("switch", "us_1")]
        )

        with self.assertLogs("yolink.devices.factory", level="WARNING"):
            devices = await home.async_load_home_devices()

        self.assertEqual(set(devices), {"switch"})

    async def test_unsupported_external_data_is_skipped_in_all_regions(self):
        for zone in ("us_1", "eu_1"):
            with self.subTest(zone=zone):
                home = YoLinkCloudClinet(Mock())
                home._http_client = AsyncMock()
                replies = [response([device("sensor", zone, "WaterDepthSensor")])]
                if zone == "eu_1":
                    replies.append(response([{"deviceId": "sensor", "token": "eu"}]))
                replies.append(YoLinkClientError("010203", "unsupported"))
                home._http_client.execute.side_effect = replies

                devices = await home.async_load_home_devices()

                self.assertEqual(set(devices), {"sensor"})
                self.assertIsNone(devices["sensor"].attrs)

    async def test_reload_removes_absent_devices_and_keeps_shared_dict(self):
        home = YoLinkCloudClinet(Mock())
        home._http_client = AsyncMock()
        home._http_client.execute.side_effect = [
            response([device("old", "us_1"), device("keep", "us_1")]),
            response([device("keep", "us_1"), device("new", "us_1")]),
            response([]),
        ]

        shared_devices = await home.async_load_home_devices()
        self.assertIs(await home.async_load_home_devices(), shared_devices)
        self.assertEqual(set(shared_devices), {"keep", "new"})
        self.assertIsNone(home.get_device("old"))
        await home.async_load_home_devices()
        self.assertEqual(shared_devices, {})

    async def test_failed_reload_preserves_previous_devices(self):
        home = YoLinkCloudClinet(Mock())
        home._http_client = AsyncMock()
        home._http_client.execute.side_effect = [
            response([device("old", "us_1")]),
            response(
                [device("new", "us_1"), device("sensor", "us_1", "WaterDepthSensor")]
            ),
            YoLinkClientError("error", "unavailable"),
        ]
        shared_devices = await home.async_load_home_devices()
        with self.assertRaises(YoLinkClientError):
            await home.async_load_home_devices()
        self.assertEqual(set(shared_devices), {"old"})

    async def test_us_only_does_not_call_eu(self):
        home = YoLinkCloudClinet(Mock())
        home._http_client = AsyncMock()
        home._http_client.execute.return_value = response([device("us", "us_1")])

        devices = await home.async_load_home_devices()

        self.assertEqual(devices["us"].token, "original-us")
        self.assertEqual(home._http_client.execute.await_count, 1)
        self.assertEqual(
            home._http_client.execute.await_args.kwargs["url"], Endpoints.US.value.url
        )

    async def test_eu_tokens_are_used_when_available(self):
        home = YoLinkCloudClinet(Mock())
        home._http_client = AsyncMock()
        home._http_client.execute.side_effect = [
            response([device("us", "us_1"), device("eu", "eu_1")]),
            response([{"deviceId": "eu", "token": "eu-token"}]),
        ]

        devices = await home.async_load_home_devices()

        self.assertEqual(devices["us"].token, "original-us")
        self.assertEqual(devices["eu"].token, "eu-token")

    async def test_invalid_eu_entries_do_not_block_valid_tokens(self):
        home = YoLinkCloudClinet(Mock())
        home._http_client = AsyncMock()
        home._http_client.execute.side_effect = [
            response([device("us", "us_1"), device("eu", "eu_1")]),
            response(
                [
                    None,
                    "invalid",
                    {"deviceId": [], "token": "bad"},
                    {"deviceId": "eu", "token": []},
                    {"deviceId": "eu", "token": "eu-token"},
                ]
            ),
        ]

        with self.assertLogs("yolink.cloud_client", level="WARNING"):
            devices = await home.async_load_home_devices()

        self.assertEqual(devices["us"].token, "original-us")
        self.assertEqual(devices["eu"].token, "eu-token")

    async def test_eu_failure_still_loads_external_data_with_original_token(self):
        for error in (
            YoLinkClientError("error", "unavailable"),
            YoLinkConnectionError("disconnected"),
            YoLinkTimeoutError("timed out"),
        ):
            with self.subTest(error=type(error).__name__):
                home = YoLinkCloudClinet(Mock())
                home._http_client = AsyncMock()
                home._http_client.execute.side_effect = [
                    response(
                        [device("us", "us_1"), device("eu", "eu_1", "WaterDepthSensor")]
                    ),
                    error,
                    BRDP(code="000000", data={"extData": {"range": 5}}),
                ]

                with self.assertLogs("yolink.cloud_client", level="WARNING"):
                    devices = await home.async_load_home_devices()

                self.assertEqual(set(devices), {"us", "eu"})
                self.assertEqual(devices["eu"].token, "original-eu")
                self.assertEqual(devices["eu"].attrs, {"range": 5})
                self.assertEqual(home._http_client.execute.await_count, 3)
                self.assertEqual(
                    home._http_client.execute.await_args.kwargs["bsdp"]["token"],
                    "original-eu",
                )

    async def test_eu_external_data_failure_does_not_block_other_devices(self):
        for error in (
            YoLinkClientError("error", "external data unavailable"),
            YoLinkConnectionError("disconnected"),
            YoLinkTimeoutError("timed out"),
        ):
            with self.subTest(error=type(error).__name__):
                home = YoLinkCloudClinet(Mock())
                home._http_client = AsyncMock()
                home._http_client.execute.side_effect = [
                    response(
                        [device("eu", "eu_1", "WaterDepthSensor"), device("us", "us_1")]
                    ),
                    YoLinkClientError("error", "unavailable"),
                    error,
                ]

                with self.assertLogs("yolink.cloud_client", level="WARNING"):
                    devices = await home.async_load_home_devices()

                self.assertEqual(set(devices), {"us", "eu"})
                self.assertIsNone(devices["eu"].attrs)

    async def test_missing_eu_token_preserves_original(self):
        home = YoLinkCloudClinet(Mock())
        home._http_client = AsyncMock()
        home._http_client.execute.side_effect = [
            response([device("eu", "eu_1")]),
            response([]),
        ]

        with self.assertLogs("yolink.cloud_client", level="WARNING"):
            devices = await home.async_load_home_devices()

        self.assertEqual(devices["eu"].token, "original-eu")


class LocalDeviceLoadingTest(unittest.IsolatedAsyncioTestCase):
    async def test_custom_http_url_and_mqtt_endpoint(self):
        hub = YoLinkLocalClinet(
            None, "https://hub.example.com:8443", "net", "client", "secret",
            mqtt_port=1883,
        )
        self.assertEqual(hub._endpoint.url, "https://hub.example.com:8443/open/yolink/v2/api")
        self.assertEqual(hub._auth_mgr._token_url, "https://hub.example.com:8443/open/yolink/token")
        self.assertEqual(hub._endpoint.mqtt_broker_host, "hub.example.com")
        self.assertEqual(hub._endpoint.mqtt_broker_port, 1883)

    async def test_default_endpoint_ports(self):
        hub = YoLinkLocalClinet(None, "localhost", "net", "client", "secret")
        self.assertEqual(hub._endpoint.url, "http://localhost:1080/open/yolink/v2/api")
        self.assertEqual(hub._endpoint.mqtt_broker_host, "localhost")
        self.assertEqual(hub._endpoint.mqtt_broker_port, 18080)

    async def test_skips_unsupported_device_type(self):
        hub = YoLinkLocalClinet(None, "localhost", "net", "client", "secret")
        hub._http_client = AsyncMock()
        hub._http_client.execute.return_value = response(
            [device("unknown", "us_1", "Unknown"), device("switch", "us_1")]
        )

        with self.assertLogs("yolink.devices.factory", level="WARNING"):
            devices = await hub.async_load_devices()

        self.assertEqual(set(devices), {"switch"})

    async def test_external_data_skips_only_unsupported_method(self):
        for code in ("010203", "000103", "000201"):
            with self.subTest(code=code):
                hub = YoLinkLocalClinet(None, "localhost", "net", "client", "secret")
                hub._http_client = AsyncMock()
                error = YoLinkClientError(code, "failed")
                hub._http_client.execute.side_effect = [
                    response([device("sensor", "us_1", "WaterDepthSensor")]),
                    error,
                ]
                if code == "010203":
                    devices = await hub.async_load_devices()
                    self.assertEqual(set(devices), {"sensor"})
                    self.assertIsNone(devices["sensor"].attrs)
                else:
                    with self.assertRaises(YoLinkClientError) as caught:
                        await hub.async_load_devices()
                    self.assertIs(caught.exception, error)

    async def test_reload_removes_absent_devices_and_keeps_shared_dict(self):
        hub = YoLinkLocalClinet(None, "localhost", "net", "client", "secret")
        hub._http_client = AsyncMock()
        hub._http_client.execute.side_effect = [
            response([device("old", "us_1"), device("keep", "us_1")]),
            response([device("keep", "us_1"), device("new", "us_1")]),
            response([]),
        ]

        shared_devices = await hub.async_load_devices()
        self.assertIs(await hub.async_load_devices(), shared_devices)
        self.assertEqual(set(shared_devices), {"keep", "new"})
        self.assertIsNone(hub.get_device("old"))
        await hub.async_load_devices()
        self.assertEqual(shared_devices, {})

    async def test_reload_replaces_device_and_updates_metadata(self):
        hub = YoLinkLocalClinet(None, "localhost", "net", "client", "secret")
        hub._http_client = AsyncMock()
        updated = device("keep", "us_1")
        updated.update(name="renamed", token="new-token")
        hub._http_client.execute.side_effect = [
            response([device("keep", "us_1")]), response([updated])
        ]
        original = (await hub.async_load_devices())["keep"]
        original.current_net_type = "known"
        await hub.async_load_devices()
        reloaded = hub.get_device("keep")
        self.assertIsNot(reloaded, original)
        self.assertEqual((reloaded.name, reloaded.token), ("renamed", "new-token"))
        self.assertIsNone(reloaded.current_net_type)

    async def test_repeated_setup_disconnects_previous_client(self):
        hub = YoLinkLocalClinet(None, "localhost", "net", "client", "secret")
        first, second = AsyncMock(), AsyncMock()
        with patch("yolink.local_client.YoLinkMqttClient", side_effect=[first, second]), \
             patch.object(hub, "async_load_devices", new_callable=AsyncMock):
            await hub.async_setup(Mock())
            await hub.async_setup(Mock())
            first.disconnect.assert_awaited_once()
            await hub.async_unload()
            second.disconnect.assert_awaited_once()

    async def test_failed_reload_preserves_previous_devices(self):
        hub = YoLinkLocalClinet(None, "localhost", "net", "client", "secret")
        hub._http_client = AsyncMock()
        hub._http_client.execute.side_effect = [
            response([device("old", "us_1")]),
            response(
                [device("new", "us_1"), device("sensor", "us_1", "WaterDepthSensor")]
            ),
            YoLinkClientError("error", "unavailable"),
        ]

        shared_devices = await hub.async_load_devices()
        with self.assertRaises(YoLinkClientError):
            await hub.async_load_devices()
        self.assertEqual(set(shared_devices), {"old"})
