"""Integration tests for StagingCommand and in-place GameState restoration."""

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
from dotter.core.state import CharacterSpriteState, GameState, StagingState
from dotter.core.types import SpritePosition, TransitionType


def test_staging_commands_instantiation() -> None:
    """Verify that all staging commands instantiate correctly with default and explicit fields."""
    show = ShowCommand(
        character="Alice",
        face="happy",
        outfit="school",
        at=SpritePosition.LEFT,
        z_order=1,
    )
    assert show.character == "Alice"
    assert show.face == "happy"
    assert show.outfit == "school"
    assert show.at == SpritePosition.LEFT
    assert show.z_order == 1

    hide = HideCommand(character="Alice")
    assert hide.character == "Alice"

    bg = BackgroundCommand(
        background="bg_classroom",
        transition=TransitionType.DISSOLVE,
        duration=1.5,
    )
    assert bg.background == "bg_classroom"
    assert bg.transition == TransitionType.DISSOLVE
    assert bg.duration == 1.5

    music = MusicCommand(track="theme.ogg", loop=True, fade_in=1.0, fade_out=0.5)
    assert music.track == "theme.ogg"
    assert music.loop is True

    sfx = SfxCommand(clip="click.ogg", volume=0.8)
    assert sfx.clip == "click.ogg"
    assert sfx.volume == 0.8

    amb = AmbienceCommand(track="rain.ogg", loop=True, fade_in=2.0)
    assert amb.track == "rain.ogg"

    voice = VoiceCommand(clip="alice_01.ogg")
    assert voice.clip == "alice_01.ogg"

    set_var = SetVarCommand(name="affection", value=10)
    assert set_var.name == "affection"
    assert set_var.value == 10

    goto = GotoCommand(label="act2_start")
    assert goto.label == "act2_start"


def test_game_state_in_place_restore() -> None:
    """Verify that GameState.restore_from mutates existing instances in-place."""
    state = GameState(
        cursor_position="scene.label.1",
        call_stack=["scene.main.0"],
        variables={"romance": 5, "visited_library": True},
        staging=StagingState(
            background="old_bg",
            sprites={"alice": CharacterSpriteState(character="alice", face="neutral")},
            current_bgm="old_music.ogg",
        ),
        chapter_title="Chapter 1",
        playtime_seconds=120.0,
    )

    # Capture original object IDs
    state_id = id(state)
    vars_id = id(state.variables)
    stack_id = id(state.call_stack)
    staging_id = id(state.staging)
    sprites_id = id(state.staging.sprites)

    # Simulated serialized save payload
    save_payload = {
        "cursor_position": "scene.label.5",
        "call_stack": ["scene.main.0", "scene.sub.2"],
        "variables": {"romance": 10, "visited_library": True, "discovered_secret": True},
        "staging": {
            "background": "new_bg",
            "sprites": {
                "bob": {
                    "character": "bob",
                    "face": "surprised",
                    "outfit": "casual",
                    "position": "right",
                    "z_order": 2,
                }
            },
            "current_bgm": "new_music.ogg",
            "current_ambience": "rain.ogg",
            "current_voice": None,
        },
        "chapter_title": "Chapter 2",
        "playtime_seconds": 250.5,
    }

    state.restore_from(save_payload)

    # Invariants: object identities must be preserved exactly
    assert id(state) == state_id
    assert id(state.variables) == vars_id
    assert id(state.call_stack) == stack_id
    assert id(state.staging) == staging_id
    assert id(state.staging.sprites) == sprites_id

    # Contents must be updated correctly
    assert state.cursor_position == "scene.label.5"
    assert state.chapter_title == "Chapter 2"
    assert state.playtime_seconds == 250.5
    assert state.call_stack == ["scene.main.0", "scene.sub.2"]
    assert state.get_variable("romance") == 10
    assert state.get_variable("discovered_secret") is True
    assert state.staging.background == "new_bg"
    assert state.staging.current_bgm == "new_music.ogg"
    assert "bob" in state.staging.sprites
    assert "alice" not in state.staging.sprites
    assert state.staging.sprites["bob"].position == SpritePosition.RIGHT
