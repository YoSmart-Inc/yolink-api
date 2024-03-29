"""SVR info."""

from dataclasses import dataclass
from enum import Enum


@dataclass(repr=True)
class Endpoint:
    """SVR endpoint."""

    name: str
    host: str
    url: str
    mqtt_broker_host: str
    mqtt_broker_port: int = 8003

    def __init__(self, name: str, host: str):
        """Init SVR Endpoint."""
        self.name = name
        self.host = host
        self.url = f"https://{host}/open/yolink/v2/api"
        self.mqtt_broker_host = host
        self.mqtt_broker_port = 8003


class Endpoints(Enum):
    """All YoLink SVR Endpoints."""

    US: Endpoint = Endpoint(name="US", host="api.yosmart.com")
    EU: Endpoint = Endpoint(name="EU", host="api-eu.yosmart.com")
