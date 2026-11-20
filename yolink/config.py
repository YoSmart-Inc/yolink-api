"""Runtime configuration for the YoLink library."""

from dataclasses import dataclass


@dataclass
class YoLinkConfig:
    """Library behavior options."""

    enable_message_conversion: bool = True


config = YoLinkConfig()
