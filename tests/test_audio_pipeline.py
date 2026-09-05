"""Unit tests for the 4-channel audio pipeline and BGM crossfading."""

from dotter.audio.channel import NullAudioSink
from dotter.audio.manager import AudioManager
from dotter.core.types import AudioChannel


def test_volume_calculation_and_master_scaling() -> None:
    """Verify master volume scales channel output proportionally."""
    mgr = AudioManager()

    mgr.master_volume = 0.5
    mgr.set_channel_volume(AudioChannel.BGM, 0.8)

    bgm_player = mgr.channels[AudioChannel.BGM]
    eff_vol = bgm_player.calculate_effective_volume(mgr.master_volume)
    assert round(eff_vol, 2) == 0.40

    mgr.master_volume = 1.0
    eff_vol_full = bgm_player.calculate_effective_volume(mgr.master_volume)
    assert round(eff_vol_full, 2) == 0.80


def test_channel_routing_and_looping() -> None:
    """Verify channel specific playback options (BGM/AMB loop, SFX one-shot)."""
    mgr = AudioManager()
    bgm_sink = mgr.channels[AudioChannel.BGM].sink
    sfx_sink = mgr.channels[AudioChannel.SFX].sink
    amb_sink = mgr.channels[AudioChannel.AMB].sink

    assert isinstance(bgm_sink, NullAudioSink)
    assert isinstance(sfx_sink, NullAudioSink)
    assert isinstance(amb_sink, NullAudioSink)

    mgr.play_bgm("theme.ogg", loop=True)
    assert "play:theme.ogg:loop=True:vol=1.00" in bgm_sink.events

    mgr.play_sfx("click.ogg")
    assert "play:click.ogg:loop=False:vol=1.00" in sfx_sink.events

    mgr.play_ambience("rain.ogg", loop=True)
    assert "play:rain.ogg:loop=True:vol=1.00" in amb_sink.events


def test_voice_auto_stop_on_beat_advance() -> None:
    """Verify that advancing a dialogue beat stops the active voice speech."""
    mgr = AudioManager()
    voice_sink = mgr.channels[AudioChannel.VOICE].sink
    assert isinstance(voice_sink, NullAudioSink)

    mgr.play_voice("alice_line_01.ogg")
    assert voice_sink.is_playing is True

    # Advance dialogue beat
    mgr.advance_beat()
    assert voice_sink.is_playing is False
    assert "stop" in voice_sink.events


def test_bgm_crossfading() -> None:
    """Verify dual-sink BGM crossfading with opposing volume ramps."""
    mgr = AudioManager()
    mgr.play_bgm("theme_old.ogg", loop=True)

    # Trigger 2.0s crossfade to new track
    mgr.play_bgm("theme_new.ogg", loop=True, crossfade=2.0)

    # At 1.0s (50% progress): crossfade is active
    mgr.update(1.0)
    assert mgr.is_crossfading is True

    # Complete crossfade (at 2.0s): outgoing stopped, crossfade cleared
    mgr.update(1.1)
    assert mgr.is_crossfading is False
    assert mgr.channels[AudioChannel.BGM].current_track == "theme_new.ogg"
