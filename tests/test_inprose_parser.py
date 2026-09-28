"""Unit and integration tests for inProse parser and SceneMaterializer."""

import pytest
from inprose import ParseError, ScreenplayParser

from dotter.core.nodes import (
    AppendNode,
    CallNode,
    ChoiceSetNode,
    DialogueNode,
    FreshBoxNode,
    HookNode,
    JumpNode,
    LabelNode,
    NarrationNode,
    ReturnNode,
)
from dotter.scenes.materializer import CompilationError, SceneMaterializer

SAMPLE_SCRIPT = """
## The Clearing --- clearing_label

# This is an ambient comment
Alice: {voice:alice_01.ogg} Welcome to the ancient ruins!
- Look at those carved pillars.
/ Be careful where you step.

The wind howls through the stone.
A cold chill runs down your spine.

~ inspect_pillars

? Examine the glowing runes (runes)
? Turn back towards town (exit)

## Ancient Runes --- runes
The runes shimmer with blue light.
>> secret_subroutine
> clearing_label

## Subroutine --- secret_subroutine
Alice: A hidden compartment opened!
<<

## Town Exit --- exit
You head back to town.
"""


def test_screenplay_parser_full_flow() -> None:
    """Verify parser extracts all node types and groups narration/choices."""
    parser = ScreenplayParser()
    items = parser.parse(SAMPLE_SCRIPT)
    assert len(items) == 16

    materializer = SceneMaterializer("demo")
    scene = materializer.materialize(items)

    assert scene.scene_name == "demo"
    assert scene.entry_node_id == "demo.clearing_label.0"
    assert "clearing_label" in scene.labels
    assert "runes" in scene.labels
    assert "secret_subroutine" in scene.labels
    assert "exit" in scene.labels

    # Verify LabelNode
    n0 = scene.get_node("demo.clearing_label.0")
    assert isinstance(n0, LabelNode)
    assert n0.display_name == "The Clearing"

    # Verify DialogueNode with voice
    n1 = scene.get_node("demo.clearing_label.1")
    assert isinstance(n1, DialogueNode)
    assert n1.speaker == "Alice"
    assert n1.voice == "alice_01.ogg"
    assert n1.text == "Welcome to the ancient ruins!"
    assert n1.emotion is None

    # Verify AppendNode
    n2 = scene.get_node("demo.clearing_label.2")
    assert isinstance(n2, AppendNode)
    assert n2.text == "Look at those carved pillars."

    # Verify FreshBoxNode
    n3 = scene.get_node("demo.clearing_label.3")
    assert isinstance(n3, FreshBoxNode)
    assert n3.text == "Be careful where you step."

    # Verify joined NarrationNode
    n4 = scene.get_node("demo.clearing_label.4")
    assert isinstance(n4, NarrationNode)
    assert "The wind howls" in n4.text
    assert "A cold chill" in n4.text

    # Verify HookNode
    n5 = scene.get_node("demo.clearing_label.5")
    assert isinstance(n5, HookNode)
    assert n5.hook_name == "inspect_pillars"

    # Verify ChoiceSetNode
    n6 = scene.get_node("demo.clearing_label.6")
    assert isinstance(n6, ChoiceSetNode)
    assert len(n6.options) == 2
    assert n6.options[0].target == "runes"
    assert n6.options[1].target == "exit"

    # Verify edge connections from choice set
    choice_edges = scene.get_next_node_ids("demo.clearing_label.6")
    assert choice_edges == ("demo.runes.0", "demo.exit.0")

    # Verify CallNode & ReturnNode
    call_node = scene.get_node("demo.runes.2")
    assert isinstance(call_node, CallNode)
    assert call_node.target == "secret_subroutine"

    ret_node = scene.get_node("demo.secret_subroutine.2")
    assert isinstance(ret_node, ReturnNode)

    # Verify JumpNode
    jump_node = scene.get_node("demo.runes.3")
    assert isinstance(jump_node, JumpNode)
    assert jump_node.target == "clearing_label"
    assert scene.get_next_node_ids("demo.runes.3") == ("demo.clearing_label.0",)


def test_parser_syntax_errors() -> None:
    """Verify parser raises descriptive ParseError on bad syntax."""
    parser = ScreenplayParser()
    with pytest.raises(ParseError, match="Invalid choice syntax"):
        parser.parse("? This choice has no target parentheses")


def test_materializer_validation_errors() -> None:
    """Verify materializer catches dangling targets and duplicate labels."""
    parser = ScreenplayParser()

    # Dangling jump target
    items = parser.parse("## Start\n> nonexistent_label\n")
    materializer = SceneMaterializer("test")
    with pytest.raises(CompilationError, match="Undefined target label 'nonexistent_label'"):
        materializer.materialize(items)

    # Duplicate label
    items = parser.parse("## Intro\n## Intro\n")
    with pytest.raises(CompilationError, match="Duplicate label identifier 'intro'"):
        materializer.materialize(items)
