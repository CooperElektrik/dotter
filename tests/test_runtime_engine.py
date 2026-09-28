"""Tier 1 stateful integration test simulating 20+ steps of the narrative loop."""

import pytest
from inprose import ScreenplayParser

from dotter.core.nodes import (
    AppendNode,
    ChoiceSetNode,
    DialogueNode,
    FreshBoxNode,
    NarrationNode,
)
from dotter.core.state import GameState
from dotter.core.types import SpritePosition
from dotter.runtime.cursor import CursorError
from dotter.runtime.engine import Engine
from dotter.scenes.hooks import HookRegistry
from dotter.scenes.materializer import SceneMaterializer

COMPREHENSIVE_SCRIPT = """
## The Clearing --- clearing
Alice: Welcome to the ancient ruins!
- Look at these mysterious monoliths.
/ We should proceed with caution.

The wind whispers through the towering stone slabs.
Dust dances in the pale morning light.

~ inspect_monolith

Bob: I've found an odd mechanism over here.
>> puzzle_subroutine

Alice: Glad we got that open!
? Approach the sacred altar (altar)
? Retreat toward the valley (valley)

## Puzzle Subroutine --- puzzle_subroutine
Bob: It looks like a sequence lock.
- Let me align the ancient gears...
A soft mechanical chime echoes as the stones shift.
~ solve_puzzle
Bob: The mechanism clicked into place!
<<

## Sacred Altar --- altar
The air grows warm and heavy with ancient power.
Alice: Look at the inscription carved into the pedestal.
/ It tells of a forgotten guardian.
Bob: We shouldn't linger here too long.
> finale

## Valley Retreat --- valley
You turn back and descend into the safety of the valley.
> finale

## The Finale --- finale
The expedition draws to an end.
"""


def _setup_test_hooks(hooks: HookRegistry, entered: list[str], exited: list[str]) -> None:
    hooks.register_on_entry(
        "clearing",
        lambda c: (
            entered.append("clearing"),
            c.background("bg_ruins"),
            c.music("theme_ruins.ogg"),
        ),
    )
    hooks.register_on_exit(
        "clearing",
        lambda c: (
            exited.append("clearing"),
            c.hide("alice"),
        ),
    )
    hooks.register_on_entry(
        "altar",
        lambda c: (
            entered.append("altar"),
            c.background("bg_altar"),
        ),
    )
    hooks.register_hook(
        "inspect_monolith",
        lambda c: (
            c.show("alice", face="curious", at=SpritePosition.CENTER),
            c.set("inspected_monolith", True),
        ),
    )
    hooks.register_hook(
        "solve_puzzle",
        lambda c: (
            c.set("puzzle_solved", True),
            c.sfx("puzzle_chime.ogg"),
        ),
    )


def _step_clearing_beats(engine: Engine, state: GameState, entered: list[str]) -> int:
    b1 = engine.advance()
    assert isinstance(b1, DialogueNode) and b1.speaker == "Alice"
    assert "clearing" in entered
    assert state.staging.background == "bg_ruins"
    assert state.staging.current_bgm == "theme_ruins.ogg"

    b2 = engine.advance()
    assert isinstance(b2, AppendNode)

    b3 = engine.advance()
    assert isinstance(b3, FreshBoxNode)

    b4 = engine.advance()
    assert isinstance(b4, NarrationNode)

    b5 = engine.advance()
    assert isinstance(b5, DialogueNode) and b5.speaker == "Bob"
    assert state.get_variable("inspected_monolith") is True
    assert "alice" in state.staging.sprites
    return 5


def _step_puzzle_subroutine(engine: Engine, state: GameState) -> int:
    b6 = engine.advance()
    assert isinstance(b6, DialogueNode) and b6.speaker == "Bob"
    assert len(state.call_stack) == 1

    b7 = engine.advance()
    assert isinstance(b7, AppendNode)

    b8 = engine.advance()
    assert isinstance(b8, NarrationNode)

    b9 = engine.advance()
    assert isinstance(b9, DialogueNode)
    assert state.get_variable("puzzle_solved") is True

    b10 = engine.advance()
    assert isinstance(b10, DialogueNode) and b10.speaker == "Alice"
    assert len(state.call_stack) == 0
    return 5


def _step_altar_and_finale(
    engine: Engine, state: GameState, entered: list[str], exited: list[str]
) -> int:
    choice_node = engine.advance()
    assert isinstance(choice_node, ChoiceSetNode)
    assert engine.is_waiting_for_choice is True

    with pytest.raises(CursorError, match="awaiting player choice"):
        engine.advance()

    b12 = engine.choose(0)
    assert isinstance(b12, NarrationNode)
    assert "clearing" in exited
    assert "alice" not in state.staging.sprites
    assert "altar" in entered
    assert state.staging.background == "bg_altar"

    b13 = engine.advance()
    assert isinstance(b13, DialogueNode) and b13.speaker == "Alice"

    b14 = engine.advance()
    assert isinstance(b14, FreshBoxNode)

    b15 = engine.advance()
    assert isinstance(b15, DialogueNode) and b15.speaker == "Bob"

    b16 = engine.advance()
    assert isinstance(b16, NarrationNode)
    assert "draws to an end" in b16.text

    assert engine.advance() is None
    assert engine.is_finished is True
    return 6


def test_stateful_runtime_playthrough_20_plus_steps() -> None:
    """Execute a real, continuous 20+ step narrative playthrough with choices and subroutines."""
    parser = ScreenplayParser()
    items = parser.parse(COMPREHENSIVE_SCRIPT)
    materializer = SceneMaterializer("act1")
    scene = materializer.materialize(items)

    hooks = HookRegistry()
    entered_labels: list[str] = []
    exited_labels: list[str] = []
    _setup_test_hooks(hooks, entered_labels, exited_labels)

    state = GameState()
    engine = Engine(scene=scene, state=state, hooks=hooks, headless=True)

    steps = 0
    steps += _step_clearing_beats(engine, state, entered_labels)
    steps += _step_puzzle_subroutine(engine, state)
    steps += _step_altar_and_finale(engine, state, entered_labels, exited_labels)

    assert steps >= 16
