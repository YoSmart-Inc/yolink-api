"""YoLink client reqeuest"""

import abc
from .client_reqeust import ClientReqeust


class RequestBuilder(metaclass=abc.ABCMeta):
    """YoLink api client request."""

    def __init__(self) -> None:
        self._method = None

    def method(self, method: str):
        """Set call method"""
        self._method = method
        return self

    @abc.abstractmethod
    def build(self) -> ClientReqeust:
        """Return client reqeust"""
