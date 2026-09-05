"""Intermediate Representation (IR) node definitions and Scene graph container."""

from dataclasses import dataclass, field

from dotter.core.types import NodeId


@dataclass(frozen=True, slots=True)
class ChoiceOption:
    """A single choice branch selectable by the player."""

    text: str
    target: str


@dataclass(frozen=True, slots=True)
class LabelNode:
    """A named section boundary and jump target."""

    node_id: NodeId
    name: str
    display_name: str


@dataclass(frozen=True, slots=True)
class DialogueNode:
    """Spoken character dialogue with an optional voice clip."""

    node_id: NodeId
    speaker: str
    text: str
    voice: str | None = None


@dataclass(frozen=True, slots=True)
class AppendNode:
    """Text appended to the active dialogue box as a subsequent beat ('-')."""

    node_id: NodeId
    text: str


@dataclass(frozen=True, slots=True)
class FreshBoxNode:
    """A new dialogue box keeping the active speaker ('/')."""

    node_id: NodeId
    text: str


@dataclass(frozen=True, slots=True)
class NarrationNode:
    """Speakerless narrative prose."""

    node_id: NodeId
    text: str


@dataclass(frozen=True, slots=True)
class ChoiceSetNode:
    """A set of branching decision choices."""

    node_id: NodeId
    options: tuple[ChoiceOption, ...]


@dataclass(frozen=True, slots=True)
class JumpNode:
    """Unconditional jump to a target label ('>')."""

    node_id: NodeId
    target: str


@dataclass(frozen=True, slots=True)
class CallNode:
    """Subroutine call pushing current position to call stack ('>>')."""

    node_id: NodeId
    target: str


@dataclass(frozen=True, slots=True)
class ReturnNode:
    """Subroutine return popping return address from call stack ('<<')."""

    node_id: NodeId


@dataclass(frozen=True, slots=True)
class HookNode:
    """Handoff point to a companion Python hook ('~')."""

    node_id: NodeId
    hook_name: str


type SceneNode = (
    LabelNode
    | DialogueNode
    | AppendNode
    | FreshBoxNode
    | NarrationNode
    | ChoiceSetNode
    | JumpNode
    | CallNode
    | ReturnNode
    | HookNode
)


@dataclass(frozen=True, slots=True)
class SceneIR:
    """Immutable compiled representation of a narrative scene."""

    scene_name: str
    entry_node_id: NodeId
    nodes: dict[NodeId, SceneNode] = field(default_factory=dict)
    labels: dict[str, NodeId] = field(default_factory=dict)
    edges: dict[NodeId, tuple[NodeId, ...]] = field(default_factory=dict)

    def get_node(self, node_id: NodeId) -> SceneNode:
        """Retrieve a node by its identifier, raising KeyError if missing."""
        if node_id not in self.nodes:
            raise KeyError(f"Node '{node_id}' not found in scene '{self.scene_name}'")
        return self.nodes[node_id]

    def get_next_node_ids(self, node_id: NodeId) -> tuple[NodeId, ...]:
        """Retrieve the target node identifiers linked from node_id."""
        return self.edges.get(node_id, ())
