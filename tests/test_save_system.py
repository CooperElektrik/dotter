"""Unit and integration tests for SaveManager and serialization."""

from pathlib import Path

from dotter.core.state import CharacterSpriteState, GameState, StagingState
from dotter.core.types import SpritePosition
from dotter.save.manager import SaveManager
from dotter.save.serializer import deserialize_state, serialize_state


def _build_test_state() -> GameState:
    return GameState(
        cursor_position="scene.clearing.5",
        call_stack=["scene.main.1", "scene.sub.2"],
        variables={"romance": 7, "discovered_map": True},
        staging=StagingState(
            background="bg_forest",
            sprites={
                "alice": CharacterSpriteState(
                    character="alice",
                    face="happy",
                    outfit="uniform",
                    position=SpritePosition.CENTER,
                    z_order=1,
                )
            },
            current_bgm="forest_theme.ogg",
            current_ambience="birds.ogg",
            current_voice="alice_05.ogg",
        ),
        chapter_title="Chapter 1: The Forest",
        playtime_seconds=345.5,
    )


def test_serializer_roundtrip() -> None:
    """Verify serialize_state and deserialize_state preserve all state fields."""
    state = _build_test_state()
    payload = serialize_state(state)

    assert payload["version"] == 1
    assert payload["cursor_position"] == "scene.clearing.5"
    assert payload["chapter_title"] == "Chapter 1: The Forest"
    assert payload["playtime_seconds"] == 345.5
    assert payload["variables"]["romance"] == 7
    assert payload["staging"]["background"] == "bg_forest"
    assert payload["staging"]["sprites"]["alice"]["face"] == "happy"

    restored = GameState()
    deserialize_state(payload, restored)

    assert restored.cursor_position == "scene.clearing.5"
    assert restored.call_stack == ["scene.main.1", "scene.sub.2"]
    assert restored.get_variable("romance") == 7
    assert restored.get_variable("discovered_map") is True
    assert restored.staging.background == "bg_forest"
    assert "alice" in restored.staging.sprites
    assert restored.staging.sprites["alice"].face == "happy"


def test_save_manager_in_place_restore(tmp_path: Path) -> None:
    """Verify SaveManager restores state strictly in-place preserving object identity."""
    mgr = SaveManager(tmp_path / "saves")
    original_state = _build_test_state()

    mock_png = b"\x89PNG\r\n\x1a\n\x00\x00"
    save_path = mgr.save_slot(1, original_state, thumbnail=mock_png)
    assert save_path.exists()

    # Active live runtime state container
    live_state = GameState(variables={"initial_var": 42})
    state_id = id(live_state)
    vars_id = id(live_state.variables)
    stack_id = id(live_state.call_stack)
    staging_id = id(live_state.staging)
    sprites_id = id(live_state.staging.sprites)

    loaded = mgr.load_slot(1, live_state)
    assert loaded is True

    # Invariants: container identities must never change
    assert id(live_state) == state_id
    assert id(live_state.variables) == vars_id
    assert id(live_state.call_stack) == stack_id
    assert id(live_state.staging) == staging_id
    assert id(live_state.staging.sprites) == sprites_id

    # Contents must reflect saved slot
    assert live_state.cursor_position == "scene.clearing.5"
    assert live_state.get_variable("romance") == 7
    assert "initial_var" not in live_state.variables
    assert live_state.staging.background == "bg_forest"


def test_save_manager_quick_and_auto_save(tmp_path: Path) -> None:
    """Verify quick_save/load and auto_save/load slots."""
    mgr = SaveManager(tmp_path / "saves")
    state = _build_test_state()

    # Quick save/load
    q_path = mgr.quick_save(state)
    assert q_path.name == "slot_quick.json"

    loaded_quick = GameState()
    assert mgr.quick_load(loaded_quick) is True
    assert loaded_quick.chapter_title == "Chapter 1: The Forest"

    # Auto save/load
    a_path = mgr.auto_save(state)
    assert a_path.name == "slot_auto.json"

    loaded_auto = GameState()
    assert mgr.auto_load(loaded_auto) is True
    assert loaded_auto.cursor_position == "scene.clearing.5"


def test_save_manager_slot_catalog(tmp_path: Path) -> None:
    """Verify list_slots enumerates slots with metadata and thumbnail flag."""
    mgr = SaveManager(tmp_path / "saves")
    state = _build_test_state()

    mgr.save_slot(1, state, thumbnail=b"fake_png")
    mgr.save_slot(2, state, thumbnail=None)

    slots = mgr.list_slots()
    assert len(slots) == 2

    slot1 = next(s for s in slots if s.slot_id == "1")
    assert slot1.has_thumbnail is True
    assert slot1.chapter_title == "Chapter 1: The Forest"

    slot2 = next(s for s in slots if s.slot_id == "2")
    assert slot2.has_thumbnail is False

    # Deletion
    assert mgr.delete_slot(1) is True
    assert len(mgr.list_slots()) == 1
    assert mgr.load_slot(1, GameState()) is False
