"""YoLink API and library exceptions."""

from enum import Enum


class YoLinkApiCode(str, Enum):
    """API codes"""

    SUCCESS = "000000"
    HUB_CONNECTION_FAILED = "000101"
    HUB_COMMAND_FAILED = "000102"
    AUTH_FAILED = "000103"
    INVALID_HUB_TOKEN = "000104"
    MISSING_REDIRECT_URI = "000105"
    INVALID_CLIENT_ID = "000106"
    DEVICE_CONNECTION_FAILED = "000201"
    DEVICE_COMMAND_FAILED = "000202"
    DEVICE_UNREACHABLE = "000203"
    SERVICE_UNAVAILABLE = "010000"
    INTERNAL_CONNECTION_UNAVAILABLE = "010001"
    INVALID_CSID = "010101"
    INVALID_SEC_KEY = "010102"
    INVALID_AUTHORIZATION = "010103"
    TOKEN_EXPIRED = "010104"
    INVALID_PARAMS = "010200"
    MISSING_TIME = "010201"
    MISSING_METHOD = "010202"
    UNSUPPORTED_METHOD = "010203"
    INVALID_PACKET = "010204"
    ACCESS_RESTRICTED = "010300"
    RATE_LIMITED = "010301"
    DEVICE_ALREADY_BOUND = "020100"
    DEVICE_NOT_FOUND = "020101"
    INVALID_DEVICE_MASK = "020102"
    UNSUPPORTED_DEVICE = "020103"
    DEVICE_BUSY = "020104"
    DEVICE_RETRIEVAL_FAILED = "020105"
    NO_DEVICES_FOUND = "020201"
    NO_DATA = "030101"
    UNKNOWN_ERROR = "999999"


class YoLinkError(Exception):
    """YoLink Error."""


class YoLinkConfigError(YoLinkError):
    """Missing configuration or uninitialized client."""


class YoLinkConnectionError(YoLinkError):
    """HTTP transport or response status failure."""


class YoLinkTimeoutError(YoLinkConnectionError):
    """HTTP request timed out."""


class YoLinkClientError(YoLinkError):
    """YoLink Client Error.

    code: Error Code
    desc: Desc or Error
    """

    def __init__(
        self,
        code: str | None,
        desc: str | None,
    ) -> None:
        """Initialize the yolink api error."""

        self.code = code
        self.message = desc
        super().__init__(f"{code}: {desc}")


class YoLinkAuthFailError(YoLinkClientError):
    """YoLink auth failed"""
