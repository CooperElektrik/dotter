"""Unit tests for SpriteRenderer: texture caching, positioning, z-order, visibility."""

import pyglet
from pyglet.image import SolidColorImagePattern

from dotter.core.state import CharacterSpriteState, StagingState
from dotter.core.types import SpritePosition
from dotter.runtime.sprite_renderer import SpriteRenderer
from dotter.staging.compositor import StagingCompositor
from dotter.staging.viewport import Viewport

_TEX_300_600 = pyglet.image.create(300, 600, SolidColorImagePattern((255, 0, 0, 255)))


def _make_renderer(loader=None, vp_w=1280, vp_h=720):
    """Create a SpriteRenderer with an optional custom texture loader."""
    vp = Viewport(vp_w, vp_h)
    comp = StagingCompositor(vp)
    if loader is None:

        def default_loader(path: str) -> pyglet.image.AbstractImage:
            return _TEX_300_600

        loader = default_loader

    return SpriteRenderer(vp, comp, texture_loader=loader), vp, comp


def test_sprite_renderer_creates_and_positions_sprites() -> None:
    """Verify sprite creation, scale, and viewport-transformed positioning."""
    renderer, vp, _ = _make_renderer()
    staging = StagingState()
    staging.sprites["alice"] = CharacterSpriteState(
        character="alice", face="happy", position=SpritePosition.LEFT, z_order=0
    )

    renderer.draw(staging)

    assert "alice" in renderer._sprites
    sp = renderer._sprites["alice"]
    assert sp.visible is True
    assert round(sp.scale, 4) == round(vp.scale, 4)

    # LEFT anchor = vx 480, vy 0; +100 offset; sprite centered horizontally
    # vp.scale for 1280x720 = 1280/1920 = 0.6667
    # wx = 480 * 0.6667 = 320, wy = (0+100) * 0.6667 = 66.667
    # x = 320 - (300 * 0.6667) / 2 = 320 - 100 = 220
    assert round(sp.x, 1) == 220.0
    assert round(sp.y, 1) == 66.7


def test_sprite_renderer_texture_caching() -> None:
    """Verify textures are loaded once and cached by path."""
    call_count = 0

    def tracking_loader(path):
        nonlocal call_count
        call_count += 1
        return pyglet.image.create(200, 400)

    renderer, _, _ = _make_renderer(loader=tracking_loader)
    staging = StagingState()
    staging.sprites["alice"] = CharacterSpriteState(character="alice")

    renderer.draw(staging)
    assert call_count == 1
    # Re-draw without changes: texture must come from cache
    renderer.draw(staging)
    assert call_count == 1


def test_sprite_renderer_sprite_reuse() -> None:
    """Verify sprite instances are reused across draw calls (no per-frame allocation)."""
    renderer, _, _ = _make_renderer()
    staging = StagingState()
    staging.sprites["alice"] = CharacterSpriteState(character="alice")

    renderer.draw(staging)
    first_id = id(renderer._sprites["alice"])
    renderer.draw(staging)
    assert id(renderer._sprites["alice"]) == first_id


def test_sprite_renderer_hides_inactive_sprites() -> None:
    """Verify sprites removed from staging become invisible."""
    renderer, _, _ = _make_renderer()
    staging = StagingState()
    staging.sprites["alice"] = CharacterSpriteState(character="alice")

    renderer.draw(staging)
    assert renderer._sprites["alice"].visible is True

    # Character disappears from staging
    staging.sprites.clear()
    renderer.draw(staging)
    assert renderer._sprites["alice"].visible is False


def test_sprite_renderer_z_ordering_with_multiple_sprites() -> None:
    """Verify all sprites in staging are rendered, in compositor z-order."""
    renderer, _, _ = _make_renderer()
    staging = StagingState()
    staging.sprites["back"] = CharacterSpriteState(
        character="back", position=SpritePosition.LEFT, z_order=-5
    )
    staging.sprites["front"] = CharacterSpriteState(
        character="front", position=SpritePosition.RIGHT, z_order=10
    )

    renderer.draw(staging)

    assert set(renderer._sprites.keys()) == {"back", "front"}
    assert renderer._sprites["back"].visible is True
    assert renderer._sprites["front"].visible is True
    # RIGHT anchor = vx 1440
    assert renderer._sprites["back"].x < renderer._sprites["front"].x


def test_sprite_renderer_viewport_resize_reposition() -> None:
    """Verify sprites reposition when viewport resizes."""
    renderer, vp, _ = _make_renderer()
    staging = StagingState()
    staging.sprites["bob"] = CharacterSpriteState(
        character="bob", position=SpritePosition.CENTER, z_order=0
    )

    renderer.draw(staging)
    x_before = renderer._sprites["bob"].x

    # Resize to exact 16:9 (scale becomes 1.0)
    vp.update(1920, 1080)
    renderer.draw(staging)
    x_after = renderer._sprites["bob"].x

    assert x_after > x_before  # sprite moves right when scale increases
    assert round(renderer._sprites["bob"].scale, 4) == 1.0
