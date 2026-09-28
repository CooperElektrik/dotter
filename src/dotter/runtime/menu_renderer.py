"""Rendering helpers for menu overlays, settings sliders, transitions, and history."""

from typing import Protocol

import pyglet
from pyglet import shapes
from pyglet.text import Label

from dotter.audio.manager import AudioManager
from dotter.core.types import AudioChannel, TransitionType
from dotter.runtime.config import ThemeConfig, WindowConfig
from dotter.runtime.engine import Engine
from dotter.save.manager import SaveManager
from dotter.staging.compositor import ActiveTransition, StagingCompositor
from dotter.staging.viewport import Viewport
from dotter.ui.menus import BaseMenu, PauseMenu, SettingsMenu, TitleMenu


class MenuWindow(Protocol):
    """Structural type for DotterWindow attributes used by menu rendering."""

    compositor: StagingCompositor
    title_menu: TitleMenu
    pause_menu: PauseMenu
    settings_menu: SettingsMenu
    audio: AudioManager
    save_mgr: SaveManager
    engine: Engine

    def _sync_beat(self) -> None: ...


_DIM_COLOR: tuple[int, int, int] = (0, 0, 0)
_DIM_OPACITY = 155


def draw_menu(menu: BaseMenu, vp: Viewport, cfg: WindowConfig) -> None:
    """Render a dimmed overlay with vertically-stacked menu buttons."""
    theme = cfg.theme
    overlay = shapes.Rectangle(
        x=vp.offset_x,
        y=vp.offset_y,
        width=vp.render_width,
        height=vp.render_height,
        color=_DIM_COLOR,
    )
    overlay.opacity = _DIM_OPACITY
    overlay.draw()

    for i, btn in enumerate(menu.buttons):
        wx, wy = vp.virtual_to_window(btn.x, btn.y)
        bw, bh = btn.width * vp.scale, btn.height * vp.scale
        is_sel = i == menu.selected_index
        bg_c = theme.choice_selected_bg if is_sel else theme.choice_normal_bg
        bdr_c = theme.choice_selected_border if is_sel else theme.choice_normal_border
        shapes.BorderedRectangle(
            x=wx,
            y=wy,
            width=bw,
            height=bh,
            border=2,
            color=bg_c,
            border_color=bdr_c,
        ).draw()
        Label(
            text=btn.display_text,
            x=wx + bw / 2.0,
            y=wy + bh / 2.0,
            font_size=max(12, int(20 * vp.scale)),
            color=theme.choice_selected_text if is_sel else theme.choice_normal_text,
            anchor_x="center",
            anchor_y="center",
        ).draw()


def _draw_slider(
    label: str,
    value: float,
    y_virtual: float,
    vp: Viewport,
    theme: ThemeConfig,
) -> None:
    """Draw a labeled horizontal slider bar with a proportional knob."""
    lx, ly = vp.virtual_to_window(380.0, y_virtual)
    Label(
        text=label,
        x=lx,
        y=ly,
        font_size=max(10, int(16 * vp.scale)),
        color=theme.quick_button_text,
        anchor_x="left",
        anchor_y="center",
    ).draw()
    bx, by = vp.virtual_to_window(700.0, y_virtual - 5.0)
    bw, bh = 300.0 * vp.scale, 10.0 * vp.scale
    shapes.Rectangle(x=bx, y=by, width=bw, height=bh, color=(80, 100, 130)).draw()
    knob_x = bx + value * bw - 5 * vp.scale
    shapes.Rectangle(
        x=knob_x,
        y=by - 5 * vp.scale,
        width=10 * vp.scale,
        height=20 * vp.scale,
        color=(200, 230, 255),
    ).draw()


def draw_settings(settings: SettingsMenu, vp: Viewport, cfg: WindowConfig) -> None:
    """Render settings menu with volume sliders and text-speed control."""
    theme = cfg.theme
    overlay = shapes.Rectangle(
        x=vp.offset_x,
        y=vp.offset_y,
        width=vp.render_width,
        height=vp.render_height,
        color=_DIM_COLOR,
    )
    overlay.opacity = _DIM_OPACITY
    overlay.draw()

    cx, ty = vp.virtual_to_window(960.0, 700.0)
    Label(
        text="Settings",
        x=cx,
        y=ty,
        font_size=max(16, int(24 * vp.scale)),
        color=(255, 255, 255, 255),
        anchor_x="center",
        anchor_y="center",
        weight="bold",
    ).draw()

    vol_items: tuple[tuple[str, float], ...] = (
        (f"Master: {settings.master_volume:.0%}", settings.master_volume),
        (f"BGM: {settings.bgm_volume:.0%}", settings.bgm_volume),
        (f"Voice: {settings.voice_volume:.0%}", settings.voice_volume),
        (f"SFX: {settings.sfx_volume:.0%}", settings.sfx_volume),
        (f"Ambience: {settings.ambience_volume:.0%}", settings.ambience_volume),
    )
    for i, (label_text, vol) in enumerate(vol_items):
        _draw_slider(label_text, vol, 580.0 - i * 50.0, vp, theme)

    y_s = 580.0 - len(vol_items) * 50.0 - 20.0
    speed_norm = (settings.text_speed - 10.0) / 110.0
    _draw_slider(
        f"Text Speed: {settings.text_speed:.0f} cps",
        speed_norm,
        y_s,
        vp,
        theme,
    )

    fx, fy = vp.virtual_to_window(960.0, 80.0)
    Label(
        text="Press ESC to go back",
        x=fx,
        y=fy,
        font_size=max(8, int(11 * vp.scale)),
        color=(200, 225, 240, 200),
        anchor_x="center",
        anchor_y="center",
    ).draw()


