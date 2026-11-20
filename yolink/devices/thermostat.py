"""YoLink device implementation."""

from __future__ import annotations

from pydantic import BaseModel

from ..client_request import ClientRequest
from ..const import CLASS_C_KEEPALIVE_TIME
from ..device import YoLinkDevice
from ..device_feature import DeviceFeature
from ..device_net_type import DeviceNetType
from ..model import BRDP


class ThermostatState(BaseModel):
    """Thermostat state used in setState requests."""

    lowTemp: float | None = None
    highTemp: float | None = None
    mode: str | None = None
    fan: str | None = None
    sche: str | None = None


class YoLinkThermostat(YoLinkDevice):
    """YoLink thermostat."""

    _supported_features = frozenset({DeviceFeature.THERMOSTAT})

    def get_net_type(self) -> DeviceNetType:
        """Return the device network class."""
        return DeviceNetType.C

    @property
    def keepalive_time(self) -> int:
        """Return the device keepalive timeout in seconds."""
        return CLASS_C_KEEPALIVE_TIME

    async def set_state(self, state: ThermostatState) -> BRDP:
        """Set thermostat state and return the device response."""
        request = ClientRequest("setState", state.model_dump(exclude_none=True))
        return await self.call_device(request)

    async def set_eco(self, state: str) -> BRDP:
        """Change eco mode and return the device response."""
        return await self.call_device(ClientRequest("setECO", {"mode": state}))
