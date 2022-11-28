"""Outlet reqeust builder"""
from __future__ import annotations

from .client_reqeust import ClientReqeust


class OutletReqeustBuilder:
    """Outlet request builder"""

    @classmethod
    def set_state_reqeust(cls, state: str, plug_indx: int | None) -> ClientReqeust:
        """Set device state."""
        params: dict[str, str | int] = {"state": state}
        if plug_indx is not None:
            params["chs"] = 1 << plug_indx
        return ClientReqeust("setState", params)
