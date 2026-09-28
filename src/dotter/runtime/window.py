"""Windowed presentation layer built on pyglet for interactive visual novel playback."""

from pathlib import Path

import pyglet
from pyglet import shapes
from pyglet.window import key

from dotter.audio.manager import AudioManager
from dotter.core.commands import (
    AmbienceCommand,
    BackgroundCommand,
    MusicCommand,
    SfxCommand,
    VoiceCommand,
)
from dotter.core.nodes import ChoiceSetNode, DialogueNode, NarrationNode
from dotter.runtime import menu_renderer, ui_renderer
from dotter.runtime.config import WindowConfig
from dotter.runtime.engine import Engine
from dotter.runtime.sprite_renderer import SpriteRenderer
from dotter.save.manager import SaveManager
from dotter.staging.compositor import StagingCompositor
from dotter.staging.viewport import Viewport
from dotter.ui.choices import ChoiceOverlay
from dotter.ui.dialogue import DialogueBox
from dotter.ui.menus import PauseMenu, SettingsMenu, TitleMenu


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
        self.sprite_renderer = SpriteRenderer(self.canvas_viewport, self.compositor)
        self.audio = AudioManager()
        self.save_mgr = SaveManager(save_dir or Path("saves"))
        self.dialogue_box = DialogueBox()
        self.choice_overlay = ChoiceOverlay()
        self._last_bg: str | None = None
        self.title_menu = TitleMenu()
        self.pause_menu = PauseMenu()
        self.settings_menu = SettingsMenu()
        self._dialogue_history: list[tuple[str | None, str]] = []
        self._log_active = False
        self._step_engine()

    def _sync_beat(self) -> None:
        node = self.engine.current_node
        if isinstance(node, ChoiceSetNode):
            self.choice_overlay.set_choices(node.options)
        elif isinstance(node, DialogueNode):
            self.choice_overlay.clear()
            self.dialogue_box.set_dialogue(
                node.speaker, node.text, self.engine.state.variables, node.emotion
            )
            if node.voice:
                self.audio.play_voice(node.voice)
            self._dialogue_history.append((node.speaker, node.text))
        elif isinstance(node, NarrationNode):
            self.choice_overlay.clear()
            self.dialogue_box.set_dialogue(None, node.text, self.engine.state.variables)
            self._dialogue_history.append((None, node.text))

    def _process_staged_commands(self) -> None:
        """Drain dispatched staging commands and route audio commands to AudioManager."""
        for cmd in self.engine.drain_dispatched_commands():
            match cmd:
                case MusicCommand(track=t, fade_in=fi):
                    self.audio.play_bgm(t, crossfade=fi)
                case AmbienceCommand(track=t, loop=loop):
                    self.audio.play_ambience(t, loop=loop)
                case VoiceCommand(clip=v):
                    self.audio.play_voice(v)
                case SfxCommand(clip=c, volume=v):
                    self.audio.play_sfx(c, volume=v)
                case BackgroundCommand(background=bg, transition=t, duration=d):
                    self.compositor.start_transition(t, d, from_bg=self._last_bg, to_bg=bg)
                    self._last_bg = bg

    def _step_engine(self) -> None:
        self.engine.advance()
        self._process_staged_commands()
        self.audio.advance_beat()
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
        """Track mouse hover over choices, menus, and quick buttons."""
        vx, vy = self.canvas_viewport.window_to_virtual(float(x), float(y))
        if self.choice_overlay.is_active:
            self.choice_overlay.handle_mouse_move(vx, vy)
        elif self.title_menu.is_active:
            self.title_menu.handle_mouse_move(vx, vy)
        elif self.pause_menu.is_active:
            self.pause_menu.handle_mouse_move(vx, vy)

    def on_mouse_press(self, x: int, y: int, button: int, modifiers: int) -> None:
        """Dispatch mouse clicks to choices, menus, or quick actions."""
        vx, vy = self.canvas_viewport.window_to_virtual(float(x), float(y))
        if self.choice_overlay.is_active:
            choice_idx = self.choice_overlay.handle_click(vx, vy)
            if choice_idx is not None:
                self.choose(choice_idx)
            return
        if self.title_menu.is_active or self.pause_menu.is_active:
            menu = self.title_menu if self.title_menu.is_active else self.pause_menu
            menu_renderer.dispatch_menu_action(menu.handle_click(vx, vy), self)
            return
        if self.settings_menu.is_active:
            return

        action = self.dialogue_box.handle_click(vx, vy)
        if action == "advance":
            self.advance()
        elif action == "save":
            self.save_mgr.quick_save(self.engine.state)
        elif action == "load":
            self.save_mgr.quick_load(self.engine.state)
            self._sync_beat()
        elif action == "settings":
            menu_renderer.open_settings(self.settings_menu, self.audio)
        elif action == "log":
            self._log_active = not self._log_active

    def on_key_press(self, symbol: int, modifiers: int) -> None:
        """Handle keyboard navigation and shortcuts."""
        name = key.symbol_string(symbol).lower() or ""
        if self.title_menu.is_active or self.pause_menu.is_active:
            menu = self.title_menu if self.title_menu.is_active else self.pause_menu
            menu_renderer.dispatch_menu_action(menu.handle_key_down(name), self)
            return
        if self.settings_menu.is_active:
            self.settings_menu.handle_key_down(name)
            return
        if symbol == key.F5:
            self.save_mgr.quick_save(self.engine.state)
        elif symbol == key.F8:
            self.save_mgr.quick_load(self.engine.state)
            self._sync_beat()
        elif self.choice_overlay.is_active:
            self._handle_choice_keys(symbol)
        elif symbol == key.ESCAPE:
            self.pause_menu.open()
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
        self.audio.update(dt)
        self.compositor.update(dt)

    def on_draw(self) -> None:
        """Render viewport, background, sprites, transitions, menus, UI, history."""
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

        self.sprite_renderer.draw(self.engine.state.staging)

        if menu_renderer.draw_overlays(self, vp, self.window_config):
            return

        ui_renderer.draw_dialogue_ui(self.dialogue_box, vp, self.window_config)
        if self.choice_overlay.is_active:
            ui_renderer.draw_choice_overlay(self.choice_overlay, vp, self.window_config)
        if self._log_active:
            menu_renderer.draw_history(self._dialogue_history, vp, self.window_config)


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