def draw_transition(transition: ActiveTransition, vp: Viewport, cfg: WindowConfig) -> None:
    """Render a fullscreen transition overlay based on the active transition."""
    alpha = transition.overlay_alpha
    if alpha <= 0.0:
        return

    if transition.transition_type == TransitionType.FADE_BLACK:
        color = (0, 0, 0)
    elif transition.transition_type == TransitionType.FADE_WHITE:
        color = (255, 255, 255)
    elif transition.transition_type == TransitionType.DISSOLVE:
        bg = transition.effective_background
        color = cfg.bg_colors.get(bg, cfg.theme.clear_color) if bg else cfg.theme.clear_color
    else:
        return

    rect = shapes.Rectangle(
        x=vp.offset_x,
        y=vp.offset_y,
        width=vp.render_width,
        height=vp.render_height,
        color=color,
    )
    rect.opacity = int(alpha * 255)
    rect.draw()


def draw_history(
    history: list[tuple[str | None, str]],
    vp: Viewport,
    cfg: WindowConfig,
) -> None:
    """Render a dimmed overlay with recent dialogue history entries."""
    theme = cfg.theme
    overlay = shapes.Rectangle(
        x=vp.offset_x,
        y=vp.offset_y,
        width=vp.render_width,
        height=vp.render_height,
        color=_DIM_COLOR,
    )
    overlay.opacity = _DIM_OPACITY
    overlay.draw()

    entries = history[-20:]
    if not entries:
        cx, cy = vp.virtual_to_window(960.0, 540.0)
        Label(
            text="No dialogue history",
            x=cx,
            y=cy,
            font_size=max(12, int(16 * vp.scale)),
            color=(200, 225, 240, 255),
            anchor_x="center",
            anchor_y="center",
        ).draw()
        return

    y = 950.0
    for speaker, text in entries:
        label_text = f"{speaker}: {text}" if speaker else text
        vx, vy = vp.virtual_to_window(220.0, y)
        Label(
            text=label_text,
            x=vx,
            y=vy,
            font_size=max(9, int(14 * vp.scale)),
            color=theme.dialogue_text_color,
            anchor_x="left",
            anchor_y="center",
            width=int(1520 * vp.scale),
            multiline=True,
        ).draw()
        y -= 30.0
        if y < 80:
            break

    fx, fy = vp.virtual_to_window(960.0, 50.0)
    Label(
        text="Press Log again to close",
        x=fx,
        y=fy,
        font_size=max(8, int(11 * vp.scale)),
        color=(200, 225, 240, 200),
        anchor_x="center",
        anchor_y="center",
    ).draw()


def draw_overlays(win: MenuWindow, vp: Viewport, cfg: WindowConfig) -> bool:
    """Draw transition and menu overlays. Return True if a menu overlays the scene."""
    if win.compositor.active_transition is not None:
        draw_transition(win.compositor.active_transition, vp, cfg)
    if win.title_menu.is_active or win.pause_menu.is_active:
        menu = win.title_menu if win.title_menu.is_active else win.pause_menu
        draw_menu(menu, vp, cfg)
        return True
    if win.settings_menu.is_active:
        draw_settings(win.settings_menu, vp, cfg)
        return True
    return False


def open_settings(settings_menu: SettingsMenu, audio: AudioManager) -> None:
    """Open the settings menu and sync all volume sliders to AudioManager."""
    settings_menu.open()
    audio.master_volume = settings_menu.master_volume
    audio.set_channel_volume(AudioChannel.BGM, settings_menu.bgm_volume)
    audio.set_channel_volume(AudioChannel.VOICE, settings_menu.voice_volume)
    audio.set_channel_volume(AudioChannel.SFX, settings_menu.sfx_volume)
    audio.set_channel_volume(AudioChannel.AMB, settings_menu.ambience_volume)


def dispatch_menu_action(action: str | None, win: MenuWindow) -> None:
    """Handle an action returned by a BaseMenu's handle_key_down or handle_click."""
    if action is None:
        return
    match action:
        case "start" | "resume":
            win.title_menu.close()
            win.pause_menu.close()
        case "settings":
            win.title_menu.close()
            win.pause_menu.close()
            open_settings(win.settings_menu, win.audio)
        case "save":
            win.save_mgr.quick_save(win.engine.state)
        case "load":
            win.save_mgr.quick_load(win.engine.state)
            win._sync_beat()
        case "title":
            win.pause_menu.close()
            win.title_menu.open()
        case "quit":
            pyglet.app.exit()
