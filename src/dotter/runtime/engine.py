"""Engine coordinator managing narrative execution, state, and command dispatch."""

from dotter.core.commands import (
    AmbienceCommand,
    BackgroundCommand,
    HideCommand,
    MusicCommand,
    SetVarCommand,
    ShowCommand,
    StagingCommand,
    VoiceCommand,
)
from dotter.core.nodes import SceneIR, SceneNode
from dotter.core.state import CharacterSpriteState, GameState
from dotter.inprose.hooks import HookRegistry
from dotter.runtime.cursor import SceneCursor


class Engine:
    """Coordinates scene execution, in-place state mutation, and subsystem dispatch."""

    def __init__(
        self,
        scene: SceneIR,
        state: GameState | None = None,
        hooks: HookRegistry | None = None,
        *,
        headless: bool = True,
    ) -> None:
        self._state = state if state is not None else GameState()
        self._hooks = hooks if hooks is not None else HookRegistry()
        self._scene = scene
        self._headless = headless
        self._cursor = SceneCursor(self._scene, self._state, self._hooks)
        self._dispatched_commands: list[StagingCommand] = []

    @property
    def state(self) -> GameState:
        """The canonical GameState container."""
        return self._state

    @property
    def current_node(self) -> SceneNode | None:
        """Currently active player beat."""
        return self._cursor.current_node

    @property
    def is_waiting_for_choice(self) -> bool:
        """True if paused waiting for player decision."""
        return self._cursor.is_waiting_for_choice

    @property
    def is_finished(self) -> bool:
        """True if the scene has reached terminal completion."""
        return self._cursor.current_node is None and self._state.cursor_position is None

    @property
    def dispatched_commands(self) -> tuple[StagingCommand, ...]:
        """Sequence of commands dispatched during execution."""
        return tuple(self._dispatched_commands)

    def dispatch_command(self, cmd: StagingCommand) -> None:
        """Apply a staging command in-place to GameState and notify active sinks."""
        self._dispatched_commands.append(cmd)
        staging = self._state.staging

        match cmd:
            case ShowCommand(character=c, face=f, outfit=o, at=pos, z_order=z):
                staging.sprites[c] = CharacterSpriteState(
                    character=c, face=f, outfit=o, position=pos, z_order=z
                )
            case HideCommand(character=c):
                staging.sprites.pop(c, None)
            case BackgroundCommand(background=bg):
                staging.background = bg
            case MusicCommand(track=trk):
                staging.current_bgm = trk
            case AmbienceCommand(track=amb):
                staging.current_ambience = amb
            case VoiceCommand(clip=v):
                staging.current_voice = v
            case SetVarCommand(name=n, value=v):
                self._state.set_variable(n, v)

    def _flush_cursor_commands(self) -> None:
        for cmd in self._cursor.emitted_commands:
            self.dispatch_command(cmd)
        self._cursor.clear_emitted_commands()

    def advance(self) -> SceneNode | None:
        """Advance narrative progression to the next player beat."""
        node = self._cursor.advance()
        self._flush_cursor_commands()
        return node

    def choose(self, index: int) -> SceneNode | None:
        """Commit player choice and resume progression."""
        node = self._cursor.choose(index)
        self._flush_cursor_commands()
        return node
