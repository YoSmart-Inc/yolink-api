"""YoLink Basic Model."""
from typing import Dict, Optional
from pydantic import BaseModel

from .exception import YoLinkAuthFailError, YoLinkClientError


class BRDP(BaseModel):
    """BRDP of YoLink API."""

    code: Optional[str]
    desc: Optional[str]
    method: Optional[str]
    data: Dict
    event: Optional[str]

    def check_response(self):
        """Check API Response."""
        if self.code != "000000":
            if self.code == "000103":
                raise YoLinkAuthFailError(self.code, self.desc)
            raise YoLinkClientError(self.code, self.desc)


class BSDPHelper:
    """YoLink API -> BSDP Builder."""

    _bsdp: Dict

    def __init__(self, deviceId: str, deviceToken: str, method: str):
        """Constanst."""
        self._bsdp = {"method": method, "params": {}}
        if deviceId is not None:
            self._bsdp["targetDevice"] = deviceId
            self._bsdp["token"] = deviceToken

    def addParams(self, params: Dict):
        """Build params of BSDP."""
        self._bsdp["params"].update(params)
        return self

    def build(self) -> Dict:
        """Generate BSDP."""
        return self._bsdp
