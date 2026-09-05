"""Windowed presentation layer built on pyglet for interactive visual novel playback."""

from pathlib import Path
from typing import Literal

import pyglet
from pyglet import shapes
from pyglet.window import key

from dotter.core.nodes import ChoiceSetNode, DialogueNode, NarrationNode
from dotter.runtime.config import WindowConfig
from dotter.runtime.engine import Engine
from dotter.save.manager import SaveManager
from dotter.staging.compositor import StagingCompositor
from dotter.staging.viewport import Viewport
from dotter.ui.choices import ChoiceOverlay
from dotter.ui.dialogue import BUTTON_RECTS, DialogueBox


def _draw_box(
    x: float,
    y: float,
    w: float,
    h: float,
    bg: tuple[int, int, int],
    bdr: tuple[int, int, int],
    b: int = 2,
) -> None:
    shapes.BorderedRectangle(
        x=x, y=y, width=w, height=h, border=b, color=bg, border_color=bdr
    ).draw()


def _draw_text(
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
    pyglet.text.Label(
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


class DotterWindow(pyglet.window.Window):
    """Pyglet window scaling the 1920x1080 canvas with text, choices, and sprites."""

    def __init__(
        self,
        engine: Engine,
        save_dir: Path | None = None,
        width: int | None = None,
        height: int | None = None,
        config: WindowConfig | None = None,
    ) -> None:
        cfg = config or WindowConfig()
        win_w = width if width is not None else cfg.width
        win_h = height if height is not None else cfg.height
        super().__init__(width=win_w, height=win_h, resizable=cfg.resizable, caption=cfg.caption)
        self.engine = engine
        self.window_config = cfg
        self.canvas_viewport = Viewport(win_w, win_h)
        self.compositor = StagingCompositor(self.canvas_viewport)
        self.save_mgr = SaveManager(save_dir or Path("saves"))
        self.dialogue_box = DialogueBox()
        self.choice_overlay = ChoiceOverlay()
        self._step_engine()

    def _sync_beat(self) -> None:
        node = self.engine.current_node
        if isinstance(node, ChoiceSetNode):
            self.choice_overlay.set_choices(node.options)
        elif isinstance(node, DialogueNode):
            self.choice_overlay.clear()
            self.dialogue_box.set_dialogue(node.speaker, node.text, self.engine.state.variables)
        elif isinstance(node, NarrationNode):
            self.choice_overlay.clear()
            self.dialogue_box.set_dialogue(None, node.text, self.engine.state.variables)

    def _step_engine(self) -> None:
        self.engine.advance()
        self._sync_beat()

    def advance(self) -> None:
        """Advance narrative if not awaiting choice."""
        if self.choice_overlay.is_active:
            return
        if not self.dialogue_box.typewriter.is_complete:
            self.dialogue_box.typewriter.skip_to_end()
            return
        self._step_engine()

    def choose(self, index: int) -> None:
        """Commit choice selection and resume progression."""
        if not self.choice_overlay.is_active:
            return
        self.engine.choose(index)
        self.choice_overlay.clear()
        self._sync_beat()

    def on_resize(self, width: int, height: int) -> None:
        """Update viewport aspect-ratio scaling."""
        super().on_resize(width, height)
        self.canvas_viewport.update(width, height)

    def on_mouse_motion(self, x: int, y: int, dx: int, dy: int) -> None:
        """Track mouse hover over choices and quick buttons."""
        vx, vy = self.canvas_viewport.window_to_virtual(float(x), float(y))
        if self.choice_overlay.is_active:
            self.choice_overlay.handle_mouse_move(vx, vy)

    def on_mouse_press(self, x: int, y: int, button: int, modifiers: int) -> None:
        """Dispatch mouse clicks."""
        vx, vy = self.canvas_viewport.window_to_virtual(float(x), float(y))
        if self.choice_overlay.is_active:
            choice_idx = self.choice_overlay.handle_click(vx, vy)
            if choice_idx is not None:
                self.choose(choice_idx)
            return

        action = self.dialogue_box.handle_click(vx, vy)
        if action == "advance":
            self.advance()
        elif action == "save":
            self.save_mgr.quick_save(self.engine.state)
        elif action == "load":
            self.save_mgr.quick_load(self.engine.state)
            self._sync_beat()

    def on_key_press(self, symbol: int, modifiers: int) -> None:
        """Handle keyboard navigation and shortcuts."""
        if symbol == key.F5:
            self.save_mgr.quick_save(self.engine.state)
        elif symbol == key.F8:
            self.save_mgr.quick_load(self.engine.state)
            self._sync_beat()
        elif self.choice_overlay.is_active:
            self._handle_choice_keys(symbol)
        elif symbol in (key.SPACE, key.ENTER):
            self.advance()

    def _handle_choice_keys(self, symbol: int) -> None:
        if symbol == key.UP:
            self.choice_overlay.handle_key_down("up")
        elif symbol == key.DOWN:
            self.choice_overlay.handle_key_down("down")
        elif symbol in (key.ENTER, key.SPACE):
            self.choose(self.choice_overlay.selected_index)
        elif key._1 <= symbol <= key._9:
            num = symbol - key._1
            if num < len(self.choice_overlay.options):
                self.choose(num)

    def update(self, dt: float) -> None:
        """Per-frame update."""
        advance_req = self.dialogue_box.update(dt)
        if advance_req and not self.choice_overlay.is_active:
            self.advance()

    def on_draw(self) -> None:
        """Render viewport, background, sprites, textbox, and choices."""
        self.clear()
        vp = self.canvas_viewport

        bg_name = self.engine.state.staging.background
        bg_color = (
            self.window_config.bg_colors.get(bg_name, self.window_config.theme.clear_color)
            if bg_name
            else self.window_config.theme.clear_color
        )
        shapes.Rectangle(
            x=vp.offset_x,
            y=vp.offset_y,
            width=vp.render_width,
            height=vp.render_height,
            color=bg_color,
        ).draw()

        self._draw_characters()
        self._draw_dialogue_ui()
        if self.choice_overlay.is_active:
            self._draw_choice_overlay()

    def _draw_characters(self) -> None:
        vp = self.canvas_viewport
        theme = self.window_config.theme
        for plan in self.compositor.get_ordered_sprites(self.engine.state.staging):
            vx, vy = plan.position
            wx, wy = vp.virtual_to_window(float(vx) - 150.0, float(vy) + 100.0)
            w, h = 300.0 * vp.scale, 600.0 * vp.scale
            _draw_box(wx, wy, w, h, theme.sprite_box_color, theme.sprite_border_color, 3)
            _draw_text(
                plan.character.upper(),
                wx + w / 2.0,
                wy + h - 30.0 * vp.scale,
                max(10, int(18 * vp.scale)),
            )

    def _draw_dialogue_ui(self) -> None:
        vp = self.canvas_viewport
        theme = self.window_config.theme
        bx, by = vp.virtual_to_window(200.0, 50.0)
        bw, bh = 1520.0 * vp.scale, 250.0 * vp.scale
        _draw_box(bx, by, bw, bh, theme.dialogue_box_bg, theme.dialogue_box_border, 3)

        if self.dialogue_box.speaker:
            nx, ny = vp.virtual_to_window(200.0, 305.0)
            nw, nh = 300.0 * vp.scale, 50.0 * vp.scale
            _draw_box(nx, ny, nw, nh, theme.nameplate_bg, theme.nameplate_border, 2)
            _draw_text(
                self.dialogue_box.speaker,
                nx + nw / 2.0,
                ny + nh / 2.0,
                max(9, int(16 * vp.scale)),
                color=theme.nameplate_text_color,
                weight="bold",
            )

        _draw_text(
            self.dialogue_box.typewriter.visible_text,
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
            _draw_box(wx, wy, bw_btn, bh_btn, theme.quick_button_bg, theme.quick_button_border, 1)
            _draw_text(
                btn.name,
                wx + bw_btn / 2.0,
                wy + bh_btn / 2.0,
                max(8, int(11 * vp.scale)),
                color=theme.quick_button_text,
            )

    def _draw_choice_overlay(self) -> None:
        vp = self.canvas_viewport
        theme = self.window_config.theme
        for btn in self.choice_overlay.buttons:
            wx, wy = vp.virtual_to_window(btn.x, btn.y)
            bw, bh = btn.width * vp.scale, btn.height * vp.scale
            is_sel = btn.index == self.choice_overlay.selected_index
            bg_c = theme.choice_selected_bg if is_sel else theme.choice_normal_bg
            bdr_c = theme.choice_selected_border if is_sel else theme.choice_normal_border

            _draw_box(wx, wy, bw, bh, bg_c, bdr_c, 2)
            _draw_text(
                f"{btn.index + 1}. {btn.text}",
                wx + bw / 2.0,
                wy + bh / 2.0,
                max(10, int(18 * vp.scale)),
                weight="bold" if is_sel else "normal",
                color=theme.choice_selected_text if is_sel else theme.choice_normal_text,
            )


def launch_window(
    engine: Engine,
    save_dir: Path | None = None,
    config: WindowConfig | None = None,
) -> int:
    """Launch the interactive pyglet window and start application event loop."""
    win = DotterWindow(engine, save_dir, config=config)
    pyglet.clock.schedule_interval(win.update, 1.0 / 60.0)
    pyglet.app.run()
    return 0
