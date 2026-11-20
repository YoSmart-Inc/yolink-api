"""YoLink device implementation."""

from ..client_request import ClientRequest
from ..device_feature import DeviceFeature
from ..model import BRDP
from .hub import YoLinkHub


class YoLinkSpeakerHub(YoLinkHub):
    """YoLink speaker hub."""

    _supported_features = frozenset({DeviceFeature.SPEAKER_HUB, DeviceFeature.VOLUME})

    async def set_volume(self, volume: float) -> BRDP:
        """Set the speaker's default volume."""
        return await self.call_device(ClientRequest("setOption", {"volume": volume}))

    async def play_audio(
        self,
        message: str,
        *,
        repeat: int = 0,
        volume: int | None = None,
        tone: str | None = None,
    ) -> BRDP:
        """Play a text message with optional playback settings."""
        params: dict[str, str | int] = {"message": message, "repeat": repeat}
        if volume is not None:
            params["volume"] = volume
        if tone is not None:
            params["tone"] = tone.capitalize()
        return await self.call_device(ClientRequest("playAudio", params))
