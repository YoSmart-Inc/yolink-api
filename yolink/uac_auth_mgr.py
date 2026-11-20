"""User Access Credentials (UAC) Authentication Manager."""

from __future__ import annotations

import asyncio
import logging
import sys
import time

from http import HTTPStatus
from typing import Any

from aiohttp import ClientError, ClientSession, ClientTimeout
from .auth_mgr import YoLinkAuthMgr
from .const import OAUTH2_TOKEN
from .exception import YoLinkAuthFailError, YoLinkClientError

_LOGGER = logging.getLogger(__name__)

TOKEN_RETRY_DELAY_SEC = 60
# Short, to leave room for the caller's own request within a typical update interval.
TOKEN_REQUEST_TIMEOUT_SEC = 5


def _parse_token_response(payload: Any) -> dict[str, Any]:
    """Return the token of a successful token response, or raise."""
    if not isinstance(payload, dict):
        raise YoLinkClientError("invalid_response", "Token response is not an object")

    # Refused credentials are reported with HTTP 200 and an error state.
    if payload.get("state") == "error":
        msg = payload.get("msg")
        raise YoLinkAuthFailError(
            "error", msg if isinstance(msg, str) and msg else "unknown error"
        )

    access_token = payload.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        raise YoLinkClientError(
            "invalid_response", "Token response has no usable access token"
        )

    expires_in = payload.get("expires_in")
    # Also rejects NaN, infinity and integers too large for a float.
    if (
        isinstance(expires_in, bool)
        or not isinstance(expires_in, (int, float))
        or not 0 < expires_in <= sys.float_info.max
    ):
        raise YoLinkClientError(
            "invalid_response",
            f"Token response has an invalid lifetime: {expires_in!r}",
        )

    return payload


# Not a YoLinkLocalAuthMgr: the MQTT client would then use local hub credentials.
class YoLinkUACAuthMgr(YoLinkAuthMgr):
    """YoLink User Access Credentials (UAID and secret key) Authentication Manager."""

    def __init__(
        self,
        session: ClientSession,
        uaid: str,
        secret_key: str,
    ) -> None:
        """Init YoLink UAC Auth Manager."""
        super().__init__(session)
        self._client_id: str = uaid
        self._client_secret: str = secret_key
        self._token: dict[str, Any] | None = None
        self._token_lock = asyncio.Lock()

    def access_token(self) -> str | None:
        """Get auth token."""
        return self._token["access_token"] if self._token is not None else None

    async def check_and_refresh_token(self) -> str:
        """Check and refresh token."""
        async with self._token_lock:
            cached = self._token
            if cached is not None and time.time() < cached["refresh_at"]:
                return cached["access_token"]
            # From before the request, so response delay does not extend the lifetime.
            requested_at = time.time()
            try:
                token = await self._token_request()
            except YoLinkAuthFailError:
                # The credentials were refused, retrying cannot fix that.
                raise
            except YoLinkClientError as err:
                # A cached token outlives a transient failure of the token endpoint.
                if cached is None or time.time() >= cached["expires_at"]:
                    raise
                cached["refresh_at"] = min(
                    time.time() + TOKEN_RETRY_DELAY_SEC, cached["expires_at"]
                )
                _LOGGER.debug(
                    "Token refresh failed, keeping the cached token: %s", err.message
                )
                return cached["access_token"]
            # Refresh at half the lifetime to leave room to retry a failing endpoint.
            token["refresh_at"] = requested_at + token["expires_in"] / 2
            token["expires_at"] = requested_at + token["expires_in"]
            self._token = token
            return token["access_token"]

    async def _token_request(self) -> dict[str, Any]:
        """Make a token request."""
        try:
            async with self._session.post(
                url=OAUTH2_TOKEN,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data={
                    "grant_type": "client_credentials",
                    "scope": "create",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                },
                timeout=ClientTimeout(total=TOKEN_REQUEST_TIMEOUT_SEC),
                # Status codes are mapped below, even if the session raises on them.
                raise_for_status=False,
            ) as resp:
                if resp.status >= HTTPStatus.BAD_REQUEST:
                    try:
                        error_response = await resp.json()
                    except (ClientError, OSError, asyncio.TimeoutError, ValueError):
                        error_response = None
                    if not isinstance(error_response, dict):
                        error_response = {}
                    error_code = error_response.get("error")
                    if not isinstance(error_code, str) or not error_code:
                        error_code = "unknown"
                    error_desc = error_response.get("error_description")
                    if not isinstance(error_desc, str) or not error_desc:
                        error_desc = f"HTTP {resp.status}"
                    _LOGGER.debug(
                        "Token request failed (%s): %s", error_code, error_desc
                    )
                    if resp.status in (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN):
                        raise YoLinkAuthFailError(error_code, error_desc)
                    raise YoLinkClientError(error_code, error_desc)
                try:
                    payload = await resp.json()
                except (ClientError, ValueError) as err:
                    raise YoLinkClientError(
                        "invalid_response", "Token response is not valid JSON"
                    ) from err
        except (ClientError, OSError, asyncio.TimeoutError) as err:
            reason = str(err) or type(err).__name__
            _LOGGER.debug("Token request failed: %s", reason)
            raise YoLinkClientError("request_failed", reason) from err

        return _parse_token_response(payload)
