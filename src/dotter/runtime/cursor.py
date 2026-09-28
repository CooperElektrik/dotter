"""Cursor walking the SceneIR graph and driving narrative execution."""

from dotter.core.commands import GotoCommand, StagingCommand
from dotter.core.nodes import (
    CallNode,
    ChoiceSetNode,
    HookNode,
    JumpNode,
    LabelNode,
    ReturnNode,
    SceneIR,
    SceneNode,
)
from dotter.core.state import GameState
from dotter.core.types import NodeId
from dotter.scenes.context import HookContext
from dotter.scenes.hooks import HookRegistry


class CursorError(RuntimeError):
    """Raised on invalid cursor navigation or state."""


class SceneCursor:
    """Walks a SceneIR graph, evaluating control flow and stopping at player beats."""

    def __init__(
        self,
        scene: SceneIR,
        state: GameState,
        hooks: HookRegistry | None = None,
    ) -> None:
        self._scene = scene
        self._state = state
        self._hooks = hooks or HookRegistry()
        self._current_node: SceneNode | None = None
        self._current_label: str | None = None
        self._emitted_commands: list[StagingCommand] = []

    @property
    def current_node(self) -> SceneNode | None:
        """Currently active node."""
        return self._current_node

    @property
    def is_waiting_for_choice(self) -> bool:
        """True if the cursor is halted at a choice menu."""
        return isinstance(self._current_node, ChoiceSetNode)

    @property
    def emitted_commands(self) -> list[StagingCommand]:
        """Commands emitted during transient transitions."""
        return self._emitted_commands

    def clear_emitted_commands(self) -> None:
        """Clear transient commands buffer."""
        self._emitted_commands.clear()

    def _fire_label_transition(self, new_label: str) -> None:
        if self._current_label and self._current_label != new_label:
            ctx = HookContext(self._state)
            self._hooks.execute_on_exit(self._current_label, ctx)
            self._emitted_commands.extend(ctx.commands)

        self._current_label = new_label
        ctx = HookContext(self._state)
        self._hooks.execute_on_entry(new_label, ctx)
        self._emitted_commands.extend(ctx.commands)

    def _handle_hook_node(self, node: HookNode) -> NodeId | None:
        ctx = HookContext(self._state)
        self._hooks.execute_hook(node.hook_name, ctx)
        self._emitted_commands.extend(ctx.commands)

        for cmd in ctx.commands:
            if isinstance(cmd, GotoCommand):
                return self._scene.labels.get(cmd.label)

        next_ids = self._scene.get_next_node_ids(node.node_id)
        return next_ids[0] if next_ids else None

    def _resolve_transient_step(self, node: SceneNode) -> NodeId | None:
        match node:
            case LabelNode(name=lbl_name):
                self._fire_label_transition(lbl_name)
                next_ids = self._scene.get_next_node_ids(node.node_id)
                return next_ids[0] if next_ids else None
            case JumpNode(target=t):
                return self._scene.labels.get(t)
            case CallNode(node_id=nid, target=t):
                node_keys = list(self._scene.nodes.keys())
                if nid in self._scene.nodes:
                    idx = node_keys.index(nid)
                    if idx + 1 < len(node_keys):
                        self._state.call_stack.append(node_keys[idx + 1])
                return self._scene.labels.get(t)
            case ReturnNode():
                if not self._state.call_stack:
                    return None
                return self._state.call_stack.pop()
            case HookNode():
                return self._handle_hook_node(node)
            case _:
                return None

    def _step_to_interactive(self, start_id: NodeId | None) -> SceneNode | None:
        curr_id = start_id
        while curr_id is not None:
            node = self._scene.get_node(curr_id)
            self._state.cursor_position = curr_id

            if isinstance(node, (LabelNode, JumpNode, CallNode, ReturnNode, HookNode)):
                curr_id = self._resolve_transient_step(node)
                continue

            self._current_node = node
            return node

        self._current_node = None
        self._state.cursor_position = None
        return None

    def advance(self) -> SceneNode | None:
        """Step to the next interactive player beat (dialogue, narration, choice)."""
        if self.is_waiting_for_choice:
            raise CursorError("Cannot advance: awaiting player choice")

        if self._current_node is None:
            return self._step_to_interactive(self._scene.entry_node_id)

        next_ids = self._scene.get_next_node_ids(self._current_node.node_id)
        next_id = next_ids[0] if next_ids else None
        return self._step_to_interactive(next_id)

    def choose(self, index: int) -> SceneNode | None:
        """Select a branch from the active choice set and step to next beat."""
        if not isinstance(self._current_node, ChoiceSetNode):
            raise CursorError("Cannot choose: not currently at a choice point")

        options = self._current_node.options
        if index < 0 or index >= len(options):
            raise CursorError(f"Choice index {index} out of range (0..{len(options) - 1})")

        target_label = options[index].target
        target_id = self._scene.labels.get(target_label)
        if target_id is None:
            raise CursorError(f"Choice target label '{target_label}' not found")

        return self._step_to_interactive(target_id)
