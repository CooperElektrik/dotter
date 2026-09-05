"""Unit tests for staging Viewport, sprite compositor, and transition effects."""

from dotter.core.state import CharacterSpriteState, StagingState
from dotter.core.types import SpritePosition, TransitionType
from dotter.staging.compositor import (
    ActiveTransition,
    StagingCompositor,
    resolve_sprite_plan,
)
from dotter.staging.viewport import Viewport


def test_viewport_aspect_scaling() -> None:
    """Verify viewport calculation across 16:9, pillarbox (ultrawide), and letterbox (4:3)."""
    # Exact 16:9 match
    vp = Viewport(1920, 1080)
    assert vp.scale == 1.0
    assert vp.offset_x == 0.0
    assert vp.offset_y == 0.0
    assert vp.virtual_to_window(960, 540) == (960.0, 540.0)
    assert vp.window_to_virtual(960.0, 540.0) == (960.0, 540.0)
    assert vp.is_in_bounds(100, 100) is True

    # Ultrawide (2560x1080) -> Pillarbox (bars on left and right)
    vp.update(2560, 1080)
    assert vp.scale == 1.0
    assert vp.offset_x == (2560 - 1920) / 2.0  # 320.0
    assert vp.offset_y == 0.0
    assert vp.is_in_bounds(10, 540) is False
    assert vp.is_in_bounds(500, 540) is True

    # 4:3 (1440x1080) -> Letterbox (bars on top and bottom)
    vp.update(1440, 1080)
    assert vp.scale == 1440 / 1920  # 0.75
    assert vp.offset_x == 0.0
    expected_render_h = 1080 * 0.75  # 810
    assert vp.offset_y == (1080 - expected_render_h) / 2.0  # 135.0


def test_composite_sprite_layering() -> None:
    """Verify layered composite sprite paths and anchor coordinates."""
    sprite = CharacterSpriteState(
        character="alice",
        face="happy",
        outfit="school_uniform",
        position=SpritePosition.LEFT,
        z_order=2,
    )
    plan = resolve_sprite_plan(sprite)

    assert plan.character == "alice"
    assert plan.position == (480, 0)
    assert plan.z_order == 2
    assert plan.layer_paths == (
        "sprites/alice/base.png",
        "sprites/alice/outfit_school_uniform.png",
        "sprites/alice/face_happy.png",
    )

    # Custom coordinate offset
    custom_sprite = CharacterSpriteState(
        character="bob",
        face=None,
        outfit=None,
        position=(500, 150),
        z_order=0,
    )
    plan_custom = resolve_sprite_plan(custom_sprite)
    assert plan_custom.position == (500, 150)
    assert plan_custom.layer_paths == ("sprites/bob/base.png",)


def test_staging_compositor_z_ordering() -> None:
    """Verify that get_ordered_sprites sorts stably by z-order ascending."""
    staging = StagingState()
    staging.sprites["front"] = CharacterSpriteState(
        character="front", position=SpritePosition.RIGHT, z_order=10
    )
    staging.sprites["back"] = CharacterSpriteState(
        character="back", position=SpritePosition.LEFT, z_order=-5
    )
    staging.sprites["mid"] = CharacterSpriteState(
        character="mid", position=SpritePosition.CENTER, z_order=0
    )

    compositor = StagingCompositor()
    ordered = compositor.get_ordered_sprites(staging)

    assert [p.character for p in ordered] == ["back", "mid", "front"]


def test_active_transitions() -> None:
    """Verify transition interpolation curves and midpoint background swap."""
    # Dissolve (crossfade)
    tx_dissolve = ActiveTransition(
        transition_type=TransitionType.DISSOLVE,
        duration=2.0,
        from_background="bg_old",
        to_background="bg_new",
    )
    assert tx_dissolve.progress == 0.0
    tx_dissolve.update(1.0)
    assert tx_dissolve.progress == 0.5
    assert tx_dissolve.overlay_alpha == 0.5
    assert tx_dissolve.effective_background == "bg_new"

    # Fade to Black
    tx_fade = ActiveTransition(
        transition_type=TransitionType.FADE_BLACK,
        duration=2.0,
        from_background="bg_old",
        to_background="bg_new",
    )
    # Quarter way: fading into black (alpha increasing)
    tx_fade.update(0.5)
    assert tx_fade.progress == 0.25
    assert tx_fade.effective_background == "bg_old"
    assert tx_fade.overlay_alpha == 0.5

    # Three-quarter way: fading out of black into new bg
    tx_fade.update(1.0)  # total 1.5s
    assert tx_fade.progress == 0.75
    assert tx_fade.effective_background == "bg_new"
    assert round(tx_fade.overlay_alpha, 2) == 0.5

    # Finished
    finished = tx_fade.update(0.6)
    assert finished is True
    assert tx_fade.progress == 1.0
