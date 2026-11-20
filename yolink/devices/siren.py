"""YoLink device implementation."""

from typing import Any

from ..client_request import ClientRequest
from ..const import CLASS_C_KEEPALIVE_TIME
from ..device import YoLinkDevice, YoLinkDeviceMode
from ..device_feature import DeviceFeature
from ..device_net_type import DeviceNetType
from ..http_client import YoLinkHttpClient
from ..model import BRDP


class YoLinkSiren(YoLinkDevice):
    """YoLink siren."""

    _supports_battery = True
    _supported_features = frozenset({DeviceFeature.SIREN})

    def __init__(self, device: YoLinkDeviceMode, client: YoLinkHttpClient) -> None:
        super().__init__(device, client)
        self._state: dict[str, Any] = {}

    def get_net_type(self) -> DeviceNetType:
        """Return the device network class."""
        return (
            DeviceNetType.D
            if any(model in self.model for model in ("YS7104", "YS7105", "YS7107"))
            else DeviceNetType.C
        )

    @property
    def keepalive_time(self) -> int:
        """Return the device keepalive timeout in seconds."""
        if self.class_mode in (DeviceNetType.C, DeviceNetType.E):
            return CLASS_C_KEEPALIVE_TIME
        return super().keepalive_time

    def _resolve_message(
        self, data: dict[str, Any] | None, event_type: str | None = None
    ) -> None:
        """Track the siren state from state responses and reports."""
        if event_type not in (
            None,
            "StatusChange",
            "getState",
            "setState",
            "setMute",
            "Alert",
            "Report",
        ):
            return
        if data is not None:
            self._state.update(data)

    def is_online(self) -> bool:
        """Return whether the siren has a recent report and is powered on."""
        return super().is_online() and self._state.get("state") != "off"

    async def set_alarm(self, enabled: bool) -> BRDP:
        """Turn the audible alarm on or off."""
        return await self.call_device(
            ClientRequest("setState", {"state": {"alarm": enabled}})
        )
