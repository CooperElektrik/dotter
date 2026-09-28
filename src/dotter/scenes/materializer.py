"""Materializes parsed inProse AST items into an immutable SceneIR graph."""

from inprose import (
    ParsedAppend,
    ParsedCall,
    ParsedChoiceSet,
    ParsedDialogue,
    ParsedFreshBox,
    ParsedHook,
    ParsedItem,
    ParsedJump,
    ParsedLabel,
    ParsedNarration,
    ParsedReturn,
    validate,
)

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
    SceneNode,
)
from dotter.core.types import NodeId


class CompilationError(Exception):
    """Raised when scene graph cannot be validated or materialized."""


def _convert_prose_node(item: ParsedItem, node_id: NodeId) -> SceneNode | None:
    match item:
        case ParsedLabel(name=n, display_name=d):
            return LabelNode(node_id=node_id, name=n, display_name=d)
        case ParsedDialogue(speaker=s, text=t, voice=v, emotion=e):
            return DialogueNode(node_id=node_id, speaker=s, text=t, voice=v, emotion=e)
        case ParsedAppend(text=t):
            return AppendNode(node_id=node_id, text=t)
        case ParsedFreshBox(text=t):
            return FreshBoxNode(node_id=node_id, text=t)
        case ParsedNarration(text=t):
            return NarrationNode(node_id=node_id, text=t)
        case _:
            return None


def _convert_flow_node(item: ParsedItem, node_id: NodeId) -> SceneNode:
    match item:
        case ParsedChoiceSet(options=opts):
            co_list = tuple(ChoiceOption(text=o.text, target=o.target) for o in opts)
            return ChoiceSetNode(node_id=node_id, options=co_list)
        case ParsedJump(target=t):
            return JumpNode(node_id=node_id, target=t)
        case ParsedCall(target=t):
            return CallNode(node_id=node_id, target=t)
        case ParsedReturn():
            return ReturnNode(node_id=node_id)
        case ParsedHook(hook_name=h):
            return HookNode(node_id=node_id, hook_name=h)
        case _:
            raise ValueError(f"Unhandled item type: {type(item)}")


class SceneMaterializer:
    """Lowers parsed items into an immutable, linked SceneIR graph."""

    def __init__(self, scene_name: str) -> None:
        self.scene_name = scene_name
        self._nodes: dict[NodeId, SceneNode] = {}
        self._labels: dict[str, NodeId] = {}
        self._edges: dict[NodeId, list[NodeId]] = {}

    def _convert_item(self, item: ParsedItem, node_id: NodeId) -> SceneNode:
        prose_node = _convert_prose_node(item, node_id)
        if prose_node is not None:
            return prose_node
        return _convert_flow_node(item, node_id)

    def _build_nodes(self, items: list[ParsedItem]) -> list[tuple[NodeId, SceneNode]]:
        node_pairs: list[tuple[NodeId, SceneNode]] = []
        current_label = "start"
        ordinal = 0

        for item in items:
            if isinstance(item, ParsedLabel):
                current_label = item.name
                ordinal = 0
                node_id = f"{self.scene_name}.{current_label}.{ordinal}"
                self._labels[current_label] = node_id
            else:
                node_id = f"{self.scene_name}.{current_label}.{ordinal}"

            node = self._convert_item(item, node_id)
            node_pairs.append((node_id, node))
            self._nodes[node_id] = node
            ordinal += 1

        return node_pairs

    def _link_edges(self, node_pairs: list[tuple[NodeId, SceneNode]]) -> None:
        total = len(node_pairs)
        for i, (node_id, node) in enumerate(node_pairs):
            if isinstance(node, JumpNode):
                target_id = self._labels.get(node.target)
                self._edges[node_id] = [target_id] if target_id else []
            elif isinstance(node, CallNode):
                target_id = self._labels.get(node.target)
                self._edges[node_id] = [target_id] if target_id else []
            elif isinstance(node, ChoiceSetNode):
                choice_targets: list[NodeId] = []
                for opt in node.options:
                    t_id = self._labels.get(opt.target)
                    if t_id:
                        choice_targets.append(t_id)
                self._edges[node_id] = choice_targets
            elif isinstance(node, ReturnNode):
                self._edges[node_id] = []
            elif i + 1 < total:
                self._edges[node_id] = [node_pairs[i + 1][0]]
            else:
                self._edges[node_id] = []

    def materialize(self, items: list[ParsedItem]) -> SceneIR:
        """Compile parsed items into an immutable SceneIR."""
        self._nodes.clear()
        self._labels.clear()
        self._edges.clear()

        effective_items = list(items)
        if not effective_items or not isinstance(effective_items[0], ParsedLabel):
            effective_items.insert(
                0, ParsedLabel(name="start", display_name="Start", line_number=1)
            )

        result = validate(effective_items)
        if not result.is_valid:
            first = result.errors[0]
            raise CompilationError(f"Line {first.line_number}: {first.message}")

        node_pairs = self._build_nodes(effective_items)
        self._link_edges(node_pairs)

        entry_node_id = node_pairs[0][0]
        frozen_edges = {nid: tuple(targets) for nid, targets in self._edges.items()}

        return SceneIR(
            scene_name=self.scene_name,
            entry_node_id=entry_node_id,
            nodes=dict(self._nodes),
            labels=dict(self._labels),
            edges=frozen_edges,
        )
