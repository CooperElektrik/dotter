"""Unit tests for Typewriter reveal engine and DialogueBox UI."""

from dotter.ui.dialogue import BUTTON_RECTS, DialogueBox
from dotter.ui.typewriter import (
    PauseToken,
    StylePopToken,
    StylePushToken,
    TextChar,
    Typewriter,
    WaitClickToken,
    tokenize_text,
)


def test_tokenize_rich_text_and_variables() -> None:
    """Verify variable interpolation and token generation for BBCode and pacing tags."""
    raw = "Hello, {name}! [b]Look[/b] {w} at this {p=0.5} shining star."
    vars_dict = {"name": "Alice"}

    tokens = tokenize_text(raw, vars_dict)

    # Check variable expanded
    first_few_chars = "".join(t.char for t in tokens if isinstance(t, TextChar))[:12]
    assert first_few_chars == "Hello, Alice"

    # Check tags present
    has_b_push = any(isinstance(t, StylePushToken) and t.tag == "b" for t in tokens)
    has_b_pop = any(isinstance(t, StylePopToken) and t.tag == "b" for t in tokens)
    has_wait = any(isinstance(t, WaitClickToken) for t in tokens)
    has_pause = any(isinstance(t, PauseToken) and t.duration == 0.5 for t in tokens)

    assert has_b_push is True
    assert has_b_pop is True
    assert has_wait is True
    assert has_pause is True


def test_typewriter_incremental_reveal() -> None:
    """Verify typewriter advances characters per delta time."""
    tw = Typewriter(chars_per_second=10.0)  # 0.1s per char
    tw.set_text("ABC")

    assert tw.visible_text == ""
    assert tw.is_complete is False

    tw.update(0.1)
    assert tw.visible_text == "A"

    tw.update(0.2)
    assert tw.visible_text == "ABC"
    assert tw.is_complete is True


def test_typewriter_wait_and_pause() -> None:
    """Verify wait for click and timed delay behavior."""
    tw = Typewriter(chars_per_second=20.0)  # 0.05s per char
    tw.set_text("A{w}B{p=0.2}C")

    tw.update(0.1)  # reveals 'A' and hits {w}
    assert tw.visible_text == "A"
    assert tw.is_waiting_for_click is True

    # Cannot advance while waiting for click
    tw.update(0.5)
    assert tw.visible_text == "A"

    # Click unpauses
    unpaused = tw.click()
    assert unpaused is True
    assert tw.is_waiting_for_click is False

    # Reveals 'B' and hits {p=0.2}
    tw.update(0.06)
    assert tw.visible_text == "AB"

    # During pause
    tw.update(0.1)
    assert tw.visible_text == "AB"

    # Pause expires -> reveals 'C'
    tw.update(0.15)
    assert tw.visible_text == "ABC"
    assert tw.is_complete is True


def test_dialogue_box_quick_buttons_and_auto_mode() -> None:
    """Verify quick button click hits and auto mode timer advancement."""
    box = DialogueBox(chars_per_second=50.0)
    box.set_dialogue("Alice", "Testing the dialogue box.")

    assert box.speaker == "Alice"

    # Hit test a quick button (e.g. Save)
    save_btn = next(b for b in BUTTON_RECTS if b.name == "Save")
    action = box.handle_click(save_btn.x + 5, save_btn.y + 5)
    assert action == "save"

    # Toggle Auto button
    auto_btn = next(b for b in BUTTON_RECTS if b.name == "Auto")
    action_auto = box.handle_click(auto_btn.x + 5, auto_btn.y + 5)
    assert action_auto == "auto"
    assert box.auto_mode is True

    # Complete text and check auto advance
    box.typewriter.skip_to_end()
    assert box.typewriter.is_complete is True

    box.auto_delay = 0.5
    advance_req = box.update(0.3)
    assert advance_req is False

    advance_req_after = box.update(0.3)
    assert advance_req_after is True


def test_dialogue_box_append_and_skip() -> None:
    """Verify appending text and instant skip mode."""
    box = DialogueBox(chars_per_second=20.0)
    box.set_dialogue("Bob", "Line 1.")
    box.typewriter.skip_to_end()
    assert box.typewriter.visible_text == "Line 1."

    box.append_dialogue(" Line 2.")
    box.toggle_skip()
    assert box.skip_mode is True

    advance_signal = box.update(0.01)
    assert advance_signal is True
    assert box.typewriter.visible_text == "Line 1. Line 2."
