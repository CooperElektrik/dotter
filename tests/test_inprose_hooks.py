"""Unit tests for HookContext and HookRegistry."""

from pathlib import Path

from dotter.core.commands import (
    AmbienceCommand,
    BackgroundCommand,
    GotoCommand,
    HideCommand,
    MusicCommand,
    SetVarCommand,
    SfxCommand,
    ShowCommand,
    VoiceCommand,
)
from dotter.core.state import GameState
from dotter.core.types import SpritePosition, TransitionType
from dotter.scenes.context import HookContext
from dotter.scenes.hooks import HookRegistry


def test_hook_context_command_recording() -> None:
    """Verify that HookContext records all staging and control flow commands."""
    state = GameState()
    ctx = HookContext(state)

    ctx.show("alice", face="smile", outfit="casual", at=SpritePosition.LEFT, z_order=1)
    ctx.hide("bob")
    ctx.background("classroom", transition=TransitionType.DISSOLVE, duration=1.0)
    ctx.music("bgm.ogg", loop=True, fade_in=0.5, fade_out=0.5)
    ctx.sfx("door.ogg", volume=0.9)
    ctx.ambience("wind.ogg", loop=True, fade_in=1.0)
    ctx.voice("line_01.ogg")
    ctx.set("discovered_ruins", True)
    ctx.goto("target_label")

    assert ctx.get("discovered_ruins") is True
    assert state.get_variable("discovered_ruins") is True

    cmds = ctx.commands
    assert len(cmds) == 9

    assert isinstance(cmds[0], ShowCommand)
    assert cmds[0].character == "alice"
    assert cmds[0].face == "smile"

    assert isinstance(cmds[1], HideCommand)
    assert isinstance(cmds[2], BackgroundCommand)
    assert isinstance(cmds[3], MusicCommand)
    assert isinstance(cmds[4], SfxCommand)
    assert isinstance(cmds[5], AmbienceCommand)
    assert isinstance(cmds[6], VoiceCommand)
    assert isinstance(cmds[7], SetVarCommand)
    assert isinstance(cmds[8], GotoCommand)


def test_hook_context_conditional_when() -> None:
    """Verify fluent ctx.when().goto() branching."""
    state = GameState()
    state.set_variable("knows_ancient_language", False)

    ctx = HookContext(state)
    ctx.when(lambda s: s.get_variable("knows_ancient_language") is True).goto("secret_room")
    assert len(ctx.commands) == 0

    state.set_variable("knows_ancient_language", True)
    ctx.when(lambda s: s.get_variable("knows_ancient_language") is True).goto("secret_room")
    assert len(ctx.commands) == 1
    assert isinstance(ctx.commands[0], GotoCommand)
    assert ctx.commands[0].label == "secret_room"


def test_hook_registry_dispatch() -> None:
    """Verify HookRegistry registers and triggers named and lifecycle hooks."""
    registry = HookRegistry()
    state = GameState()
    ctx = HookContext(state)

    entry_called = []
    exit_called = []
    named_called = []

    registry.register_on_entry("clearing", lambda c: entry_called.append("entered"))
    registry.register_on_exit("clearing", lambda c: exit_called.append("exited"))
    registry.register_hook("inspect_pillars", lambda c: named_called.append("inspected"))

    registry.execute_on_entry("clearing", ctx)
    assert entry_called == ["entered"]

    registry.execute_on_exit("clearing", ctx)
    assert exit_called == ["exited"]

    executed = registry.execute_hook("inspect_pillars", ctx)
    assert executed is True
    assert named_called == ["inspected"]

    assert registry.execute_hook("missing_hook", ctx) is False


def test_hook_registry_load_companion(tmp_path: Path) -> None:
    """Verify loading companion Python module triggers registrations."""
    registry = HookRegistry()
    companion_file = tmp_path / "companion_scene.py"
    companion_file.write_text(
        "from dotter.scenes.hooks import hook\n"
        "@hook('companion_test')\n"
        "def on_test(ctx):\n"
        "    ctx.set('companion_ran', True)\n"
    )

    loaded = registry.load_companion_module(companion_file)
    assert loaded is True
