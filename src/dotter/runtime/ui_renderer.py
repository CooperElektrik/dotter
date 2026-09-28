"""Rendering helpers for dialogue UI, choice overlays, and primitive drawing."""

from typing import Literal

from pyglet import shapes
from pyglet.text import Label

from dotter.runtime.config import WindowConfig
from dotter.staging.viewport import Viewport
from dotter.ui.choices import ChoiceOverlay
from dotter.ui.dialogue import BUTTON_RECTS, DialogueBox


def draw_box(
    x: float,
    y: float,
    w: float,
    h: float,
    bg: tuple[int, int, int],
    bdr: tuple[int, int, int],
    b: int = 2,
) -> None:
    """Draw a bordered rectangle at the given window-space coordinates."""
    shapes.BorderedRectangle(
        x=x, y=y, width=w, height=h, border=b, color=bg, border_color=bdr
    ).draw()


def draw_text(
    text: str,
    x: float,
    y: float,
    size: int,
    color: tuple[int, int, int, int] = (255, 255, 255, 255),
    weight: str = "normal",
    ax: Literal["left", "center", "right"] = "center",
    ay: Literal["top", "bottom", "center", "baseline"] = "center",
    w: int | None = None,
    multi: bool = False,
) -> None:
    """Draw a text label at the given window-space coordinates."""
    Label(
        text=text,
        x=x,
        y=y,
        font_size=size,
        color=color,
        weight=weight,
        anchor_x=ax,
        anchor_y=ay,
        width=w,
        multiline=multi,
    ).draw()


def draw_dialogue_ui(
    dialogue_box: DialogueBox,
    vp: Viewport,
    cfg: WindowConfig,
) -> None:
    """Render the dialogue textbox, nameplate, text, and quick-action buttons."""
    theme = cfg.theme
    bx, by = vp.virtual_to_window(200.0, 50.0)
    bw, bh = 1520.0 * vp.scale, 250.0 * vp.scale
    draw_box(bx, by, bw, bh, theme.dialogue_box_bg, theme.dialogue_box_border, 3)

    if dialogue_box.speaker:
        nx, ny = vp.virtual_to_window(200.0, 305.0)
        nw, nh = 300.0 * vp.scale, 50.0 * vp.scale
        draw_box(nx, ny, nw, nh, theme.nameplate_bg, theme.nameplate_border, 2)
        draw_text(
            dialogue_box.speaker,
            nx + nw / 2.0,
            ny + nh / 2.0,
            max(9, int(16 * vp.scale)),
            color=theme.nameplate_text_color,
            weight="bold",
        )

    draw_text(
        dialogue_box.typewriter.visible_text,
        bx + 35.0 * vp.scale,
        by + bh - 40.0 * vp.scale,
        max(10, int(20 * vp.scale)),
        color=theme.dialogue_text_color,
        ax="left",
        ay="top",
        w=int(bw - 70.0 * vp.scale),
        multi=True,
    )

    for btn in BUTTON_RECTS:
        wx, wy = vp.virtual_to_window(btn.x, btn.y)
        bw_btn, bh_btn = btn.width * vp.scale, btn.height * vp.scale
        draw_box(
            wx,
            wy,
            bw_btn,
            bh_btn,
            theme.quick_button_bg,
            theme.quick_button_border,
            1,
        )
        draw_text(
            btn.name,
            wx + bw_btn / 2.0,
            wy + bh_btn / 2.0,
            max(8, int(11 * vp.scale)),
            color=theme.quick_button_text,
        )


def draw_choice_overlay(
    choice_overlay: ChoiceOverlay,
    vp: Viewport,
    cfg: WindowConfig,
) -> None:
    """Render the choice overlay with highlighted selected item."""
    theme = cfg.theme
    for btn in choice_overlay.buttons:
        wx, wy = vp.virtual_to_window(btn.x, btn.y)
        bw, bh = btn.width * vp.scale, btn.height * vp.scale
        is_sel = btn.index == choice_overlay.selected_index
        bg_c = theme.choice_selected_bg if is_sel else theme.choice_normal_bg
        bdr_c = theme.choice_selected_border if is_sel else theme.choice_normal_border

        draw_box(wx, wy, bw, bh, bg_c, bdr_c, 2)
        draw_text(
            f"{btn.index + 1}. {btn.text}",
            wx + bw / 2.0,
            wy + bh / 2.0,
            max(10, int(18 * vp.scale)),
            weight="bold" if is_sel else "normal",
            color=theme.choice_selected_text if is_sel else theme.choice_normal_text,
        )
