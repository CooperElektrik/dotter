"""State containers for runtime persistence and in-place restoration."""

from dataclasses import dataclass, field
from typing import Any

from dotter.core.types import NodeId, SpritePosition


@dataclass(slots=True)
class CharacterSpriteState:
    """State of an active character sprite on the staging layer."""

    character: str
    face: str | None = None
    outfit: str | None = None
    position: SpritePosition | tuple[int, int] = SpritePosition.CENTER
    z_order: int = 0


@dataclass(slots=True)
class StagingState:
    """Active visual and audio staging state."""

    background: str | None = None
    sprites: dict[str, CharacterSpriteState] = field(default_factory=dict)
    current_bgm: str | None = None
    current_ambience: str | None = None
    current_voice: str | None = None

    def restore_from(self, data: dict[str, Any]) -> None:
        """Update staging state in-place, preserving internal container identities."""
        self.background = data.get("background")
        self.current_bgm = data.get("current_bgm")
        self.current_ambience = data.get("current_ambience")
        self.current_voice = data.get("current_voice")

        self.sprites.clear()
        raw_sprites = data.get("sprites", {})
        if isinstance(raw_sprites, dict):
            for name, sdata in raw_sprites.items():
                if isinstance(sdata, dict):
                    pos_val = sdata.get("position", SpritePosition.CENTER)
                    pos = SpritePosition(pos_val) if isinstance(pos_val, str) else tuple(pos_val)
                    self.sprites[str(name)] = CharacterSpriteState(
                        character=str(sdata.get("character", name)),
                        face=sdata.get("face"),
                        outfit=sdata.get("outfit"),
                        position=pos,
                        z_order=int(sdata.get("z_order", 0)),
                    )


@dataclass(slots=True)
class GameState:
    """Canonical game state container updated strictly in-place."""

    cursor_position: NodeId | None = None
    call_stack: list[NodeId] = field(default_factory=list)
    variables: dict[str, Any] = field(default_factory=dict)
    staging: StagingState = field(default_factory=StagingState)
    chapter_title: str = ""
    playtime_seconds: float = 0.0

    def set_variable(self, name: str, value: Any) -> None:
        """Mutate a narrative variable."""
        self.variables[name] = value

    def get_variable(self, name: str, default: Any = None) -> Any:
        """Access a narrative variable."""
        return self.variables.get(name, default)

    def restore_from(self, data: dict[str, Any]) -> None:
        """Restore game state in-place to preserve object identities and listener bindings."""
        self.cursor_position = data.get("cursor_position")
        self.chapter_title = str(data.get("chapter_title", ""))
        self.playtime_seconds = float(data.get("playtime_seconds", 0.0))

        self.variables.clear()
        raw_vars = data.get("variables", {})
        if isinstance(raw_vars, dict):
            self.variables.update(raw_vars)

        self.call_stack.clear()
        raw_stack = data.get("call_stack", [])
        if isinstance(raw_stack, list):
            self.call_stack.extend(str(item) for item in raw_stack)

        raw_staging = data.get("staging", {})
        if isinstance(raw_staging, dict):
            self.staging.restore_from(raw_staging)
