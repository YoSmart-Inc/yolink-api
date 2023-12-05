"""YoLink Client Error."""


class YoLinkClientError(Exception):
    """YoLink Client Error.

    code: Error Code
    desc: Desc or Error
    """

    def __init__(
        self,
        code: str,
        desc: str,
    ) -> None:
        """Initialize the yolink api error."""

        self.code = code
        self.message = desc


class YoLinkInitializationError(YoLinkClientError):
    """YoLink Initialization error."""

    def __init__(self, desc: str) -> None:
        super().__init__("-1001", desc)


class YoLinkAuthFailedError(YoLinkClientError):
    """YoLink authenticate failed error."""


class YoLinkDeviceDisconnectedError(YoLinkClientError):
    """YoLink device connection failed error."""


class YoLinkDeviceBusyError(YoLinkClientError):
    """YoLink device is busy currently."""


class YoLinkAPIRateLimitError(YoLinkClientError):
    """YoLink API Rate limit error."""
