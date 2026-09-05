"""Staging and narrative commands dispatched during scene execution."""

from dataclasses import dataclass

from dotter.core.types import SpritePosition, TransitionType


@dataclass(frozen=True, slots=True)
class StagingCommand:
    """Base class for all engine staging and mutation commands."""


@dataclass(frozen=True, slots=True)
class ShowCommand(StagingCommand):
    """Command to display or update a layered character sprite."""

    character: str
    face: str | None = None
    outfit: str | None = None
    at: SpritePosition | tuple[int, int] = SpritePosition.CENTER
    z_order: int = 0


@dataclass(frozen=True, slots=True)
class HideCommand(StagingCommand):
    """Command to hide a character sprite."""

    character: str


@dataclass(frozen=True, slots=True)
class BackgroundCommand(StagingCommand):
    """Command to display a background with an optional transition."""

    background: str
    transition: TransitionType = TransitionType.CUT
    duration: float = 0.0


@dataclass(frozen=True, slots=True)
class MusicCommand(StagingCommand):
    """Command to play, loop, or crossfade background music."""

    track: str | None
    loop: bool = True
    fade_in: float = 0.0
    fade_out: float = 0.0


@dataclass(frozen=True, slots=True)
class SfxCommand(StagingCommand):
    """Command to play a one-shot sound effect."""

    clip: str
    volume: float = 1.0


@dataclass(frozen=True, slots=True)
class AmbienceCommand(StagingCommand):
    """Command to play or stop looping ambient audio."""

    track: str | None
    loop: bool = True
    fade_in: float = 0.0


@dataclass(frozen=True, slots=True)
class VoiceCommand(StagingCommand):
    """Command to play or cancel a spoken dialogue line."""

    clip: str | None


@dataclass(frozen=True, slots=True)
class SetVarCommand(StagingCommand):
    """Command to mutate a narrative variable in game state."""

    name: str
    value: object


@dataclass(frozen=True, slots=True)
class GotoCommand(StagingCommand):
    """Command to jump execution to a specific label."""

    label: str
