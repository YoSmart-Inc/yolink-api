"""HTTP client for YoLink API requests."""

import logging
from asyncio import TimeoutError as AsyncTimeoutError
from time import monotonic
from typing import Any

from aiohttp import ClientError, ClientResponse
from tenacity import RetryCallState, retry, retry_if_exception, stop_after_attempt

from .auth_mgr import YoLinkAuthMgr
from .exception import (
    YoLinkApiCode,
    YoLinkClientError,
    YoLinkConnectionError,
    YoLinkTimeoutError,
)
from .model import BRDP

_LOGGER = logging.getLogger(__name__)


def _log_retry(state: RetryCallState) -> None:
    """Log retry context without request bodies or authentication details."""
    bsdp = state.kwargs.get("bsdp")
    if bsdp is None:
        bsdp = state.args[2]
    error = state.outcome.exception()
    cause = error.__cause__
    _LOGGER.warning(
        "Retrying API request: method=%s device=%s attempt=%s/2 "
        "error=%s code=%s cause=%s status=%s",
        bsdp.get("method"),
        bsdp.get("targetDevice"),
        state.attempt_number + 1,
        type(error).__name__,
        error.code if isinstance(error, YoLinkClientError) else None,
        type(cause).__name__ if cause is not None else None,
        getattr(cause, "status", None),
    )


def _is_retryable_error(error: BaseException) -> bool:
    """Retry HTTP failures and API hub/device connection failures."""
    return isinstance(error, YoLinkConnectionError) or (
        isinstance(error, YoLinkClientError)
        and error.code
        in (
            YoLinkApiCode.HUB_CONNECTION_FAILED,
            YoLinkApiCode.DEVICE_CONNECTION_FAILED,
            YoLinkApiCode.DEVICE_UNREACHABLE,
        )
    )


class YoLinkHttpClient:
    """HTTP client for YoLink API requests."""

    def __init__(self, auth_mgr: YoLinkAuthMgr) -> None:
        """Initialize the HTTP client with an authentication manager."""
        self._auth_mgr = auth_mgr

    async def request(
        self,
        method: str,
        url: str,
        auth_required: bool = True,
        **kwargs: Any,
    ) -> ClientResponse:
        """Send an HTTP request, adding authorization when required."""
        try:
            headers = kwargs.pop("headers", {})
            params = kwargs.pop("params", None)
            data = kwargs.pop("data", None)
            timeout = kwargs.pop("timeout", 8)

            # Extra, user supplied values
            extra_headers = kwargs.pop("extra_headers", None)
            extra_params = kwargs.pop("extra_params", None)
            extra_data = kwargs.pop("extra_data", None)
            if auth_required:
                # Ensure token valid
                await self._auth_mgr.check_and_refresh_token()
                # Set auth header
                headers["Authorization"] = self._auth_mgr.http_auth_header()
            # Extend with optionally supplied values
            if extra_headers:
                headers.update(extra_headers)
            if extra_params:
                # Query parameters
                params = params or {}
                params.update(extra_params)
            if extra_data:
                # form encoded post data
                data = data or {}
                data.update(extra_data)
            return await self._auth_mgr.client_session().request(
                method,
                url,
                **kwargs,
                headers=headers,
                params=params,
                data=data,
                timeout=timeout,
            )
        except (TimeoutError, AsyncTimeoutError) as err:
            raise YoLinkTimeoutError("YoLink HTTP request timed out") from err
        except ClientError as err:
            raise YoLinkConnectionError("YoLink HTTP request failed") from err

    async def get(self, url: str, **kwargs: Any) -> ClientResponse:
        """Send an authenticated GET request."""
        return await self.request("GET", url, True, **kwargs)

    async def post(self, url: str, **kwargs: Any) -> ClientResponse:
        """Send an authenticated POST request."""
        return await self.request("POST", url, True, **kwargs)

    @retry(
        retry=retry_if_exception(_is_retryable_error),
        stop=stop_after_attempt(2),
        reraise=True,
        before_sleep=_log_retry,
    )
    async def execute(self, url: str, bsdp: dict, **kwargs: Any) -> BRDP:
        """Send a YoLink API request and validate its response."""
        started_at = monotonic()
        status = None
        code = None
        error = None
        _LOGGER.debug(
            "API request started: method=%s device=%s",
            bsdp.get("method"),
            bsdp.get("targetDevice"),
        )
        try:
            yl_resp = await self.post(url, json=bsdp, **kwargs)
            status = yl_resp.status
            yl_resp.raise_for_status()
            _yl_body = await yl_resp.text()
            brdp = BRDP.model_validate_json(_yl_body)
            code = brdp.code
            brdp.check_response()
        except (TimeoutError, AsyncTimeoutError) as err:
            error = "YoLinkTimeoutError"
            raise YoLinkTimeoutError("YoLink API request timed out") from err
        except ClientError as err:
            error = "YoLinkConnectionError"
            raise YoLinkConnectionError("YoLink API request failed") from err
        except Exception as err:
            error = type(err).__name__
            raise
        finally:
            _LOGGER.debug(
                "API request finished: method=%s device=%s status=%s code=%s "
                "elapsed=%.3fs error=%s",
                bsdp.get("method"),
                bsdp.get("targetDevice"),
                status,
                code,
                monotonic() - started_at,
                error,
            )
        return brdp
