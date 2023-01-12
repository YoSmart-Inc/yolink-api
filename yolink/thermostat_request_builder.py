"""Thermostat request builder"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel

from .client_request import ClientRequest


class ThermostatState(BaseModel):
    """Thermostat State."""

    low_temp: Optional[float]
    high_temp: Optional[float]
    mode: Optional[str]
    fan_mode: Optional[str]
    sche: Optional[str]


class ThermostatRequestBuilder:  # pylint: disable=too-few-public-methods
    """Thermostat request builder"""

    @classmethod
    def set_state_request(cls, state: ThermostatState) -> ClientRequest:
        """Set device state."""
        return ClientRequest("setState", state.dict(exclude_none=True))

    @classmethod
    def set_eco_request(cls, state: str) -> ClientRequest:
        """Enable/Disable eco mode."""
        return ClientRequest("setECO", {"mode": state})
