"""Unit tests for the DotterWindow presentation layer."""

from pathlib import Path

from pyglet.window import key

from dotter.demo import build_demo_engine
from dotter.runtime.window import DotterWindow


def test_dotter_window_initialization_and_events(tmp_path: Path) -> None:
    """Verify window initializes headless/hidden and processes advance events."""
    engine = build_demo_engine()
    win = DotterWindow(engine, save_dir=tmp_path / "saves")
    win.set_visible(False)

    try:
        assert win.canvas_viewport.window_width == 1280
        assert win.canvas_viewport.window_height == 720
        assert win.dialogue_box.speaker == "Alice"

        # Advance via space key
        win.on_key_press(key.SPACE, 0)
        # Advance through append, fresh box, narration
        win.on_key_press(key.SPACE, 0)
        win.on_key_press(key.SPACE, 0)

        # Quick save via F5
        win.on_key_press(key.F5, 0)
        assert (tmp_path / "saves" / "slot_quick.json").exists()

        # Quick load via F8
        win.on_key_press(key.F8, 0)

        # Resize event
        win.on_resize(1920, 1080)
        assert win.canvas_viewport.scale == 1.0

        # Mouse click simulation on textbox
        win.on_mouse_press(500, 150, 1, 0)

        # Update tick
        win.update(0.016)
    finally:
        win.close()
