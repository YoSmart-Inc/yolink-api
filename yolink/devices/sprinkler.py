"""YoLink device implementation."""

from __future__ import annotations

from typing import Any

from ..client_request import ClientRequest
from ..device import YoLinkDevice, YoLinkDeviceMode
from ..device_feature import DeviceFeature
from ..device_net_type import DeviceNetType
from ..http_client import YoLinkHttpClient
from ..model import BRDP


class YoLinkSprinkler(YoLinkDevice):
    """YoLink sprinkler controller."""

    _supported_features = frozenset({DeviceFeature.VALVE})

    def __init__(self, device: YoLinkDeviceMode, client: YoLinkHttpClient) -> None:
        super().__init__(device, client)
        self._state: dict | None = {}

    def get_net_type(self) -> DeviceNetType:
        """Return the device network class."""
        return DeviceNetType.A

    def _resolve_message(
        self, data: dict[str, Any] | None, event_type: str | None = None
    ) -> None:
        """Resolve watering progress and cache the watering mode."""
        if data is None:
            return
        if (state := data.get("state")) is not None:
            self._state = {"mode": state.get("mode")}

        if state is not None and (watering_data := state.get("watering")) is not None:
            data["valve"] = watering_data["left"] != watering_data["total"]
        if event_type == "waterReport":
            if self._state is not None:
                data["state"] = {"mode": self._state.get("mode")}
            if (event := data.get("event")) is not None:
                data["valve"] = event == "start"

    async def set_mode(self, mode: str) -> BRDP:
        """Set the watering mode and update the cached state from the response."""
        response = await self.call_device(
            ClientRequest("setState", {"state": {"mode": mode}})
        )
        self.resolve_message(response.data)
        return response

    async def set_valve(self, opened: bool) -> BRDP:
        """Start or stop manual watering."""
        return await self.call_device(
            ClientRequest("setManualWater", {"state": "start" if opened else "stop"})
        )
