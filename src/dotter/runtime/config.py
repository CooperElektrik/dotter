"""Runtime configuration and theming containers for windowed presentation."""

from dataclasses import dataclass, field


@dataclass(slots=True)
class ThemeConfig:
    """Color and styling properties for runtime UI components."""

    # Clear and staging colors
    clear_color: tuple[int, int, int] = (20, 20, 25)
    sprite_box_color: tuple[int, int, int] = (45, 55, 70)
    sprite_border_color: tuple[int, int, int] = (120, 150, 190)

    # Dialogue box colors
    dialogue_box_bg: tuple[int, int, int] = (15, 20, 28)
    dialogue_box_border: tuple[int, int, int] = (80, 100, 130)
    dialogue_text_color: tuple[int, int, int, int] = (240, 245, 255, 255)

    # Nameplate colors
    nameplate_bg: tuple[int, int, int] = (25, 35, 50)
    nameplate_border: tuple[int, int, int] = (140, 170, 210)
    nameplate_text_color: tuple[int, int, int, int] = (255, 255, 255, 255)

    # Choice overlay colors
    choice_normal_bg: tuple[int, int, int] = (25, 35, 50)
    choice_normal_border: tuple[int, int, int] = (90, 120, 160)
    choice_normal_text: tuple[int, int, int, int] = (210, 225, 240, 255)
    choice_selected_bg: tuple[int, int, int] = (60, 80, 115)
    choice_selected_border: tuple[int, int, int] = (200, 230, 255)
    choice_selected_text: tuple[int, int, int, int] = (255, 255, 255, 255)

    # Quick button colors
    quick_button_bg: tuple[int, int, int] = (30, 40, 55)
    quick_button_border: tuple[int, int, int] = (90, 110, 140)
    quick_button_text: tuple[int, int, int, int] = (200, 215, 235, 255)


@dataclass(slots=True)
class WindowConfig:
    """Configuration parameters for the presentation window and stage rendering."""

    width: int = 1280
    height: int = 720
    caption: str = "Dotter Visual Novel Engine"
    resizable: bool = True
    bg_colors: dict[str, tuple[int, int, int]] = field(default_factory=dict)
    theme: ThemeConfig = field(default_factory=ThemeConfig)
