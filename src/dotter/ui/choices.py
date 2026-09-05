"""Choice overlay displaying vertically stacked buttons with keyboard and mouse input."""

from dataclasses import dataclass

from dotter.core.nodes import ChoiceOption

BUTTON_WIDTH = 800.0
BUTTON_HEIGHT = 60.0
BUTTON_GAP = 20.0
CANVAS_CENTER_X = 960.0
CANVAS_CENTER_Y = 540.0


@dataclass(frozen=True, slots=True)
class ChoiceBox:
    """Bounding box for an individual choice button."""

    index: int
    text: str
    x: float
    y: float
    width: float
    height: float

    def contains(self, px: float, py: float) -> bool:
        """True if virtual coordinate is inside button bounds."""
        return self.x <= px <= self.x + self.width and self.y <= py <= self.y + self.height


class ChoiceOverlay:
    """Renders and manages decision choices with keyboard arrows, numbers, and mouse."""

    def __init__(self) -> None:
        self.options: tuple[ChoiceOption, ...] = ()
        self.selected_index = 0
        self.is_active = False
        self._buttons: list[ChoiceBox] = []

    def set_choices(self, options: tuple[ChoiceOption, ...]) -> None:
        """Activate choice overlay with new set of branch choices."""
        self.options = options
        self.selected_index = 0
        self.is_active = bool(options)
        self._recalculate_layout()

    def clear(self) -> None:
        """Deactivate choice overlay."""
        self.options = ()
        self.selected_index = 0
        self.is_active = False
        self._buttons.clear()

    def _recalculate_layout(self) -> None:
        self._buttons.clear()
        count = len(self.options)
        if count == 0:
            return

        total_height = count * BUTTON_HEIGHT + (count - 1) * BUTTON_GAP
        start_y = CANVAS_CENTER_Y - (total_height / 2.0)
        btn_x = CANVAS_CENTER_X - (BUTTON_WIDTH / 2.0)

        for i, opt in enumerate(self.options):
            # Top-to-bottom layout in OpenGL Y-up coordinates
            btn_y = start_y + (count - 1 - i) * (BUTTON_HEIGHT + BUTTON_GAP)
            self._buttons.append(
                ChoiceBox(
                    index=i,
                    text=opt.text,
                    x=btn_x,
                    y=btn_y,
                    width=BUTTON_WIDTH,
                    height=BUTTON_HEIGHT,
                )
            )

    @property
    def buttons(self) -> tuple[ChoiceBox, ...]:
        """Current button layouts."""
        return tuple(self._buttons)

    def handle_mouse_move(self, vx: float, vy: float) -> None:
        """Update selected index based on mouse hover."""
        if not self.is_active:
            return
        for btn in self._buttons:
            if btn.contains(vx, vy):
                self.selected_index = btn.index
                break

    def handle_click(self, vx: float, vy: float) -> int | None:
        """Commit choice if clicked within a button."""
        if not self.is_active:
            return None
        for btn in self._buttons:
            if btn.contains(vx, vy):
                self.selected_index = btn.index
                return btn.index
        return None

    def handle_key_down(self, key_name: str) -> int | None:
        """Handle keyboard navigation: UP/DOWN arrows, ENTER/SPACE, and numeric keys."""
        if not self.is_active or not self.options:
            return None

        count = len(self.options)
        normalized = key_name.lower()

        if normalized in ("up", "w"):
            self.selected_index = (self.selected_index - 1) % count
            return None

        if normalized in ("down", "s"):
            self.selected_index = (self.selected_index + 1) % count
            return None

        if normalized in ("enter", "return", "space"):
            return self.selected_index

        if normalized.isdigit():
            num = int(normalized)
            if 1 <= num <= count:
                self.selected_index = num - 1
                return self.selected_index

        return None
