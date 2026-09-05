"""End-to-end integration test exercising all P0 features through the demo playthrough."""

from pathlib import Path

from dotter.__main__ import main
from dotter.core.nodes import ChoiceSetNode, DialogueNode
from dotter.core.types import SpritePosition
from dotter.demo import build_demo_engine, run_demo
from dotter.runtime.engine import Engine
from dotter.save.manager import SaveManager
from dotter.staging.compositor import StagingCompositor


def test_cli_entry_points(tmp_path: Path) -> None:
    """Verify main() CLI execution in headless mode."""
    assert main(["demo", "--headless"]) == 0
    assert main(["run", "--headless"]) == 0
    assert run_demo(headless=True) == 0


def _verify_clearing_and_puzzle(
    engine: Engine, compositor: StagingCompositor, save_mgr: SaveManager
) -> None:
    state = engine.state
    b1 = engine.advance()
    assert isinstance(b1, DialogueNode) and b1.speaker == "Alice"
    assert b1.voice == "alice_01.ogg"
    assert state.staging.background == "bg_ruins"
    assert state.staging.current_bgm == "theme_ancient.ogg"
    assert state.staging.current_ambience == "wind.ogg"

    engine.advance()  # Append
    engine.advance()  # FreshBox
    engine.advance()  # Narration

    b5 = engine.advance()
    assert isinstance(b5, DialogueNode) and b5.speaker == "Bob"
    assert state.get_variable("inspected_ruins") is True

    plans = compositor.get_ordered_sprites(state.staging)
    assert len(plans) == 1 and plans[0].character == "alice"
    assert plans[0].position == (480, 0)

    b6 = engine.advance()
    assert isinstance(b6, DialogueNode) and b6.speaker == "Bob"
    assert state.staging.current_bgm == "theme_puzzle.ogg"
    assert "bob" in state.staging.sprites
    assert len(state.call_stack) == 1

    multi_plans = compositor.get_ordered_sprites(state.staging)
    assert [p.character for p in multi_plans] == ["bob", "alice"]

    engine.advance()  # Append
    engine.advance()  # Narration
    b9 = engine.advance()
    assert isinstance(b9, DialogueNode)
    assert state.get_variable("puzzle_solved") is True

    b10 = engine.advance()
    assert isinstance(b10, DialogueNode) and b10.speaker == "Alice"
    assert len(state.call_stack) == 0


def _verify_save_and_sanctum_branch(engine: Engine, save_mgr: SaveManager) -> None:
    state = engine.state
    save_mgr.quick_save(state, thumbnail=b"mock_thumb")
    state_id = id(state)
    vars_id = id(state.variables)

    state.set_variable("puzzle_solved", False)
    assert state.get_variable("puzzle_solved") is False

    assert save_mgr.quick_load(state) is True
    assert id(state) == state_id
    assert id(state.variables) == vars_id
    assert state.get_variable("puzzle_solved") is True

    b11 = engine.advance()
    assert isinstance(b11, ChoiceSetNode)
    assert engine.is_waiting_for_choice is True

    b12 = engine.choose(0)
    assert b12 is not None
    assert state.staging.background == "bg_sanctum"
    assert state.staging.sprites["alice"].face == "amazed"
    assert state.staging.sprites["alice"].position == SpritePosition.CENTER

    engine.advance()
    engine.advance()
    engine.advance()
    engine.advance()  # Final narration

    assert engine.advance() is None
    assert engine.is_finished is True


def test_demo_full_playthrough_and_subsystem_integration(tmp_path: Path) -> None:
    """Verify all P0 systems end-to-end: narrative, staging, audio, choices, and save/load."""
    engine = build_demo_engine()
    compositor = StagingCompositor()
    save_mgr = SaveManager(tmp_path / "saves")

    _verify_clearing_and_puzzle(engine, compositor, save_mgr)
    _verify_save_and_sanctum_branch(engine, save_mgr)
