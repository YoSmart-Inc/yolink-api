"""Outlet reqeust builder"""

from .client_reqeust import ClientReqeust
from .reqeust_builder import RequestBuilder


class OutletReqeustBuilder(RequestBuilder):
    """Outlet request builder"""

    def __init__(self) -> None:
        super().__init__()
        self._state: str = None
        self._plug_index: str | None = None

    @property
    def state(self):
        """Return state"""
        return self._state

    @state.setter
    def state(self, state: str):
        """Set state"""
        self._state = state
        return self

    @property
    def plug_index(self):
        """Return plug index"""
        return self._plug_index

    @plug_index.setter
    def plug_index(self, plug_index: int):
        """Set plug index"""
        self._plug_index = plug_index
        return self

    def build(self) -> ClientReqeust:
        """Create outlet reqeust params"""
        params: dict[str, str | int] = {"state": self._state}
        if self._plug_index is not None:
            params["chs"] = 1 << self._plug_index
        return ClientReqeust(self.method, params)
