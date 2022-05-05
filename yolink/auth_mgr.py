"""YoLink authorization manager."""
import abc
from aiohttp import ClientSession


class YoLinkAuthMgr(metaclass=abc.ABCMeta):
    """YoLink API Authentication Manager."""

    def __init__(self, webSession: ClientSession) -> None:
        """YoLink Auth Manager"""
        self.webSession = webSession

    def client_session(self) -> ClientSession:
        """Get client session."""
        return self.webSession

    @abc.abstractmethod
    def access_token(self) -> str:
        """Get auth token."""

    def http_auth_header(self) -> str:
        """Get auth header."""
        return f"Bearer {self.access_token()}"

    @abc.abstractmethod
    async def check_and_refresh_token(self) -> str:
        """Check and fresh token."""
