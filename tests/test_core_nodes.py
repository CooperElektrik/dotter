"""Unit tests for IR nodes and SceneIR data structures."""

from dataclasses import FrozenInstanceError

import pytest

from dotter.core.nodes import (
    AppendNode,
    CallNode,
    ChoiceOption,
    ChoiceSetNode,
    DialogueNode,
    FreshBoxNode,
    HookNode,
    JumpNode,
    LabelNode,
    NarrationNode,
    ReturnNode,
    SceneIR,
)
from dotter.core.types import AudioChannel, SpritePosition, TransitionType


def test_core_enums() -> None:
    """Verify enum values."""
    assert SpritePosition.LEFT == "left"
    assert SpritePosition.CENTER == "center"
    assert SpritePosition.RIGHT == "right"
    assert SpritePosition.CUSTOM == "custom"

    assert TransitionType.DISSOLVE == "dissolve"
    assert TransitionType.FADE_BLACK == "fade_black"
    assert TransitionType.FADE_WHITE == "fade_white"
    assert TransitionType.CUT == "cut"

    assert AudioChannel.BGM == "bgm"
    assert AudioChannel.VOICE == "voice"
    assert AudioChannel.SFX == "sfx"
    assert AudioChannel.AMB == "amb"


def test_node_instantiation_and_immutability() -> None:
    """Verify that all node types instantiate and enforce immutability."""
    dialogue = DialogueNode(
        node_id="scene.label.1",
        speaker="Alice",
        text="Hello world",
        voice="audio/v1.ogg",
    )
    assert dialogue.speaker == "Alice"
    assert dialogue.voice == "audio/v1.ogg"

    with pytest.raises(FrozenInstanceError):
        field_name = "speaker"
        setattr(dialogue, field_name, "Bob")

    label = LabelNode(node_id="scene.label.0", name="start", display_name="The Start")
    assert label.name == "start"

    append = AppendNode(node_id="scene.label.2", text="more text")
    assert append.text == "more text"

    fresh = FreshBoxNode(node_id="scene.label.3", text="fresh text")
    assert fresh.text == "fresh text"

    narration = NarrationNode(node_id="scene.label.4", text="narrator spoke")
    assert narration.text == "narrator spoke"

    opt1 = ChoiceOption(text="Option 1", target="target1")
    opt2 = ChoiceOption(text="Option 2", target="target2")
    choices = ChoiceSetNode(node_id="scene.label.5", options=(opt1, opt2))
    assert len(choices.options) == 2
    assert choices.options[0].target == "target1"

    jump = JumpNode(node_id="scene.label.6", target="other_label")
    assert jump.target == "other_label"

    call = CallNode(node_id="scene.label.7", target="subroutine")
    assert call.target == "subroutine"

    ret = ReturnNode(node_id="scene.label.8")
    assert ret.node_id == "scene.label.8"

    hook = HookNode(node_id="scene.label.9", hook_name="on_enter_room")
    assert hook.hook_name == "on_enter_room"


def test_scene_ir_graph() -> None:
    """Verify SceneIR container node retrieval and edge navigation."""
    n0 = LabelNode(node_id="s.l.0", name="intro", display_name="Intro")
    n1 = DialogueNode(node_id="s.l.1", speaker="Alice", text="Welcome!")
    n2 = JumpNode(node_id="s.l.2", target="outro")

    scene = SceneIR(
        scene_name="intro_scene",
        entry_node_id="s.l.0",
        nodes={"s.l.0": n0, "s.l.1": n1, "s.l.2": n2},
        labels={"intro": "s.l.0"},
        edges={"s.l.0": ("s.l.1",), "s.l.1": ("s.l.2",)},
    )

    assert scene.scene_name == "intro_scene"
    assert scene.entry_node_id == "s.l.0"
    assert scene.get_node("s.l.0") == n0
    assert scene.get_node("s.l.1") == n1
    assert scene.get_next_node_ids("s.l.0") == ("s.l.1",)
    assert scene.get_next_node_ids("s.l.2") == ()

    with pytest.raises(KeyError, match="Node 's.l.999' not found in scene 'intro_scene'"):
        scene.get_node("s.l.999")
