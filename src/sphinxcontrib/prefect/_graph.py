"""Parse, classify, and style Mermaid graphs returned by Prefect."""

from __future__ import annotations

import importlib
import re
import sys
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Literal

from sphinxcontrib.prefect._import import flow_entrypoint

if TYPE_CHECKING:
    from prefect import Flow, Task

    NodeObject = Flow | Task

NodeKind = Literal["main", "subflow", "task", "unknown", "ambiguous"]

_NODE = re.compile(
    r'^\s*(?P<node_id>[^\s\[\]]+)\s*\[\s*"(?P<label>(?:[^"\\]|\\.)*)"\s*\]\s*$'
)
_EDGE = re.compile(r"^\s*(?P<source>[^\s\[\]]+)\s*-->\s*(?P<target>[^\s\[\]]+)\s*$")
_DUPLICATE_SUFFIX = re.compile(r"-\d+$")
_MAIN_NODE_ID = "prefect_main_flow"

_CLASS_DEFINITIONS = (
    ("prefectMain", "fill:#4f46e5,stroke:#312e81,color:#ffffff"),
    ("prefectSubflow", "fill:#0ea5e9,stroke:#075985,color:#ffffff"),
    ("prefectTask", "fill:#10b981,stroke:#065f46,color:#ffffff"),
    ("prefectUnknown", "fill:#f59e0b,stroke:#92400e,color:#1f2937"),
)
_KIND_CLASSES: dict[str, str] = {
    "main": "prefectMain",
    "subflow": "prefectSubflow",
    "task": "prefectTask",
    "unknown": "prefectUnknown",
    "ambiguous": "prefectUnknown",
}


@dataclass(frozen=True)
class GraphNode:
    """A Mermaid node, its label, and the Prefect object it matched."""

    node_id: str
    label: str
    name: str
    kind: NodeKind = "unknown"
    obj: NodeObject | None = None


@dataclass(frozen=True)
class GraphEdge:
    """A directed edge between two Mermaid node ids."""

    source: str
    target: str


@dataclass(frozen=True)
class ParsedGraph:
    """The nodes and edges parsed from a Prefect Mermaid graph."""

    header: str
    nodes: tuple[GraphNode, ...] = ()
    edges: tuple[GraphEdge, ...] = ()
    extra_lines: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    ambiguous: tuple[str, ...] = ()

    @property
    def matched_nodes(self) -> tuple[GraphNode, ...]:
        """Return nodes matched to a main flow, subflow, or task."""
        return tuple(
            node for node in self.nodes if node.kind in {"main", "subflow", "task"}
        )

    @property
    def ambiguous_nodes(self) -> tuple[GraphNode, ...]:
        """Return nodes whose names match multiple Flow or Task objects."""
        return tuple(node for node in self.nodes if node.kind == "ambiguous")

    @property
    def unknown_nodes(self) -> tuple[GraphNode, ...]:
        """Return nodes that matched no object."""
        return tuple(node for node in self.nodes if node.kind == "unknown")


def strip_duplicate_suffix(label: str) -> str:
    """Strip Prefect's ``-0``, ``-1``, ... duplicate-node suffix."""
    return _DUPLICATE_SUFFIX.sub("", label)


def parse_mermaid(code: str) -> ParsedGraph:
    """Parse ``generate_mermaid_graph()`` output into nodes and edges."""
    lines = [line for line in code.splitlines() if line.strip()]
    header = lines[0].strip() if lines else "flowchart TD"
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []
    extra_lines: list[str] = []

    for line in lines[1:]:
        if match := _NODE.match(line):
            label = match.group("label")
            nodes.append(
                GraphNode(
                    node_id=match.group("node_id"),
                    label=label,
                    name=strip_duplicate_suffix(label),
                )
            )
        elif match := _EDGE.match(line):
            edges.append(
                GraphEdge(
                    source=match.group("source"),
                    target=match.group("target"),
                )
            )
        else:
            # Preserve syntax this version does not interpret (for example
            # subgraphs or labelled edges) instead of truncating the diagram.
            extra_lines.append(line.strip())

    return ParsedGraph(
        header=header,
        nodes=tuple(nodes),
        edges=tuple(edges),
        extra_lines=tuple(extra_lines),
    )


