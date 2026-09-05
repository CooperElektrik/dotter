"""State serialization to and from standard JSON payloads."""

from datetime import datetime, timezone
from typing import Any

from dotter.core.state import CharacterSpriteState, GameState, StagingState
from dotter.core.types import SpritePosition

FORMAT_VERSION = 1


def _serialize_sprite(sprite: CharacterSpriteState) -> dict[str, Any]:
    """Serialize a single character sprite state."""
    pos_val: str | list[int]
    if isinstance(sprite.position, SpritePosition):
        pos_val = sprite.position.value
    else:
        pos_val = list(sprite.position)

    return {
        "character": sprite.character,
        "face": sprite.face,
        "outfit": sprite.outfit,
        "position": pos_val,
        "z_order": sprite.z_order,
    }


def _serialize_staging(staging: StagingState) -> dict[str, Any]:
    """Serialize visual and audio staging state."""
    return {
        "background": staging.background,
        "current_bgm": staging.current_bgm,
        "current_ambience": staging.current_ambience,
        "current_voice": staging.current_voice,
        "sprites": {name: _serialize_sprite(sprite) for name, sprite in staging.sprites.items()},
    }


def serialize_state(state: GameState) -> dict[str, Any]:
    """Convert GameState into a standard JSON-compatible dictionary."""
    return {
        "version": FORMAT_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "cursor_position": state.cursor_position,
        "call_stack": list(state.call_stack),
        "chapter_title": state.chapter_title,
        "playtime_seconds": state.playtime_seconds,
        "variables": dict(state.variables),
        "staging": _serialize_staging(state.staging),
    }


def deserialize_state(data: dict[str, Any], state: GameState) -> None:
    """Restore GameState in-place from a serialized JSON dictionary."""
    state.restore_from(data)
