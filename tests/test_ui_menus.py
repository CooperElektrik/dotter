"""Unit tests for ChoiceOverlay and Menu systems (Title, Pause, Settings)."""

from dotter.core.nodes import ChoiceOption
from dotter.ui.choices import ChoiceOverlay
from dotter.ui.menus import PauseMenu, SettingsMenu, TitleMenu


def test_choice_overlay_keyboard_and_numeric_shortcuts() -> None:
    """Verify choice navigation with arrow keys and numeric 1, 2, 3 shortcuts."""
    overlay = ChoiceOverlay()
    opts = (
        ChoiceOption(text="Go North", target="north"),
        ChoiceOption(text="Go South", target="south"),
        ChoiceOption(text="Stay put", target="camp"),
    )
    overlay.set_choices(opts)
    assert overlay.is_active is True
    assert len(overlay.buttons) == 3

    # Navigate Down
    assert overlay.selected_index == 0
    overlay.handle_key_down("down")
    assert overlay.selected_index == 1

    # Navigate Up
    overlay.handle_key_down("up")
    assert overlay.selected_index == 0

    # Commit with Enter
    chosen = overlay.handle_key_down("enter")
    assert chosen == 0

    # Numeric shortcut '2' -> commits index 1 directly
    shortcut_res = overlay.handle_key_down("2")
    assert shortcut_res == 1


def test_choice_overlay_mouse_hover_and_click() -> None:
    """Verify mouse hover updates selection and click commits index."""
    overlay = ChoiceOverlay()
    opts = (
        ChoiceOption(text="Option A", target="a"),
        ChoiceOption(text="Option B", target="b"),
    )
    overlay.set_choices(opts)

    btn0 = overlay.buttons[0]
    btn1 = overlay.buttons[1]

    # Hover over button 1
    overlay.handle_mouse_move(btn1.x + 10, btn1.y + 10)
    assert overlay.selected_index == 1

    # Click outside buttons
    assert overlay.handle_click(10, 10) is None

    # Click button 0
    clicked = overlay.handle_click(btn0.x + 5, btn0.y + 5)
    assert clicked == 0

    # Clear deactivates
    overlay.clear()
    assert overlay.is_active is False


def test_title_and_pause_menus() -> None:
    """Verify menu layout, keyboard navigation, and escape shortcuts."""
    title = TitleMenu()
    title.open()
    assert title.is_active is True
    assert len(title.buttons) == 4

    # Navigate to 'Load Game' (index 1) and press enter
    title.handle_key_down("down")
    assert title.selected_index == 1
    action = title.handle_key_down("enter")
    assert action == "load"

    # Click 'Start Game'
    btn_start = title.buttons[0]
    clicked_action = title.handle_click(btn_start.x + 5, btn_start.y + 5)
    assert clicked_action == "start"

    # PauseMenu escape key
    pause = PauseMenu()
    pause.open()
    assert pause.handle_key_down("escape") == "resume"


def test_settings_menu_sliders() -> None:
    """Verify audio volume clamping and text speed adjustments."""
    settings = SettingsMenu()
    settings.open()
    assert settings.is_active is True

    settings.set_volume("master", 0.75)
    assert settings.master_volume == 0.75

    # Out of bounds clamping
    settings.set_volume("bgm", 1.5)
    assert settings.bgm_volume == 1.0

    settings.set_volume("voice", -0.2)
    assert settings.voice_volume == 0.0

    # Text speed clamping
    settings.set_text_speed(80.0)
    assert settings.text_speed == 80.0

    settings.set_text_speed(5.0)  # below 10 min
    assert settings.text_speed == 10.0

    # Escape to back
    res = settings.handle_key_down("escape")
    assert res == "back"
    assert settings.is_active is False
