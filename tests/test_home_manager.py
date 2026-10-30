"""Tests for home device loading."""

import asyncio
import unittest
from unittest.mock import AsyncMock

from yolink.endpoint import Endpoints
from yolink.exception import YoLinkClientError
from yolink.home_manager import YoLinkHome
from yolink.local_hub_client import YoLinkLocalHubClient
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
    async def test_reload_removes_absent_devices_and_keeps_shared_dict(self):
        home = YoLinkHome()
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
        home = YoLinkHome()
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
        home = YoLinkHome()
        home._http_client = AsyncMock()
        home._http_client.execute.return_value = response([device("us", "us_1")])

        devices = await home.async_load_home_devices()

        self.assertEqual(devices["us"].device_token, "original-us")
        self.assertEqual(home._http_client.execute.await_count, 1)
        self.assertEqual(
            home._http_client.execute.await_args.kwargs["url"], Endpoints.US.value.url
        )

    async def test_eu_tokens_are_used_when_available(self):
        home = YoLinkHome()
        home._http_client = AsyncMock()
        home._http_client.execute.side_effect = [
            response([device("us", "us_1"), device("eu", "eu_1")]),
            response([{"deviceId": "eu", "token": "eu-token"}]),
        ]

        devices = await home.async_load_home_devices()

        self.assertEqual(devices["us"].device_token, "original-us")
        self.assertEqual(devices["eu"].device_token, "eu-token")

    async def test_invalid_eu_entries_do_not_block_valid_tokens(self):
        home = YoLinkHome()
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

        with self.assertLogs("yolink.home_manager", level="WARNING"):
            devices = await home.async_load_home_devices()

        self.assertEqual(devices["us"].device_token, "original-us")
        self.assertEqual(devices["eu"].device_token, "eu-token")

    async def test_eu_failure_still_loads_external_data_with_original_token(self):
        for error in (
            YoLinkClientError("error", "unavailable"),
            asyncio.TimeoutError(),
            TimeoutError(),
        ):
            with self.subTest(error=type(error).__name__):
                home = YoLinkHome()
                home._http_client = AsyncMock()
                home._http_client.execute.side_effect = [
                    response(
                        [device("us", "us_1"), device("eu", "eu_1", "WaterDepthSensor")]
                    ),
                    error,
                    BRDP(code="000000", data={"extData": {"range": 5}}),
                ]

                with self.assertLogs("yolink.home_manager", level="WARNING"):
                    devices = await home.async_load_home_devices()

                self.assertEqual(set(devices), {"us", "eu"})
                self.assertEqual(devices["eu"].device_token, "original-eu")
                self.assertEqual(devices["eu"].device_attrs, {"range": 5})
                self.assertEqual(home._http_client.execute.await_count, 3)
                self.assertEqual(
                    home._http_client.execute.await_args.kwargs["bsdp"]["token"],
                    "original-eu",
                )

    async def test_eu_external_data_failure_does_not_block_other_devices(self):
        for error in (
            YoLinkClientError("error", "external data unavailable"),
            asyncio.TimeoutError(),
            TimeoutError(),
        ):
            with self.subTest(error=type(error).__name__):
                home = YoLinkHome()
                home._http_client = AsyncMock()
                home._http_client.execute.side_effect = [
                    response(
                        [device("eu", "eu_1", "WaterDepthSensor"), device("us", "us_1")]
                    ),
                    YoLinkClientError("error", "unavailable"),
                    error,
                ]

                with self.assertLogs("yolink.home_manager", level="WARNING"):
                    devices = await home.async_load_home_devices()

                self.assertEqual(set(devices), {"us", "eu"})
                self.assertIsNone(devices["eu"].device_attrs)

    async def test_missing_eu_token_preserves_original(self):
        home = YoLinkHome()
        home._http_client = AsyncMock()
        home._http_client.execute.side_effect = [
            response([device("eu", "eu_1")]),
            response([]),
        ]

        with self.assertLogs("yolink.home_manager", level="WARNING"):
            devices = await home.async_load_home_devices()

        self.assertEqual(devices["eu"].device_token, "original-eu")


class LocalDeviceLoadingTest(unittest.IsolatedAsyncioTestCase):
    async def test_reload_removes_absent_devices_and_keeps_shared_dict(self):
        hub = YoLinkLocalHubClient(None, "localhost", "net", "client", "secret")
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

    async def test_failed_reload_preserves_previous_devices(self):
        hub = YoLinkLocalHubClient(None, "localhost", "net", "client", "secret")
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