def classify_nodes(flow: Flow, graph: ParsedGraph) -> ParsedGraph:
    """Classify graph nodes as the main flow, a subflow, task, or unknown.

    Matched nodes retain the module-level ``Flow`` or ``Task`` object in
    :attr:`GraphNode.obj`. Names shared by multiple objects are ambiguous and
    stay unlinked.
    """
    objects, warnings = _module_objects(flow)
    main_entrypoint = flow_entrypoint(flow)
    nodes: list[GraphNode] = []
    ambiguous: list[str] = []
    for node in graph.nodes:
        matches = objects.get(node.name, ())
        if len(matches) == 1:
            matched = matches[0]
            nodes.append(
                replace(
                    node,
                    kind=_node_kind(matched, main_entrypoint),
                    obj=matched,
                )
            )
        elif matches:
            ambiguous.append(node.name)
            nodes.append(replace(node, kind="ambiguous"))
        elif node.name == flow.name:
            # Prefect normally omits the main flow; handle a future graph that
            # includes it even when the module could not be inspected.
            nodes.append(replace(node, kind="main", obj=flow))
        else:
            nodes.append(replace(node, kind="unknown"))

    ambiguous_names = tuple(dict.fromkeys(ambiguous))
    ambiguous_warnings = tuple(
        f"Graph node {name!r} in {flow.fn.__module__!r} matches multiple Flow "
        "or Task objects; it is left unlinked."
        for name in ambiguous_names
    )
    return replace(
        graph,
        nodes=tuple(nodes),
        ambiguous=ambiguous_names,
        warnings=tuple(
            dict.fromkeys((*graph.warnings, *warnings, *ambiguous_warnings))
        ),
    )


def build_diagram(
    flow: Flow, graph: ParsedGraph, *, preclassified: bool = False
) -> str:
    """Return a styled Mermaid diagram with a main-flow node.

    Pass ``preclassified=True`` when *graph* already came from
    :func:`classify_nodes` to avoid scanning the flow module twice.
    """
    classified = graph if preclassified else classify_nodes(flow, graph)
    nodes = classified.nodes
    lines = [classified.header]
    lines.extend(f'    {node.node_id}["{node.label}"]' for node in nodes)
    lines.extend(f"    {edge.source} --> {edge.target}" for edge in classified.edges)
    lines.extend(classified.extra_lines)

    main_id: str | None = None
    if not any(node.kind == "main" for node in nodes):
        main_id = _unique_main_id(nodes)
        lines.append(f'    {main_id}["{_escape_label(flow.name or "flow")}"]')
        for root in _root_node_ids(classified):
            lines.append(f"    {main_id} --> {root}")

    lines.extend(f"    classDef {name} {style}" for name, style in _CLASS_DEFINITIONS)
    lines.extend(
        f"    class {node.node_id} {_KIND_CLASSES[node.kind]}" for node in nodes
    )
    if main_id is not None:
        lines.append(f"    class {main_id} prefectMain")
    return "\n".join(lines)


def _module_objects(
    flow: Flow,
) -> tuple[dict[str, tuple[NodeObject, ...]], tuple[str, ...]]:
    """Map module-level flow and task names to their objects."""
    # Importing Prefect is deferred until a DAG is classified.
    from prefect import Flow, Task

    module = sys.modules.get(flow.fn.__module__)
    if module is None:
        try:
            module = importlib.import_module(flow.fn.__module__)
        except Exception as exc:
            warning = (
                f"Could not inspect module {flow.fn.__module__!r} for graph "
                f"nodes: {exc}. Matching graph nodes to flow and task objects "
                "will be skipped."
            )
            return {}, (warning,)

    objects: dict[str, list[NodeObject]] = {}
    seen: dict[str, set[int]] = {}
    for obj in vars(module).values():
        if not isinstance(obj, (Flow, Task)):
            continue
        if id(obj) in seen.setdefault(obj.name, set()):
            continue
        seen[obj.name].add(id(obj))
        objects.setdefault(obj.name, []).append(obj)

    return {name: tuple(values) for name, values in objects.items()}, ()


def _node_kind(obj: NodeObject, main_entrypoint: str) -> NodeKind:
    """Return the graph node kind for a matched Flow or Task object."""
    from prefect import Flow

    if isinstance(obj, Flow):
        return "main" if flow_entrypoint(obj) == main_entrypoint else "subflow"
    return "task"


def _unique_main_id(nodes: tuple[GraphNode, ...]) -> str:
    """Return a main-flow node id that does not collide with an existing node."""
    used = {node.node_id for node in nodes}
    main_id = _MAIN_NODE_ID
    while main_id in used:
        main_id = f"{main_id}_node"
    return main_id


def _root_node_ids(graph: ParsedGraph) -> tuple[str, ...]:
    """Return node ids without incoming edges, preserving graph order."""
    targets = {edge.target for edge in graph.edges}
    return tuple(node.node_id for node in graph.nodes if node.node_id not in targets)


def _escape_label(label: str) -> str:
    """Escape a label inserted into Mermaid's quoted node syntax."""
    return label.replace("\\", "\\\\").replace('"', "&quot;")
