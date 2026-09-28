"""Sprite rendering with texture caching and pyglet batch drawing."""

from collections.abc import Callable

import pyglet
from pyglet.graphics import Batch
from pyglet.sprite import Sprite

from dotter.core.state import StagingState
from dotter.staging.compositor import CompositeSpritePlan, StagingCompositor
from dotter.staging.viewport import Viewport

TextureLoader = Callable[[str], pyglet.image.AbstractImage | None]

# Vertical offset (virtual pixels) to raise sprites above the bottom edge,
# preserving the visual convention from the placeholder box layout.
SPRITE_Y_OFFSET = 100.0


def _default_texture_loader(path: str) -> pyglet.image.AbstractImage | None:
    """Load a texture by relative resource path, returning None on failure."""
    try:
        return pyglet.resource.image(path)
    except Exception:
        return None


class SpriteRenderer:
    """Caches pyglet textures and batch-renders character sprites from staging state.

    Holds a reference to the shared ``Viewport`` so it sees in-place resize
    updates automatically.  Textures are cached by path (standard dict) and
    ``pyglet.sprite.Sprite`` instances are reused per character to avoid
    per-frame allocations on the hot path.
    """

    def __init__(
        self,
        viewport: Viewport,
        compositor: StagingCompositor,
        texture_loader: TextureLoader | None = None,
    ) -> None:
        self.viewport = viewport
        self._compositor = compositor
        self._texture_loader = texture_loader or _default_texture_loader
        self._batch = Batch()
        self._textures: dict[str, pyglet.image.AbstractImage | None] = {}
        self._sprites: dict[str, Sprite] = {}

    def _get_texture(self, path: str) -> pyglet.image.AbstractImage | None:
        """Load and cache a texture by path."""
        if path not in self._textures:
            self._textures[path] = self._texture_loader(path)
        return self._textures[path]

    def _get_or_create_sprite(self, character: str, tex: pyglet.image.AbstractImage) -> Sprite:
        """Create or reuse a batched Sprite for the given character."""
        if character not in self._sprites:
            self._sprites[character] = Sprite(tex, batch=self._batch, subpixel=True)
        else:
            self._sprites[character].image = tex
        return self._sprites[character]

    def _position_sprite(
        self,
        sp: Sprite,
        plan: CompositeSpritePlan,
        tex: pyglet.image.AbstractImage,
    ) -> None:
        """Set sprite scale and position from plan coordinates via the viewport."""
        sp.scale = self.viewport.scale
        vx, vy = plan.position
        wx, wy = self.viewport.virtual_to_window(float(vx), float(vy) + SPRITE_Y_OFFSET)
        sp.update(x=wx - tex.width * sp.scale / 2.0, y=wy)

    def draw(self, staging: StagingState) -> None:
        """Update sprite state from staging and render all visible sprites in one batch."""
        active: set[str] = set()

        for plan in self._compositor.get_ordered_sprites(staging):
            active.add(plan.character)
            tex = self._get_texture(plan.layer_paths[0])
            if tex is None:
                continue
            sp = self._get_or_create_sprite(plan.character, tex)
            sp.visible = True
            self._position_sprite(sp, plan, tex)

        for char, sp in self._sprites.items():
            if char not in active:
                sp.visible = False

        self._batch.draw()
