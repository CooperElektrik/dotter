"""Command-recording context provided to companion Python scene hooks."""

from collections.abc import Callable
from typing import Any

from dotter.core.commands import (
    AmbienceCommand,
    BackgroundCommand,
    GotoCommand,
    HideCommand,
    MusicCommand,
    SetVarCommand,
    SfxCommand,
    ShowCommand,
    StagingCommand,
    VoiceCommand,
)
from dotter.core.state import GameState
from dotter.core.types import SpritePosition, TransitionType


class WhenCondition:
    """Fluent builder for conditional commands."""

    def __init__(self, context: "HookContext", is_active: bool) -> None:
        self._context = context
        self._is_active = is_active

    def goto(self, label: str) -> None:
        """Jump to label if condition evaluated to true."""
        if self._is_active:
            self._context.goto(label)


class HookContext:
    """Records staging and control flow commands emitted by user-defined scene hooks."""

    def __init__(self, state: GameState) -> None:
        self._state = state
        self._commands: list[StagingCommand] = []

    @property
    def commands(self) -> tuple[StagingCommand, ...]:
        """Return the immutable sequence of recorded commands."""
        return tuple(self._commands)

    def clear_commands(self) -> None:
        """Clear recorded commands buffer."""
        self._commands.clear()

    def show(
        self,
        character: str,
        *,
        face: str | None = None,
        outfit: str | None = None,
        at: SpritePosition | tuple[int, int] = SpritePosition.CENTER,
        z_order: int = 0,
    ) -> None:
        """Record a command to display or modify a character sprite."""
        self._commands.append(
            ShowCommand(
                character=character,
                face=face,
                outfit=outfit,
                at=at,
                z_order=z_order,
            )
        )

    def hide(self, character: str) -> None:
        """Record a command to hide a character sprite."""
        self._commands.append(HideCommand(character=character))

    def background(
        self,
        background: str,
        *,
        transition: TransitionType = TransitionType.CUT,
        duration: float = 0.0,
    ) -> None:
        """Record a command to change background art with a transition."""
        self._commands.append(
            BackgroundCommand(
                background=background,
                transition=transition,
                duration=duration,
            )
        )

    def music(
        self,
        track: str | None,
        *,
        loop: bool = True,
        fade_in: float = 0.0,
        fade_out: float = 0.0,
    ) -> None:
        """Record a command to change background music."""
        self._commands.append(
            MusicCommand(
                track=track,
                loop=loop,
                fade_in=fade_in,
                fade_out=fade_out,
            )
        )

    def sfx(self, clip: str, *, volume: float = 1.0) -> None:
        """Record a command to trigger a one-shot sound effect."""
        self._commands.append(SfxCommand(clip=clip, volume=volume))

    def ambience(
        self,
        track: str | None,
        *,
        loop: bool = True,
        fade_in: float = 0.0,
    ) -> None:
        """Record a command to change ambient audio."""
        self._commands.append(AmbienceCommand(track=track, loop=loop, fade_in=fade_in))

    def voice(self, clip: str | None) -> None:
        """Record a command to play or stop voice audio."""
        self._commands.append(VoiceCommand(clip=clip))

    def set(self, key: str, value: Any) -> None:
        """Update game state variable and record command."""
        self._state.set_variable(key, value)
        self._commands.append(SetVarCommand(name=key, value=value))

    def get(self, key: str, default: Any = None) -> Any:
        """Read a variable from game state."""
        return self._state.get_variable(key, default)

    def goto(self, label: str) -> None:
        """Record an explicit jump to a label."""
        self._commands.append(GotoCommand(label=label))

    def when(self, predicate: Callable[[GameState], bool] | bool) -> WhenCondition:
        """Conditionally perform an action based on boolean or predicate."""
        active = predicate(self._state) if callable(predicate) else bool(predicate)
        return WhenCondition(self, active)
