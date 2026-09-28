"""Integration tests for AudioManager command routing through DotterWindow."""

from pathlib import Path

from dotter.audio.channel import NullAudioSink
from dotter.core.types import AudioChannel
from dotter.demo import build_demo_engine
from dotter.runtime.window import DotterWindow


def _make_window(tmp_path: Path) -> DotterWindow:
    """Create a hidden DotterWindow with the demo engine."""
    engine = build_demo_engine()
    win = DotterWindow(engine, save_dir=tmp_path / "saves")
    win.set_visible(False)
    return win


def test_audio_manager_initialized_with_four_channels(tmp_path: Path) -> None:
    """Verify window instantiates AudioManager with all four channels."""
    win = _make_window(tmp_path)
    try:
        assert len(win.audio.channels) == 4
        for ch in AudioChannel:
            assert ch in win.audio.channels
            assert isinstance(win.audio.channels[ch].sink, NullAudioSink)
    finally:
        win.close()


def test_on_entry_audio_commands_routed(tmp_path: Path) -> None:
    """Verify MusicCommand and AmbienceCommand from on_entry hooks reach audio sinks."""
    win = _make_window(tmp_path)
    try:
        bgm = win.audio.channels[AudioChannel.BGM].sink
        amb = win.audio.channels[AudioChannel.AMB].sink

        assert isinstance(bgm, NullAudioSink)
        assert isinstance(amb, NullAudioSink)
        # on_entry("start") dispatched MusicCommand("theme_ancient.ogg")
        assert any("play:theme_ancient.ogg" in e for e in bgm.events)
        # and AmbienceCommand("wind.ogg")
        assert any("play:wind.ogg" in e for e in amb.events)
    finally:
        win.close()


def test_voice_played_on_dialogue_sync(tmp_path: Path) -> None:
    """Verify DialogueNode.voice triggers playback on the voice channel."""
    win = _make_window(tmp_path)
    try:
        voice = win.audio.channels[AudioChannel.VOICE].sink
        assert isinstance(voice, NullAudioSink)
        # First node is DialogueNode(Alice) with voice:alice_01.ogg
        assert any("play:alice_01.ogg" in e for e in voice.events)
    finally:
        win.close()


def test_voice_stops_on_beat_advance(tmp_path: Path) -> None:
    """Verify advance_beat() stops current voice when moving past a dialogue line."""
    win = _make_window(tmp_path)
    try:
        voice = win.audio.channels[AudioChannel.VOICE].sink
        assert isinstance(voice, NullAudioSink)

        # First SPACE: skip typewriter to end
        win.advance()
        # Second SPACE: _step_engine advances to AppendNode → advance_beat stops voice
        win.advance()

        assert any("stop" in e for e in voice.events)
    finally:
        win.close()


def test_sfx_routed_from_hook_after_advance(tmp_path: Path) -> None:
    """Verify SfxCommand from inspect_ruins hook reaches the SFX channel."""
    win = _make_window(tmp_path)
    try:
        sfx = win.audio.channels[AudioChannel.SFX].sink
        assert isinstance(sfx, NullAudioSink)
        assert not any("discover" in e for e in sfx.events)

        # Advance through: Alice(skip+step) → Append(skip+step) →
        # FreshBox(skip+step) → Narration1(skip+step) → Narration2(skip+step)
        # = 10 advances reaches the HookNode(inspect_ruins) → DialogueNode(Bob)
        for _ in range(10):
            win.advance()

        assert any("play:discover.ogg" in e for e in sfx.events)
    finally:
        win.close()


def test_bgm_crossfade_on_fade_in_command(tmp_path: Path) -> None:
    """Verify MusicCommand with fade_in triggers BGM crossfade."""
    win = _make_window(tmp_path)
    try:
        bgm = win.audio.channels[AudioChannel.BGM].sink

        # Advance to puzzle_chamber: 10 to reach Bob, +2 to trigger CallNode
        for _ in range(10):
            win.advance()
        win.advance()  # skip Bob's text
        win.advance()  # step → CallNode → puzzle_chamber on_entry → MusicCommand(fade_in=2.0)

        assert win.audio.is_crossfading is True
        # Re-fetch: crossfade swaps the BGM player's sink to a new instance
        bgm = win.audio.channels[AudioChannel.BGM].sink
        assert isinstance(bgm, NullAudioSink)
        assert any("play:theme_puzzle.ogg" in e for e in bgm.events)

        # Complete the crossfade directly (avoid dt side-effects on typewriter)
        win.audio.update(2.1)
        assert win.audio.is_crossfading is False
    finally:
        win.close()
