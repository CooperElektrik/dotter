"""Title, Pause, and Settings menu state machines and layout."""

from dataclasses import dataclass

MENU_BTN_WIDTH = 350.0
MENU_BTN_HEIGHT = 50.0
MENU_BTN_GAP = 15.0
CANVAS_CENTER_X = 960.0
CANVAS_CENTER_Y = 540.0


@dataclass(frozen=True, slots=True)
class MenuItemBox:
    """Bounding box for a menu item."""

    action: str
    display_text: str
    x: float
    y: float
    width: float
    height: float

    def contains(self, px: float, py: float) -> bool:
        """True if virtual coordinate is inside item bounds."""
        return self.x <= px <= self.x + self.width and self.y <= py <= self.y + self.height


class BaseMenu:
    """Base class for keyboard and mouse driven menu overlays."""

    def __init__(self, actions: tuple[tuple[str, str], ...]) -> None:
        self._actions = actions
        self.selected_index = 0
        self.is_active = False
        self._buttons: list[MenuItemBox] = []
        self._build_layout()

    def _build_layout(self) -> None:
        self._buttons.clear()
        count = len(self._actions)
        total_h = count * MENU_BTN_HEIGHT + (count - 1) * MENU_BTN_GAP
        start_y = CANVAS_CENTER_Y - (total_h / 2.0)
        btn_x = CANVAS_CENTER_X - (MENU_BTN_WIDTH / 2.0)

        for i, (action, text) in enumerate(self._actions):
            btn_y = start_y + (count - 1 - i) * (MENU_BTN_HEIGHT + MENU_BTN_GAP)
            self._buttons.append(
                MenuItemBox(
                    action=action,
                    display_text=text,
                    x=btn_x,
                    y=btn_y,
                    width=MENU_BTN_WIDTH,
                    height=MENU_BTN_HEIGHT,
                )
            )

    @property
    def buttons(self) -> tuple[MenuItemBox, ...]:
        """Menu buttons layout."""
        return tuple(self._buttons)

    def open(self) -> None:
        """Open and activate the menu."""
        self.is_active = True
        self.selected_index = 0

    def close(self) -> None:
        """Close the menu."""
        self.is_active = False

    def handle_mouse_move(self, vx: float, vy: float) -> None:
        """Update selected item on mouse hover."""
        if not self.is_active:
            return
        for i, btn in enumerate(self._buttons):
            if btn.contains(vx, vy):
                self.selected_index = i
                break

    def handle_click(self, vx: float, vy: float) -> str | None:
        """Commit action on mouse click."""
        if not self.is_active:
            return None
        for i, btn in enumerate(self._buttons):
            if btn.contains(vx, vy):
                self.selected_index = i
                return btn.action
        return None

    def handle_key_down(self, key_name: str) -> str | None:
        """Navigate with UP/DOWN and commit with ENTER/SPACE."""
        if not self.is_active or not self._actions:
            return None

        count = len(self._actions)
        k = key_name.lower()

        if k in ("up", "w"):
            self.selected_index = (self.selected_index - 1) % count
            return None

        if k in ("down", "s"):
            self.selected_index = (self.selected_index + 1) % count
            return None

        if k in ("enter", "return", "space"):
            return self._actions[self.selected_index][0]

        return None


class TitleMenu(BaseMenu):
    """Main menu displayed at game launch."""

    ACTIONS = (
        ("start", "Start Game"),
        ("load", "Load Game"),
        ("settings", "Settings"),
        ("quit", "Quit"),
    )

    def __init__(self) -> None:
        super().__init__(self.ACTIONS)


class PauseMenu(BaseMenu):
    """In-game pause menu overlay."""

    ACTIONS = (
        ("resume", "Resume"),
        ("save", "Save"),
        ("load", "Load"),
        ("settings", "Settings"),
        ("title", "Return to Title"),
        ("quit", "Quit"),
    )

    def __init__(self) -> None:
        super().__init__(self.ACTIONS)

    def handle_key_down(self, key_name: str) -> str | None:
        """Handle escape key as instant resume."""
        if not self.is_active:
            return None
        if key_name.lower() == "escape":
            return "resume"
        return super().handle_key_down(key_name)


class SettingsMenu:
    """Configurable settings menu for audio volumes and typewriter speed."""

    def __init__(self) -> None:
        self.is_active = False
        self.master_volume = 1.0
        self.bgm_volume = 1.0
        self.voice_volume = 1.0
        self.sfx_volume = 1.0
        self.ambience_volume = 1.0
        self.text_speed = 40.0

    def open(self) -> None:
        """Open settings overlay."""
        self.is_active = True

    def close(self) -> None:
        """Close settings overlay."""
        self.is_active = False

    def set_volume(self, channel: str, val: float) -> None:
        """Set a channel volume level clamped to 0.0-1.0."""
        clamped = max(0.0, min(1.0, val))
        match channel.lower():
            case "master":
                self.master_volume = clamped
            case "bgm":
                self.bgm_volume = clamped
            case "voice":
                self.voice_volume = clamped
            case "sfx":
                self.sfx_volume = clamped
            case "amb" | "ambience":
                self.ambience_volume = clamped

    def set_text_speed(self, speed: float) -> None:
        """Set typewriter reveal speed between 10 and 120 chars/sec."""
        self.text_speed = max(10.0, min(120.0, speed))

    def handle_key_down(self, key_name: str) -> str | None:
        """Close on Escape."""
        if self.is_active and key_name.lower() == "escape":
            self.close()
            return "back"
        return None
