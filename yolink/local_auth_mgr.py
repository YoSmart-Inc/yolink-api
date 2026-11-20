"""Local Hub Authentication Manager."""

import logging
import time
from asyncio import Lock
from http import HTTPStatus
from typing import cast

from aiohttp import ClientError, ClientResponseError, ClientSession, ClientTimeout

from .auth_mgr import YoLinkAuthMgr
from .exception import (
    YoLinkApiCode,
    YoLinkAuthFailError,
    YoLinkConnectionError,
    YoLinkTimeoutError,
)

_LOGGER = logging.getLogger(__name__)

CLOCK_OUT_OF_SYNC_MAX_SEC = 20


class YoLinkLocalAuthMgr(YoLinkAuthMgr):
    """YoLink Local API Authentication Manager."""

    def __init__(
        self,
        session: ClientSession,
        token_url: str,
        client_id: str,
        client_secret: str,
    ) -> None:
        """Init YoLink Local Auth Manager."""
        super().__init__(session)
        self._token_url = token_url
        self._client_id: str = client_id
        self._client_secret: str = client_secret
        self._token: dict | None = None
        self._token_lock = Lock()

    def access_token(self) -> str | None:
        """Get auth token."""
        return self._token["access_token"] if self._token is not None else None

    @property
    def valid_token(self) -> bool:
        if self._token is None:
            return False
        return (
            cast(float, self._token["expires_at"])
            > time.time() + CLOCK_OUT_OF_SYNC_MAX_SEC
        )

    async def check_and_refresh_token(self) -> str | None:
        """Check and fresh token."""
        async with self._token_lock:
            if self.valid_token:
                return self.access_token()
            try:
                new_token = await self._token_request()
                new_token["expires_at"] = time.time() + new_token["expires_in"]
                self._token = new_token
                return self.access_token()
            except TimeoutError as err:
                raise YoLinkTimeoutError("Token request timed out") from err
            except ClientResponseError as err:
                if err.status in (
                    HTTPStatus.BAD_REQUEST,
                    HTTPStatus.UNAUTHORIZED,
                    HTTPStatus.FORBIDDEN,
                ):
                    raise YoLinkAuthFailError(
                        YoLinkApiCode.AUTH_FAILED, "Local Hub authentication failed"
                    ) from err
                raise YoLinkConnectionError("Token request failed") from err
            except ClientError as err:
                raise YoLinkConnectionError("Token request failed") from err

    async def _token_request(self) -> dict:
        """Make a token request."""
        resp = await self._session.post(
            url=self._token_url,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "client_credentials",
                "scope": "create",
                "client_id": self._client_id,
                "client_secret": self._client_secret,
            },
            timeout=ClientTimeout(total=10),
        )
        if resp.status >= 400:
            _LOGGER.debug(
                "Local Hub token request failed: status=%s",
                resp.status,
            )
        resp.raise_for_status()
        return cast(dict, await resp.json())
