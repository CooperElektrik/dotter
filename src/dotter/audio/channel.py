"""Audio channel player and pluggable audio sink interfaces."""

from typing import Protocol

from dotter.core.types import AudioChannel


class AudioSink(Protocol):
    """Low-level audio device sink interface for hardware or headless playback."""

    def play(self, source: str, *, loop: bool, volume: float) -> None:
        """Play audio source."""

    def stop(self) -> None:
        """Stop active playback."""

    def pause(self) -> None:
        """Pause active playback."""

    def resume(self) -> None:
        """Resume paused playback."""

    def set_volume(self, volume: float) -> None:
        """Set output volume level between 0.0 and 1.0."""


class NullAudioSink:
    """Headless recording sink for testing without audio drivers."""

    def __init__(self) -> None:
        self.events: list[str] = []
        self.current_source: str | None = None
        self.is_playing: bool = False
        self.volume: float = 1.0

    def play(self, source: str, *, loop: bool, volume: float) -> None:
        self.current_source = source
        self.is_playing = True
        self.volume = volume
        self.events.append(f"play:{source}:loop={loop}:vol={volume:.2f}")

    def stop(self) -> None:
        self.events.append("stop")
        self.current_source = None
        self.is_playing = False

    def pause(self) -> None:
        self.events.append("pause")

    def resume(self) -> None:
        self.events.append("resume")

    def set_volume(self, volume: float) -> None:
        self.volume = volume
        self.events.append(f"vol:{volume:.2f}")


class AudioChannelPlayer:
    """Manages playback and volume scaling on an individual dedicated channel."""

    def __init__(
        self,
        channel: AudioChannel,
        sink: AudioSink | None = None,
        volume: float = 1.0,
    ) -> None:
        self.channel = channel
        self.sink: AudioSink = sink or NullAudioSink()
        self._volume = max(0.0, min(1.0, volume))
        self.current_track: str | None = None
        self.is_playing = False
        self.is_paused = False

    @property
    def volume(self) -> float:
        """Independent channel volume slider (0.0 to 1.0)."""
        return self._volume

    @volume.setter
    def volume(self, val: float) -> None:
        self._volume = max(0.0, min(1.0, val))

    def calculate_effective_volume(self, master_volume: float, fade_factor: float = 1.0) -> float:
        """Calculate effective output volume incorporating master and fade factors."""
        return max(0.0, min(1.0, self._volume * master_volume * fade_factor))

    def play(
        self,
        track: str,
        *,
        loop: bool = False,
        master_volume: float = 1.0,
        fade_factor: float = 1.0,
    ) -> None:
        """Play a track on this channel."""
        eff_vol = self.calculate_effective_volume(master_volume, fade_factor)
        self.current_track = track
        self.is_playing = True
        self.is_paused = False
        self.sink.play(track, loop=loop, volume=eff_vol)

    def stop(self) -> None:
        """Stop playback on this channel."""
        self.current_track = None
        self.is_playing = False
        self.is_paused = False
        self.sink.stop()

    def pause(self) -> None:
        """Pause playback on this channel."""
        if self.is_playing and not self.is_paused:
            self.is_paused = True
            self.sink.pause()

    def resume(self) -> None:
        """Resume playback on this channel."""
        if self.is_playing and self.is_paused:
            self.is_paused = False
            self.sink.resume()

    def update_volume(self, master_volume: float, fade_factor: float = 1.0) -> None:
        """Re-apply volume level to active sink."""
        eff_vol = self.calculate_effective_volume(master_volume, fade_factor)
        self.sink.set_volume(eff_vol)
