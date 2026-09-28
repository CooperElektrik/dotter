"""Integration tests for rendering pipeline: transitions, menus, and quick actions."""

from pathlib import Path

from pyglet.window import key

from dotter.core.types import AudioChannel, TransitionType
from dotter.demo import build_demo_engine
from dotter.runtime import menu_renderer
from dotter.runtime.window import DotterWindow


def _make_window(tmp_path: Path) -> DotterWindow:
    """Create a hidden DotterWindow with the demo engine."""
    engine = build_demo_engine()
    win = DotterWindow(engine, save_dir=tmp_path / "saves")
    win.set_visible(False)
    return win


def test_menus_instantiated_inactive(tmp_path: Path) -> None:
    """Verify menus are created but not active after window initialization."""
    win = _make_window(tmp_path)
    try:
        assert not win.title_menu.is_active
        assert not win.pause_menu.is_active
        assert not win.settings_menu.is_active
    finally:
        win.close()


def test_transition_triggered_on_init(tmp_path: Path) -> None:
    """Verify BackgroundCommand from on_entry hooks triggers compositor transition."""
    win = _make_window(tmp_path)
    try:
        t = win.compositor.active_transition
        assert t is not None
        assert t.transition_type == TransitionType.DISSOLVE
        assert t.duration == 1.5
        assert t.to_background == "bg_ruins"
        assert win._last_bg == "bg_ruins"
    finally:
        win.close()


def test_transition_progresses_after_update(tmp_path: Path) -> None:
    """Verify transition timer advances and completes via compositor.update."""
    win = _make_window(tmp_path)
    try:
        assert win.compositor.active_transition is not None

        win.update(0.5)
        t = win.compositor.active_transition
        assert t is not None
        assert t.overlay_alpha > 0.0

        win.update(2.0)
        assert win.compositor.active_transition is None
    finally:
        win.close()


def test_escape_opens_and_closes_pause_menu(tmp_path: Path) -> None:
    """Verify Escape opens PauseMenu and Escape again closes it via dispatch."""
    win = _make_window(tmp_path)
    try:
        win.on_key_press(key.ESCAPE, 0)
        assert win.pause_menu.is_active

        win.on_key_press(key.ESCAPE, 0)
        assert not win.pause_menu.is_active
    finally:
        win.close()


def test_title_menu_start_closes_menu(tmp_path: Path) -> None:
    """Verify TitleMenu 'start' action closes the title menu."""
    win = _make_window(tmp_path)
    try:
        win.title_menu.open()
        assert win.title_menu.is_active
        win.on_key_press(key.ENTER, 0)
        assert not win.title_menu.is_active
    finally:
        win.close()


def test_settings_quick_button_opens_settings(tmp_path: Path) -> None:
    """Verify clicking the Settings quick button opens the SettingsMenu."""
    win = _make_window(tmp_path)
    try:
        assert not win.settings_menu.is_active
        # Settings button center at virtual (1500, 329), window (1000, 219) for 1280x720
        win.on_mouse_press(1000, 219, 1, 0)
        assert win.settings_menu.is_active
        win.settings_menu.close()
    finally:
        win.close()


def test_settings_volume_syncs_to_audio(tmp_path: Path) -> None:
    """Verify open_settings syncs SettingsMenu volumes to AudioManager."""
    win = _make_window(tmp_path)
    try:
        win.settings_menu.master_volume = 0.5
        win.settings_menu.bgm_volume = 0.3
        menu_renderer.open_settings(win.settings_menu, win.audio)
        assert win.audio.master_volume == 0.5
        assert win.audio.channels[AudioChannel.BGM].volume == 0.3
        win.settings_menu.close()
    finally:
        win.close()


def test_log_button_toggles_history(tmp_path: Path) -> None:
    """Verify the Log quick button toggles the dialogue history overlay."""
    win = _make_window(tmp_path)
    try:
        assert not win._log_active
        # Log button center at virtual (1390, 329), window (927, 219) for 1280x720
        win.on_mouse_press(927, 219, 1, 0)
        assert win._log_active
        win.on_mouse_press(927, 219, 1, 0)
        assert not win._log_active
    finally:
        win.close()


def test_dialogue_history_populated(tmp_path: Path) -> None:
    """Verify _sync_beat appends dialogue and narration lines to history."""
    win = _make_window(tmp_path)
    try:
        assert len(win._dialogue_history) >= 1
        speaker, text = win._dialogue_history[0]
        assert speaker == "Alice"
        assert len(text) > 0
    finally:
        win.close()
