"""YoLink authorization manager."""

import abc
from aiohttp import ClientSession


class YoLinkAuthMgr(metaclass=abc.ABCMeta):
    """YoLink API Authentication Manager."""

    def __init__(self, session: ClientSession) -> None:
        """YoLink Auth Manager"""
        self._session = session

    def client_session(self) -> ClientSession:
        """Get client session."""
        return self._session

    @abc.abstractmethod
    def access_token(self) -> str:
        """Get auth token."""

    def http_auth_header(self) -> str:
        """Get auth header."""
        return f"Bearer {self.access_token()}"

    @abc.abstractmethod
    async def check_and_refresh_token(self) -> str:
        """Check and fresh token."""


class YoLinkAccessTokenAuthMgr(YoLinkAuthMgr):
    """YoLink Access Token Authentication Manager.

    For callers that already hold a valid access token, for example right after
    an OAuth exchange. The token cannot be refreshed.
    """

    def __init__(self, session: ClientSession, access_token: str) -> None:
        """Init YoLink Access Token Auth Manager."""
        super().__init__(session)
        self._access_token = access_token

    def access_token(self) -> str:
        """Get auth token."""
        return self._access_token

    async def check_and_refresh_token(self) -> str:
        """Get auth token, it cannot be refreshed."""
        return self._access_token
