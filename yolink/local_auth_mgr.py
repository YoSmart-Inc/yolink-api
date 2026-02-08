"""Local Hub Authentication Manager."""

import logging
import time

from asyncio import Lock
from .auth_mgr import YoLinkAuthMgr
from aiohttp import ClientSession, ClientError
from json import JSONDecodeError


from typing import cast

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
            new_token = await self._token_request()
            new_token["expires_at"] = time.time() + new_token["expires_in"]
            self._token = new_token
            return self.access_token()

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
        )
        if resp.status >= 400:
            try:
                error_response = await resp.json()
            except (ClientError, JSONDecodeError):
                error_response = {}
            error_code = error_response.get("error", "unknown")
            error_description = error_response.get("error_description", "unknown error")
            _LOGGER.error(
                "Token request failed (%s): %s",
                error_code,
                error_description,
            )
        resp.raise_for_status()
        return cast(dict, await resp.json())
