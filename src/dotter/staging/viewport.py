"""Virtual 1920x1080 resolution letterboxing and coordinate transformation."""

from dataclasses import dataclass

DESIGN_WIDTH = 1920
DESIGN_HEIGHT = 1080
DESIGN_ASPECT = DESIGN_WIDTH / DESIGN_HEIGHT


@dataclass(slots=True)
class Viewport:
    """Calculates uniform scaling and letterbox/pillarbox bars for arbitrary window sizes."""

    window_width: int = DESIGN_WIDTH
    window_height: int = DESIGN_HEIGHT
    scale: float = 1.0
    offset_x: float = 0.0
    offset_y: float = 0.0
    render_width: float = float(DESIGN_WIDTH)
    render_height: float = float(DESIGN_HEIGHT)

    def __post_init__(self) -> None:
        self.update(self.window_width, self.window_height)

    def update(self, window_width: int, window_height: int) -> None:
        """Recalculate letterbox parameters for new window dimensions."""
        self.window_width = max(1, window_width)
        self.window_height = max(1, window_height)

        window_aspect = self.window_width / self.window_height

        if window_aspect > DESIGN_ASPECT:
            # Pillarbox (black bars on left and right)
            self.scale = self.window_height / DESIGN_HEIGHT
            self.render_width = DESIGN_WIDTH * self.scale
            self.render_height = float(self.window_height)
            self.offset_x = (self.window_width - self.render_width) / 2.0
            self.offset_y = 0.0
        else:
            # Letterbox (black bars on top and bottom)
            self.scale = self.window_width / DESIGN_WIDTH
            self.render_width = float(self.window_width)
            self.render_height = DESIGN_HEIGHT * self.scale
            self.offset_x = 0.0
            self.offset_y = (self.window_height - self.render_height) / 2.0

    def virtual_to_window(self, vx: float, vy: float) -> tuple[float, float]:
        """Convert design coordinates (1920x1080) to physical window pixels."""
        wx = self.offset_x + vx * self.scale
        wy = self.offset_y + vy * self.scale
        return wx, wy

    def window_to_virtual(self, wx: float, wy: float) -> tuple[float, float]:
        """Convert physical window pixels to virtual design coordinates."""
        vx = (wx - self.offset_x) / self.scale
        vy = (wy - self.offset_y) / self.scale
        return vx, vy

    def is_in_bounds(self, wx: float, wy: float) -> bool:
        """Check if a window pixel lies within the active virtual canvas."""
        return (
            self.offset_x <= wx <= self.offset_x + self.render_width
            and self.offset_y <= wy <= self.offset_y + self.render_height
        )
