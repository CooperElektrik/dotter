#!/usr/bin/env python3
"""Generate a DOT dependency graph of the Dotter engine modules."""

import ast
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src" / "dotter"


def _resolve_import(imp: ast.Import) -> list[tuple[str, str]]:
    """Return (local_name, full_module_path) pairs for a plain import."""
    pairs: list[tuple[str, str]] = []
    for alias in imp.names:
        local = alias.asname or alias.name
        pairs.append((local, alias.name))
    return pairs


def _resolve_import_from(imp: ast.ImportFrom) -> list[tuple[str, str]]:
    """Return (local_name, full_module_path) pairs for a from...import."""
    if imp.module is None:
        return []
    pairs: list[tuple[str, str]] = []
    for alias in imp.names:
        local = alias.asname or alias.name
        pairs.append((local, f"{imp.module}.{alias.name}"))
    return pairs


def _local_imports(tree: ast.Module) -> list[tuple[str, str]]:
    """Extract all (local_name, source_module) pairs from an AST."""
    pairs: list[tuple[str, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            pairs.extend(_resolve_import(node))
        elif isinstance(node, ast.ImportFrom):
            pairs.extend(_resolve_import_from(node))
    return pairs


def _discover_modules() -> dict[str, Path]:
    """Walk src/dotter and map dotted module names to file paths."""
    modules: dict[str, Path] = {}
    for py_path in sorted(SRC_DIR.rglob("*.py")):
        if py_path.name == "__init__.py":
            continue
        rel = py_path.relative_to(SRC_DIR).with_suffix("")
        dotted = ".".join(rel.parts)
        modules[dotted] = py_path
    return modules


def _source_mapping(module_map: dict[str, Path]) -> dict[str, str]:
    """Map each imported module name to the local file that defines it, if any."""
    mapping: dict[str, str] = {}
    for dotted, path in module_map.items():
        mapping[dotted] = str(path.relative_to(PROJECT_ROOT))
        # Bare package name -> __init__.py
        top = dotted.split(".", 1)[0]
        init_path = SRC_DIR / top / "__init__.py"
        if init_path.exists():
            mapping[top] = str(init_path.relative_to(PROJECT_ROOT))
    return mapping


def _resolve_source_target(
    imported_name: str,
    module_map: dict[str, Path],
    source_map: dict[str, str],
) -> str | None:
    """Map an imported dotted name to a file path in our source tree, or None.

    All Imports inside the dotter package use the ``dotter.`` prefix (e.g.
    ``dotter.core.types.NodeId``).  The ``source_map`` keys omit that prefix
    (e.g. ``core.types``), so we strip it before lookup.
    """
    # Strip the leading ``dotter.`` package prefix if present.
    if imported_name.startswith("dotter."):
        imported_name = imported_name[7:]

    # Case 1: exact module match (e.g. ``core.types``)
    if imported_name in source_map:
        return source_map[imported_name]

    # Case 2: ``from module import name`` -> resolve the parent module
    parts = imported_name.rsplit(".", 1)
    if len(parts) == 2:
        parent, _name = parts
        if parent in source_map:
            return source_map[parent]

    return None


def _build_edges(
    module_map: dict[str, Path],
    source_map: dict[str, str],
) -> list[tuple[str, str]]:
    """Return (source_file, target_file) edges for internal imports only."""
    edges: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()

    for dotted, path in sorted(module_map.items()):
        source_file = str(path.relative_to(PROJECT_ROOT))
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for _local, imported in _local_imports(tree):
            target = _resolve_source_target(imported, module_map, source_map)
            if target is None:
                continue
            edge = (source_file, target)
            if edge not in seen and source_file != target:
                seen.add(edge)
                edges.append(edge)

    return edges


def _module_label(path: str) -> str:
    """Human-readable module name for a relative source file path.

    E.g. "src/dotter/runtime/engine.py" -> "runtime.engine"
    """
    rel = Path(path)
    stem = rel.with_suffix("")
    parts = list(stem.parts)

    # Strip leading "src" and "dotter" noise.
    while parts and parts[0] in ("src", "dotter"):
        parts = parts[1:]

    # Top-level module: ``demo.py`` -> ``demo``, ``__main__.py`` -> ``dotter.__main__``
    if len(parts) == 1:
        name = stem.name
        if name == "__main__":
            return "dotter.__main__"
        return name

    return ".".join(parts)


def _node_id(path: str) -> str:
    """DOT-safe node identifier derived from a relative file path."""
    return str(Path(path).stem).replace("-", "_")


def generate_dot(edges: list[tuple[str, str]]) -> str:
    """Build the DOT source text from a list of (source, target) edges."""
    lines = [
        "digraph EngineDependencies {",
        "  rankdir=LR;",
        "  node [shape=box, style=filled, fillcolor=\"#e8e8e8\", fontname=\"Helvetica\"];",
        "  edge [color=\"#555555\", arrowsize=0.8];",
        "",
    ]

    node_labels: dict[str, str] = {}
    for src, tgt in edges:
        src_id = _node_id(src)
        tgt_id = _node_id(tgt)
        if src_id not in node_labels:
            node_labels[src_id] = _module_label(src)
        if tgt_id not in node_labels:
            node_labels[tgt_id] = _module_label(tgt)
        lines.append(f'  {src_id} -> {tgt_id};')

    lines.append("")
    for nid in sorted(node_labels):
        lines.append(f'  {nid} [label="{node_labels[nid]}"];')

    lines.append("}")
    return "\n".join(lines)


def main() -> None:
    module_map = _discover_modules()
    source_map = _source_mapping(module_map)
    edges = _build_edges(module_map, source_map)
    dot = generate_dot(edges)

    out_path = PROJECT_ROOT / "engine_dependencies.dot"
    out_path.write_text(dot, encoding="utf-8")
    print(f"Wrote {out_path} ({len(edges)} edges across {len(module_map)} modules)")

    # Also print to stdout so it can be piped
    print(dot)


if __name__ == "__main__":
    main()
