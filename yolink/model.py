"""YoLink Basic Model."""

from typing import Any

from pydantic import BaseModel, Field

from .exception import (
    YoLinkApiCode,
    YoLinkAuthFailError,
    YoLinkClientError,
)


class DeviceMessage(BaseModel):
    """A device event received from MQTT."""

    event: str
    time: int | None = None
    msgid: str | int | None = None
    device_id: str | None = Field(default=None, alias="deviceId")
    data: dict[str, Any]


class BRDP(BaseModel):
    """BRDP of YoLink API."""

    code: str | None = None
    desc: str | None = None
    method: str | None = None
    data: dict[str, Any] = None
    event: str | None = None

    def check_response(self) -> None:
        """Check API Response."""
        if self.code != YoLinkApiCode.SUCCESS:
            if self.code in (
                YoLinkApiCode.AUTH_FAILED,
                YoLinkApiCode.INVALID_CLIENT_ID,
                YoLinkApiCode.INVALID_AUTHORIZATION,
                YoLinkApiCode.TOKEN_EXPIRED,
            ):
                raise YoLinkAuthFailError(self.code, self.desc)
            raise YoLinkClientError(self.code, self.desc)


class BSDPHelper:
    """YoLink API -> BSDP Builder."""

    _bsdp: dict

    def __init__(self, device_id: str, device_token: str, method: str):
        """Constanst."""
        self._bsdp = {"method": method, "params": {}}
        if device_id is not None:
            self._bsdp["targetDevice"] = device_id
            self._bsdp["token"] = device_token

    def add_params(self, params: dict):
        """Build params of BSDP."""
        self._bsdp["params"].update(params)
        return self

    def build(self) -> dict:
        """Generate BSDP."""
        return self._bsdp
