"""Audio manager orchestrating 4 dedicated channels, volume scaling, and BGM crossfading."""

from collections.abc import Callable
from dataclasses import dataclass

from dotter.audio.channel import AudioChannelPlayer, AudioSink, NullAudioSink
from dotter.core.types import AudioChannel


@dataclass(slots=True)
class CrossfadeState:
    """Active crossfade between outgoing and incoming audio sinks."""

    outgoing_sink: AudioSink
    incoming_sink: AudioSink
    duration: float
    elapsed: float = 0.0

    def update(self, dt: float, master_vol: float, bgm_vol: float) -> bool:
        """Advance crossfade timers and update opposing volume ramps."""
        self.elapsed += dt
        progress = min(1.0, self.elapsed / self.duration) if self.duration > 0 else 1.0

        out_vol = max(0.0, min(1.0, bgm_vol * master_vol * (1.0 - progress)))
        in_vol = max(0.0, min(1.0, bgm_vol * master_vol * progress))

        self.outgoing_sink.set_volume(out_vol)
        self.incoming_sink.set_volume(in_vol)

        if progress >= 1.0:
            self.outgoing_sink.stop()
            return True
        return False


class AudioManager:
    """Orchestrates BGM, VOICE, SFX, and AMB dedicated channels."""

    def __init__(self, sink_factory: Callable[[], AudioSink] | None = None) -> None:
        self._sink_factory = sink_factory or NullAudioSink
        self._master_volume = 1.0
        self._crossfade: CrossfadeState | None = None

        self.channels: dict[AudioChannel, AudioChannelPlayer] = {
            ch: AudioChannelPlayer(channel=ch, sink=self._sink_factory()) for ch in AudioChannel
        }

    @property
    def master_volume(self) -> float:
        """Global master volume slider (0.0 to 1.0)."""
        return self._master_volume

    @property
    def is_crossfading(self) -> bool:
        """True if a BGM crossfade is currently active."""
        return self._crossfade is not None

    @master_volume.setter
    def master_volume(self, val: float) -> None:
        self._master_volume = max(0.0, min(1.0, val))
        for player in self.channels.values():
            player.update_volume(self._master_volume)

    def set_channel_volume(self, channel: AudioChannel, volume: float) -> None:
        """Set volume on a specific dedicated channel."""
        player = self.channels[channel]
        player.volume = volume
        player.update_volume(self._master_volume)

    def play_bgm(self, track: str | None, *, loop: bool = True, crossfade: float = 0.0) -> None:
        """Play or crossfade background music track."""
        bgm_player = self.channels[AudioChannel.BGM]

        if track is None:
            bgm_player.stop()
            self._crossfade = None
            return

        if crossfade > 0.0 and bgm_player.is_playing:
            # Dual-player crossfade
            old_sink = bgm_player.sink
            new_sink = self._sink_factory()
            bgm_player.sink = new_sink
            bgm_player.play(track, loop=loop, master_volume=self._master_volume, fade_factor=0.0)

            self._crossfade = CrossfadeState(
                outgoing_sink=old_sink,
                incoming_sink=new_sink,
                duration=crossfade,
            )
        else:
            self._crossfade = None
            bgm_player.play(track, loop=loop, master_volume=self._master_volume)

    def play_voice(self, clip: str | None) -> None:
        """Play character voice line, stopping any currently speaking line."""
        voice_player = self.channels[AudioChannel.VOICE]
        if clip is None:
            voice_player.stop()
            return
        voice_player.play(clip, loop=False, master_volume=self._master_volume)

    def stop_voice(self) -> None:
        """Immediately stop character speech."""
        self.channels[AudioChannel.VOICE].stop()

    def play_sfx(self, clip: str, *, volume: float = 1.0) -> None:
        """Trigger a one-shot sound effect."""
        sfx_player = self.channels[AudioChannel.SFX]
        eff_vol = self._master_volume * sfx_player.volume * max(0.0, min(1.0, volume))
        sfx_player.sink.play(clip, loop=False, volume=eff_vol)

    def play_ambience(self, track: str | None, *, loop: bool = True) -> None:
        """Play or stop looping ambient audio."""
        amb_player = self.channels[AudioChannel.AMB]
        if track is None:
            amb_player.stop()
            return
        amb_player.play(track, loop=loop, master_volume=self._master_volume)

    def advance_beat(self) -> None:
        """Handle dialogue beat advancement by auto-stopping dialogue voice."""
        self.stop_voice()

    def update(self, dt: float) -> None:
        """Update crossfade interpolation."""
        if self._crossfade is not None:
            bgm_vol = self.channels[AudioChannel.BGM].volume
            finished = self._crossfade.update(dt, self._master_volume, bgm_vol)
            if finished:
                self._crossfade = None
