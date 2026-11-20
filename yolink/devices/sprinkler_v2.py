"""YoLink device implementation."""

from __future__ import annotations

from typing import Any

from ..client_request import ClientRequest
from ..device import YoLinkDevice
from ..device_feature import DeviceFeature
from ..device_net_type import DeviceNetType
from ..model import BRDP


class YoLinkSprinklerV2(YoLinkDevice):
    """YoLink sprinkler controller V2."""

    _supports_battery = True
    _supported_features = frozenset({DeviceFeature.VALVE})

    def get_net_type(self) -> DeviceNetType:
        """Return the device network class."""
        return DeviceNetType.D

    def _resolve_message(
        self, data: dict[str, Any] | None, event_type: str | None = None
    ) -> None:
        """Resolve this device's message in place."""
        if data is not None and ((state := data.get("state")) is not None):
            data["valve"] = state.get("running")

    async def set_valve(self, opened: bool) -> BRDP:
        """Start or stop watering."""
        return await self.call_device(ClientRequest("setState", {"running": opened}))
