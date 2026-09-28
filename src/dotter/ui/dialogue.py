"""Dialogue box UI component managing text display, nameplate, and quick actions."""

from dataclasses import dataclass
from typing import Any

from dotter.ui.typewriter import Typewriter

BOX_X = 200
BOX_Y = 50
BOX_WIDTH = 1520
BOX_HEIGHT = 250

NAMEPLATE_X = 200
NAMEPLATE_Y = 305
NAMEPLATE_WIDTH = 300
NAMEPLATE_HEIGHT = 50

QUICK_BUTTON_NAMES = ("Save", "Load", "Auto", "Skip", "Log", "Settings")
BUTTON_WIDTH = 100
BUTTON_HEIGHT = 38
BUTTON_START_X = 900
BUTTON_Y = 310
BUTTON_GAP = 10


@dataclass(frozen=True, slots=True)
class ButtonRect:
    """Bounding box for a quick action button."""

    name: str
    x: float
    y: float
    width: float
    height: float

    def contains(self, px: float, py: float) -> bool:
        """Check if point is inside button bounds."""
        return self.x <= px <= self.x + self.width and self.y <= py <= self.y + self.height


def _build_button_rects() -> list[ButtonRect]:
    buttons: list[ButtonRect] = []
    for i, name in enumerate(QUICK_BUTTON_NAMES):
        bx = BUTTON_START_X + i * (BUTTON_WIDTH + BUTTON_GAP)
        buttons.append(
            ButtonRect(
                name=name,
                x=float(bx),
                y=float(BUTTON_Y),
                width=float(BUTTON_WIDTH),
                height=float(BUTTON_HEIGHT),
            )
        )
    return buttons


BUTTON_RECTS = _build_button_rects()


class DialogueBox:
    """Manages the dialogue textbox, speaker nameplate, and quick action buttons."""

    def __init__(self, chars_per_second: float = 40.0) -> None:
        self.typewriter = Typewriter(chars_per_second)
        self.speaker: str | None = None
        self.auto_mode = False
        self.skip_mode = False
        self.auto_delay = 1.5
        self.auto_timer = 0.0

    def set_dialogue(
        self,
        speaker: str | None,
        text: str,
        variables: dict[str, Any] | None = None,
        emotion: str | None = None,
    ) -> None:
        """Open a fresh dialogue box with given speaker, text, and emotion."""
        self.speaker = speaker
        self.emotion = emotion
        self.typewriter.set_text(text, variables)
        self.auto_timer = 0.0

    def append_dialogue(self, text: str, variables: dict[str, Any] | None = None) -> None:
        """Append text to active dialogue box."""
        self.typewriter.append_text(text, variables)
        self.auto_timer = 0.0

    def toggle_auto(self) -> bool:
        """Toggle auto-forward mode."""
        self.auto_mode = not self.auto_mode
        if self.auto_mode:
            self.skip_mode = False
        self.auto_timer = 0.0
        return self.auto_mode

    def toggle_skip(self) -> bool:
        """Toggle skip-to-next mode."""
        self.skip_mode = not self.skip_mode
        if self.skip_mode:
            self.auto_mode = False
            self.typewriter.skip_to_end()
        return self.skip_mode

    def update(self, dt: float) -> bool:
        """Update dialogue typewriter and auto-advance timers. Returns True if advance requested."""
        if self.skip_mode:
            self.typewriter.skip_to_end()
            return True

        self.typewriter.update(dt)

        if self.auto_mode and self.typewriter.is_complete:
            self.auto_timer += dt
            if self.auto_timer >= self.auto_delay:
                self.auto_timer = 0.0
                return True
        else:
            self.auto_timer = 0.0

        return False

    def handle_click(self, vx: float, vy: float) -> str | None:
        """Process click in virtual coordinates and return action name."""
        for btn in BUTTON_RECTS:
            if btn.contains(vx, vy):
                action = btn.name.lower()
                if action == "auto":
                    self.toggle_auto()
                elif action == "skip":
                    self.toggle_skip()
                return action

        in_box = BOX_X <= vx <= BOX_X + BOX_WIDTH and BOX_Y <= vy <= BOX_Y + BOX_HEIGHT
        in_nameplate = (
            NAMEPLATE_X <= vx <= NAMEPLATE_X + NAMEPLATE_WIDTH
            and NAMEPLATE_Y <= vy <= NAMEPLATE_Y + NAMEPLATE_HEIGHT
        )

        if in_box or in_nameplate:
            handled = self.typewriter.click()
            return "click" if handled else "advance"

        return None
