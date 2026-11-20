"""Hub device and its network-based online status."""

from datetime import datetime, timedelta, timezone
from typing import Any

from ..const import HUB_KEEPALIVE_TIME
from ..device import YoLinkDevice
from ..device_feature import DeviceFeature
from ..device_net_type import DeviceNetType


class YoLinkHub(YoLinkDevice):
    """YoLink hub."""

    def supported_features(self) -> frozenset[DeviceFeature]:
        """Return the capabilities declared for this hub."""
        return self._supported_features

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._hub_online = False
        self._mq_connected: bool | None = None
        self._has_lora = False

    def get_net_type(self) -> DeviceNetType:
        """Return the device network class."""
        return DeviceNetType.HUB

    @property
    def keepalive_time(self) -> int:
        """Return the device keepalive timeout in seconds."""
        return HUB_KEEPALIVE_TIME

    @property
    def is_siren_hub(self) -> bool:
        """Return whether this Hub is a siren Hub."""
        return "YS1614" in self.model

    def _resolve_message(
        self, data: dict[str, Any] | None, event_type: str | None = None
    ) -> None:
        """Update Hub connectivity from the app's network status rules."""
        if not isinstance(data, dict):
            return
        network = data.get("networkInfo")
        if isinstance(network, dict):
            mq = network.get("ylgmq")
            if isinstance(mq, dict) and isinstance(mq.get("connected"), bool):
                self._mq_connected = mq["connected"]
            lora = network.get("lora")
            if isinstance(lora, dict) and isinstance(lora.get("signal"), (int, float)):
                self._has_lora = True

        if event_type not in (
            None,
            "StatusChange",
            "Report",
            "getState",
        ):
            return
        if self._mq_connected is not None or self._has_lora:
            if self._mq_connected is True or (
                self._has_lora
                and self.last_report_at is not None
                and self.last_report_at + timedelta(minutes=130)
                > datetime.now(timezone.utc)
            ):
                self._hub_online = True
        else:
            online = data.get("online")
            self._hub_online = online is True if online is not None else True
            if self._hub_online and not self.is_siren_hub:
                self._mq_connected = True

    def is_online(self) -> bool:
        """Return the Hub online status derived from its network messages."""
        return self._hub_online
