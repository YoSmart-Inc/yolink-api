"""Tests for API codes and library exception boundaries."""

import asyncio
import unittest
from unittest.mock import AsyncMock, Mock

from aiohttp import ClientConnectionError, ClientResponseError, RequestInfo
from yolink.http_client import YoLinkHttpClient
from yolink.exception import (
    YoLinkApiCode,
    YoLinkAuthFailError,
    YoLinkClientError,
    YoLinkConfigError,
    YoLinkConnectionError,
    YoLinkTimeoutError,
)
from yolink.cloud_client import YoLinkCloudClinet
from yolink.local_auth_mgr import YoLinkLocalAuthMgr
from yolink.local_client import YoLinkLocalClinet
from yolink.model import BRDP


class ApiCodeTest(unittest.TestCase):
    def test_success_and_error_mapping_preserve_api_values(self):
        BRDP(code=YoLinkApiCode.SUCCESS).check_response()
        for code, exception in (
            ("000101", YoLinkClientError),
            ("000102", YoLinkClientError),
            ("000103", YoLinkAuthFailError),
            ("000104", YoLinkAuthFailError),
            ("000105", YoLinkClientError),
            ("000106", YoLinkAuthFailError),
            ("000201", YoLinkClientError),
            ("000202", YoLinkClientError),
            ("000203", YoLinkClientError),
            ("010000", YoLinkClientError),
            ("010001", YoLinkClientError),
            ("010101", YoLinkAuthFailError),
            ("010102", YoLinkAuthFailError),
            ("010103", YoLinkAuthFailError),
            ("010104", YoLinkAuthFailError),
            ("010200", YoLinkClientError),
            ("010201", YoLinkClientError),
            ("010202", YoLinkClientError),
            ("010203", YoLinkClientError),
            ("010204", YoLinkClientError),
            ("010300", YoLinkClientError),
            ("010301", YoLinkClientError),
            ("020100", YoLinkClientError),
            ("020101", YoLinkClientError),
            ("020102", YoLinkClientError),
            ("020103", YoLinkClientError),
            ("020104", YoLinkClientError),
            ("020105", YoLinkClientError),
            ("020201", YoLinkClientError),
            ("030101", YoLinkClientError),
            ("999999", YoLinkClientError),
            ("unknown", YoLinkClientError),
            (None, YoLinkClientError),
        ):
            with self.subTest(code=code):
                with self.assertRaises(exception) as caught:
                    BRDP(code=code, desc="API description").check_response()
                self.assertIs(type(caught.exception), exception)
                self.assertEqual(caught.exception.code, code)
                if code not in (None, "unknown"):
                    self.assertEqual(YoLinkApiCode(code).value, code)
                self.assertEqual(caught.exception.message, "API description")
                self.assertIn("API description", str(caught.exception))


class ClientExceptionTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.auth = Mock()
        self.auth.check_and_refresh_token = AsyncMock()
        self.session = Mock()
        self.session.request = AsyncMock()
        self.auth.client_session.return_value = self.session
        self.client = YoLinkHttpClient(self.auth)

    def response(self, code):
        response = Mock()
        response.status = 200
        response.text = AsyncMock(
            return_value=f'{{"code":"{code}","desc":"result","data":{{}}}}'
        )
        return response

    async def test_transport_errors_from_direct_and_api_requests(self):
        for error, expected in (
            (ClientConnectionError("disconnected"), YoLinkConnectionError),
            (asyncio.TimeoutError(), YoLinkTimeoutError),
        ):
            for execute in (False, True):
                with self.subTest(error=type(error).__name__, execute=execute):
                    self.session.request.reset_mock()
                    self.session.request.side_effect = error
                    with self.assertRaises(expected) as caught:
                        if execute:
                            await self.client.execute("https://example.test", {})
                        else:
                            await self.client.get("https://example.test")
                    self.assertIs(caught.exception.__cause__, error)
                    self.assertFalse(hasattr(caught.exception, "code"))
                    self.assertEqual(
                        self.session.request.await_count,
                        2 if execute else 1,
                    )

    async def test_response_status_and_body_timeout_are_wrapped(self):
        status_error = ClientResponseError(
            request_info=Mock(spec=RequestInfo), history=(), status=503
        )
        for error, expected in (
            (status_error, YoLinkConnectionError),
            (asyncio.TimeoutError(), YoLinkTimeoutError),
        ):
            with self.subTest(error=type(error).__name__):
                self.session.request.reset_mock()
                response = self.response("000000")
                if isinstance(error, ClientResponseError):
                    response.raise_for_status.side_effect = error
                else:
                    response.text.side_effect = error
                self.session.request.return_value = response
                with self.assertRaises(expected) as caught:
                    await self.client.execute("https://example.test", {})
                self.assertIs(caught.exception.__cause__, error)
                self.assertEqual(self.session.request.await_count, 2)

    async def test_connection_failure_retry_can_succeed(self):
        self.session.request.side_effect = [
            ClientConnectionError("disconnected"),
            self.response("000000"),
        ]
        response = await self.client.execute("https://example.test", {})
        self.assertEqual(response.code, "000000")
        self.assertEqual(self.session.request.await_count, 2)

    async def test_http_status_failure_retry_can_succeed(self):
        failed_response = self.response("000000")
        failed_response.raise_for_status.side_effect = ClientResponseError(
            request_info=Mock(spec=RequestInfo), history=(), status=503
        )
        self.session.request.side_effect = [
            failed_response,
            self.response("000000"),
        ]
        response = await self.client.execute("https://example.test", {})
        self.assertEqual(response.code, "000000")
        self.assertEqual(self.session.request.await_count, 2)

    async def test_timeout_retry_can_succeed(self):
        self.session.request.side_effect = [
            asyncio.TimeoutError(),
            self.response("000000"),
        ]
        response = await self.client.execute("https://example.test", {})
        self.assertEqual(response.code, "000000")
        self.assertEqual(self.session.request.await_count, 2)

    async def test_body_timeout_retry_can_succeed(self):
        timed_out_response = self.response("000000")
        timed_out_response.text.side_effect = asyncio.TimeoutError()
        self.session.request.side_effect = [
            timed_out_response,
            self.response("000000"),
        ]
        response = await self.client.execute("https://example.test", {})
        self.assertEqual(response.code, "000000")
        self.assertEqual(self.session.request.await_count, 2)

    async def test_device_connection_failure_retries_and_raises_original_type(self):
        for code in ("000201", "000203"):
            with self.subTest(code=code):
                self.session.request.reset_mock()
                self.session.request.return_value = self.response(code)
                with self.assertRaises(YoLinkClientError) as caught:
                    await self.client.execute("https://example.test", {})
                self.assertEqual(caught.exception.code, code)
                self.assertEqual(self.session.request.await_count, 2)

    async def test_device_connection_retry_can_succeed(self):
        self.session.request.side_effect = [
            self.response("000201"),
            self.response("000000"),
        ]
        response = await self.client.execute("https://example.test", {})
        self.assertEqual(response.code, "000000")
        self.assertEqual(self.session.request.await_count, 2)

    async def test_authentication_failure_is_not_retried(self):
        self.session.request.return_value = self.response("000103")
        with self.assertRaises(YoLinkAuthFailError):
            await self.client.execute("https://example.test", {})
        self.assertEqual(self.session.request.await_count, 1)

    async def test_hub_connection_failure_retries_and_raises_original_type(self):
        self.session.request.return_value = self.response("000101")
        with self.assertRaises(YoLinkClientError) as caught:
            await self.client.execute("https://example.test", {})
        self.assertEqual(caught.exception.code, "000101")
        self.assertEqual(caught.exception.message, "result")
        self.assertEqual(self.session.request.await_count, 2)

    async def test_hub_connection_retry_can_succeed(self):
        self.session.request.side_effect = [
            self.response("000101"),
            self.response("000000"),
        ]
        response = await self.client.execute("https://example.test", {})
        self.assertEqual(response.code, "000000")
        self.assertEqual(self.session.request.await_count, 2)

    async def test_hub_command_failure_is_not_retried(self):
        self.session.request.return_value = self.response("000102")
        with self.assertRaises(YoLinkClientError) as caught:
            await self.client.execute("https://example.test", {})
        self.assertEqual(caught.exception.code, "000102")
        self.assertEqual(self.session.request.await_count, 1)

    async def test_other_api_errors_are_not_retried(self):
        for code in YoLinkApiCode:
            if code in (
                YoLinkApiCode.SUCCESS,
                YoLinkApiCode.HUB_CONNECTION_FAILED,
                YoLinkApiCode.DEVICE_CONNECTION_FAILED,
                YoLinkApiCode.DEVICE_UNREACHABLE,
            ):
                continue
            with self.subTest(code=code):
                self.session.request.reset_mock()
                self.session.request.return_value = self.response(code.value)
                with self.assertRaises(YoLinkClientError) as caught:
                    await self.client.execute("https://example.test", {})
                self.assertEqual(caught.exception.code, code)
                self.assertEqual(self.session.request.await_count, 1)

    async def test_local_token_http_errors(self):
        session = Mock()
        session.post = AsyncMock()
        auth = YoLinkLocalAuthMgr(session, "https://example.test", "id", "secret")
        for status, expected in (
            (400, YoLinkAuthFailError),
            (401, YoLinkAuthFailError),
            (403, YoLinkAuthFailError),
            (503, YoLinkConnectionError),
        ):
            with self.subTest(status=status):
                error = ClientResponseError(Mock(), (), status=status)
                session.post.side_effect = error
                with self.assertRaises(expected) as caught:
                    await auth.check_and_refresh_token()
                self.assertIs(caught.exception.__cause__, error)

    async def test_local_token_transport_errors(self):
        session = Mock()
        session.post = AsyncMock()
        auth = YoLinkLocalAuthMgr(session, "https://example.test", "id", "secret")
        for error, expected in (
            (ClientConnectionError("disconnected"), YoLinkConnectionError),
            (asyncio.TimeoutError(), YoLinkTimeoutError),
        ):
            with self.subTest(error=type(error).__name__):
                session.post.side_effect = error
                with self.assertRaises(expected) as caught:
                    await auth.check_and_refresh_token()
                self.assertIs(caught.exception.__cause__, error)

    async def test_configuration_errors_have_no_api_code(self):
        home = YoLinkCloudClinet(Mock())
        hub = YoLinkLocalClinet(None, "localhost", "net", "id", "secret")
        with self.assertRaises(YoLinkConfigError):
            YoLinkCloudClinet(None)
        for call in (
            lambda: home.async_setup(None),
            lambda: hub.async_setup(None),
            hub.async_load_devices,
        ):
            with self.assertRaises(YoLinkConfigError) as caught:
                await call()
            self.assertFalse(hasattr(caught.exception, "code"))
