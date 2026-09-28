"""Canonical demo scene and runtime launcher demonstrating all P0 engine capabilities."""

from pathlib import Path

from inprose import ScreenplayParser

from dotter.core.state import GameState
from dotter.core.types import SpritePosition, TransitionType
from dotter.runtime.engine import Engine
from dotter.scenes.hooks import HookRegistry
from dotter.scenes.materializer import SceneMaterializer

DEMO_SCREENPLAY = """
## Ancient Ruins --- start
Alice: {voice:alice_01.ogg} Welcome, {player_name}! Look at these [b]mysterious ruins[/b].
- The stone pillars date back thousands of years.
/ Let us proceed with [i]utmost caution[/i].

The wind howls through the weathered archways.
Ancient dust stirs across the courtyard.

~ inspect_ruins

Bob: I've detected an entrance to the underground chamber!
>> puzzle_chamber

Alice: Exceptional work, {player_name}! The inner sanctum is now accessible.
? Venture into the ancient sanctum (sanctum)
? Return to base camp (camp)

## Puzzle Chamber --- puzzle_chamber
Bob: The door is locked with ancient glyphs.
- Aligning the celestial rings now...
A resonant mechanical chime resonates through the stone walls.
~ solve_puzzle
Bob: The ancient seals have opened!
<<

## Ancient Sanctum --- sanctum
The chamber radiates an intense blue luminescence.
Alice: Look at the crystal hovering in the center.
/ This discovery will rewrite our history.
Bob: We must document everything before we depart.
> conclusion

## Base Camp --- camp
You decide discretion is the better part of valor and retreat to camp.
> conclusion

## Conclusion --- conclusion
The expedition reaches its milestone.
"""

DEMO_BG_COLORS: dict[str, tuple[int, int, int]] = {
    "bg_ruins": (35, 45, 60),
    "bg_altar": (70, 30, 45),
    "bg_sanctum": (20, 50, 75),
}


def build_demo_engine(screenplay_text: str | None = None) -> Engine:
    """Construct an initialized Engine loaded with the demo scene and companion hooks."""
    text = screenplay_text if screenplay_text is not None else DEMO_SCREENPLAY
    parser = ScreenplayParser()
    items = parser.parse(text)
    materializer = SceneMaterializer("demo")
    scene = materializer.materialize(items)

    hooks = HookRegistry()

    hooks.register_on_entry(
        "start",
        lambda c: (
            c.background("bg_ruins", transition=TransitionType.DISSOLVE, duration=1.5),
            c.music("theme_ancient.ogg", loop=True),
            c.ambience("wind.ogg", loop=True),
        ),
    )

    hooks.register_on_exit(
        "start",
        lambda c: c.hide("alice"),
    )

    hooks.register_hook(
        "inspect_ruins",
        lambda c: (
            c.show(
                "alice",
                face="curious",
                outfit="adventurer",
                at=SpritePosition.LEFT,
                z_order=1,
            ),
            c.set("inspected_ruins", True),
            c.sfx("discover.ogg"),
        ),
    )

    hooks.register_on_entry(
        "puzzle_chamber",
        lambda c: (
            c.music("theme_puzzle.ogg", loop=True, fade_in=2.0),
            c.show("bob", face="thinking", at=SpritePosition.RIGHT, z_order=0),
            c.show(
                "alice",
                face="curious",
                outfit="adventurer",
                at=SpritePosition.LEFT,
                z_order=1,
            ),
        ),
    )

    hooks.register_hook(
        "solve_puzzle",
        lambda c: (
            c.set("puzzle_solved", True),
            c.sfx("puzzle_chime.ogg"),
        ),
    )

    hooks.register_on_entry(
        "sanctum",
        lambda c: (
            c.background("bg_sanctum", transition=TransitionType.FADE_BLACK, duration=1.0),
            c.show(
                "alice",
                face="amazed",
                outfit="adventurer",
                at=SpritePosition.CENTER,
                z_order=2,
            ),
        ),
    )

    state = GameState()
    state.set_variable("player_name", "Explorer")
    state.chapter_title = "Demo Chapter: The Ancient Ruins"

    return Engine(scene=scene, state=state, hooks=hooks, headless=True)


def run_demo(scene_path: Path | None = None, *, headless: bool = False) -> int:
    """Run screenplay playback either in windowed graphical mode or headless mode."""
    screenplay_text: str | None = None
    if scene_path is not None:
        screenplay_text = scene_path.read_text(encoding="utf-8")

    engine = build_demo_engine(screenplay_text)

    if not headless:
        from dotter.runtime.config import WindowConfig
        from dotter.runtime.window import launch_window

        config = WindowConfig(
            caption="Dotter Engine Demo: The Ancient Ruins",
            bg_colors=DEMO_BG_COLORS,
        )
        return launch_window(engine, config=config)

    # Headless mode for automated verification
    while not engine.is_finished:
        if engine.is_waiting_for_choice:
            engine.choose(0)
        else:
            engine.advance()

    return 0
