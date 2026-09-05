"""Staging compositor managing sprite layering, z-ordering, and transitions."""

from dataclasses import dataclass

from dotter.core.state import CharacterSpriteState, StagingState
from dotter.core.types import SpritePosition, TransitionType
from dotter.staging.viewport import Viewport

ANCHOR_X = {
    SpritePosition.LEFT: 480,
    SpritePosition.CENTER: 960,
    SpritePosition.RIGHT: 1440,
    SpritePosition.CUSTOM: 960,
}


@dataclass(frozen=True, slots=True)
class CompositeSpritePlan:
    """Ordered sprite render commands with layer paths and screen coordinates."""

    character: str
    position: tuple[int, int]
    z_order: int
    layer_paths: tuple[str, ...]


def resolve_sprite_plan(sprite: CharacterSpriteState) -> CompositeSpritePlan:
    """Resolve character sprite layers and coordinates from convention naming."""
    char = sprite.character
    layers: list[str] = [f"sprites/{char}/base.png"]

    if sprite.outfit:
        layers.append(f"sprites/{char}/outfit_{sprite.outfit}.png")
    if sprite.face:
        layers.append(f"sprites/{char}/face_{sprite.face}.png")

    if isinstance(sprite.position, SpritePosition):
        pos = (ANCHOR_X.get(sprite.position, 960), 0)
    else:
        pos = (int(sprite.position[0]), int(sprite.position[1]))

    return CompositeSpritePlan(
        character=char,
        position=pos,
        z_order=sprite.z_order,
        layer_paths=tuple(layers),
    )


@dataclass(slots=True)
class ActiveTransition:
    """Tracks transition interpolation across scene background switches."""

    transition_type: TransitionType
    duration: float
    elapsed: float = 0.0
    from_background: str | None = None
    to_background: str | None = None

    @property
    def is_active(self) -> bool:
        """True if the transition is still interpolating."""
        return self.elapsed < self.duration and self.transition_type != TransitionType.CUT

    @property
    def progress(self) -> float:
        """Normalized progress between 0.0 and 1.0."""
        if self.duration <= 0.0 or self.transition_type == TransitionType.CUT:
            return 1.0
        return min(1.0, self.elapsed / self.duration)

    @property
    def effective_background(self) -> str | None:
        """The active background image to display during transition."""
        if self.transition_type in (TransitionType.FADE_BLACK, TransitionType.FADE_WHITE):
            return self.from_background if self.progress < 0.5 else self.to_background
        return self.to_background

    @property
    def overlay_alpha(self) -> float:
        """Alpha level for color or crossfade overlay (0.0 to 1.0)."""
        match self.transition_type:
            case TransitionType.DISSOLVE:
                return self.progress
            case TransitionType.FADE_BLACK | TransitionType.FADE_WHITE:
                p = self.progress
                return p * 2.0 if p < 0.5 else (1.0 - p) * 2.0
            case _:
                return 0.0

    def update(self, dt: float) -> bool:
        """Advance transition time. Returns True if transition just finished."""
        if not self.is_active:
            return False
        self.elapsed += dt
        return not self.is_active


class StagingCompositor:
    """Coordinates sprite z-ordering, viewport scaling, and transition interpolation."""

    def __init__(self, viewport: Viewport | None = None) -> None:
        self.viewport = viewport or Viewport()
        self.active_transition: ActiveTransition | None = None

    def start_transition(
        self,
        t_type: TransitionType,
        duration: float,
        from_bg: str | None,
        to_bg: str | None,
    ) -> None:
        """Initiate a scene transition."""
        self.active_transition = ActiveTransition(
            transition_type=t_type,
            duration=duration,
            from_background=from_bg,
            to_background=to_bg,
        )

    def update(self, dt: float) -> None:
        """Update active transition timer."""
        if self.active_transition is not None:
            finished = self.active_transition.update(dt)
            if finished:
                self.active_transition = None

    def get_ordered_sprites(self, staging: StagingState) -> list[CompositeSpritePlan]:
        """Return composite sprites sorted stably by z-order ascending."""
        plans = [resolve_sprite_plan(s) for s in staging.sprites.values()]
        return sorted(plans, key=lambda p: (p.z_order, p.character))
