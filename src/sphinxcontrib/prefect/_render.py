"""Shared helpers for building directive doctrees."""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from docutils import nodes
from sphinx import addnodes

from sphinxcontrib.prefect._dag import render_flow_graph
from sphinxcontrib.prefect._description import (
    read_description_file,
    render_external_description,
    render_rst_description,
    resolve_flow_description,
)
from sphinxcontrib.prefect._errors import source_path, with_sources
from sphinxcontrib.prefect._graph import GraphNode, NodeKind, ParsedGraph
from sphinxcontrib.prefect._import import callable_entrypoint, flow_entrypoint
from sphinxcontrib.prefect._markers import parse_mainflow_markers
from sphinxcontrib.prefect._models import (
    ModelCollection,
    collect_callable_models,
    render_model_sections,
)
from sphinxcontrib.prefect._params import render_parameter_table

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable
    from typing import Any

    from sphinx.util.docutils import SphinxDirective

    from prefect import Flow, Task
    from sphinxcontrib.prefect._markers import MarkerResult


@dataclass(frozen=True)
class RenderDiagnostics:
    """Diagnostics collected while assembling a generated section."""

    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()


@dataclass(frozen=True)
class RenderResult:
    """A rendered section plus diagnostics for the directive to report."""

    section: nodes.section
    diagnostics: RenderDiagnostics = field(default_factory=RenderDiagnostics)


def make_section(
    directive: SphinxDirective,
    title: str,
    *,
    node_id: str | None = None,
    cross_reference: bool = False,
) -> nodes.section:
    """Create a section with *title*, optionally assigning a stable id.

    When *cross_reference* is true, the section becomes a standard-domain
    label unless another document already registered that label. Duplicate
    ids within one document receive a numeric suffix.
    """
    section = nodes.section()
    document = directive.state.document
    base_id = node_id if node_id is not None else nodes.make_id(title)
    section_id = _unique_section_id(document, base_id)
    section["ids"].append(section_id)
    if cross_reference and section_id == base_id:
        _register_label(directive, section, base_id)
    directive.set_source_info(section)
    section += nodes.title(text=title)
    return section


def _unique_section_id(document: nodes.document, base_id: str) -> str:
    """Return an id that no generated section or parsed target uses yet."""
    used = getattr(document, "_prefect_section_ids", None)
    if used is None:
        used = set()
        document._prefect_section_ids = used
    candidate = base_id
    index = 2
    while candidate in used or candidate in document.ids:
        candidate = f"{base_id}-{index}"
        index += 1
    used.add(candidate)
    return candidate


def _register_label(
    directive: SphinxDirective,
    section: nodes.section,
    label: str,
) -> None:
    """Register *label* for *section* without emitting duplicate warnings."""
    document = directive.state.document
    if label in document.nametypes:
        return
    if label in directive.env.domains.standard_domain.labels:
        return
    section["names"].append(label)
    document.note_explicit_target(section)


def add_field_list(
    section: nodes.Element,
    fields: Iterable[tuple[str, str]],
) -> nodes.field_list:
    """Append a field list whose values are rendered as literals."""
    field_list = nodes.field_list()
    for name, value in fields:
        field = nodes.field()
        field += nodes.field_name(text=name)
        body = nodes.field_body()
        paragraph = nodes.paragraph()
        paragraph += nodes.literal(text=value)
        body += paragraph
        field += body
        field_list += field
    section += field_list
    return field_list


def render_directive_content(
    directive: SphinxDirective,
    section: nodes.Element,
) -> None:
    """Parse the directive body and append it to *section*."""
    section.extend(directive.parse_content_to_nodes(allow_section_headings=True))


def flow_node_id(flow: Flow) -> str:
    """Return a stable, unique section id for *flow*."""
    return nodes.make_id(f"prefect-flow-{flow_entrypoint(flow)}")


def task_node_id(task: Task) -> str:
    """Return a stable, unique section id for *task*."""
    return nodes.make_id(f"prefect-task-{callable_entrypoint(task.fn)}")


def params_node_id(flow: Flow) -> str:
    """Return a stable, unique section id for *flow*'s parameter section."""
    return nodes.make_id(f"prefect-params-{flow_entrypoint(flow)}")


def dag_node_id(flow: Flow) -> str:
    """Return a stable, unique section id for *flow*'s DAG section."""
    return nodes.make_id(f"prefect-dag-{flow_entrypoint(flow)}")


def render_graph_node_sections(
    directive: SphinxDirective,
    section: nodes.Element,
    graph: ParsedGraph,
) -> RenderDiagnostics:
    """Append subflow, task, and unknown-node sections for a runtime graph."""
    subflows = _unique_nodes(graph.matched_nodes, "subflow")
    tasks = _unique_nodes(graph.matched_nodes, "task")
    warnings: list[str] = []
    errors: list[str] = []

    if subflows:
        subflow_section = make_section(directive, "Subflows")
        _append_link_list(subflow_section, subflows)
        for node in subflows:
            diagnostics = _render_subflow_section(directive, subflow_section, node)
            warnings.extend(diagnostics.warnings)
            errors.extend(diagnostics.errors)
        section += subflow_section

    if tasks:
        task_section = make_section(directive, "Tasks")
        _append_link_list(task_section, tasks)
        for node in tasks:
            diagnostics = _render_task_section(directive, task_section, node)
            warnings.extend(diagnostics.warnings)
            errors.extend(diagnostics.errors)
        section += task_section

    ambiguous = tuple(dict.fromkeys(node.name for node in graph.ambiguous_nodes))
    unknown = tuple(dict.fromkeys(node.name for node in graph.unknown_nodes))
    if ambiguous or unknown:
        unknown_section = make_section(directive, "Unknown nodes")
        explanation = nodes.paragraph(
            text=(
                "These graph nodes could not be resolved to exactly one Flow "
                "or Task in the flow's module, so they are listed without links."
            )
        )
        unknown_section += explanation
        unknown_section += _name_list(
            [(name, "ambiguous name") for name in ambiguous]
            + [(name, "unknown or external") for name in unknown]
        )
        section += unknown_section

    return RenderDiagnostics(tuple(warnings), tuple(errors))


def _unique_nodes(
    nodes_: Iterable[GraphNode],
    kind: NodeKind,
) -> tuple[GraphNode, ...]:
    """Return graph nodes of *kind*, deduplicated by matched object."""
    seen: set[int] = set()
    result: list[GraphNode] = []
    for node in nodes_:
        if node.kind != kind or node.obj is None or id(node.obj) in seen:
            continue
        seen.add(id(node.obj))
        result.append(node)
    return tuple(result)


def _append_link_list(
    section: nodes.Element,
    graph_nodes: Iterable[GraphNode],
) -> None:
    """Append a bullet list linking to each documented related node."""
    bullet_list = nodes.bullet_list()
    for node in graph_nodes:
        item = nodes.list_item()
        paragraph = nodes.paragraph()
        paragraph += _cross_reference(node.name, _node_anchor(node))
        item += paragraph
        bullet_list += item
    section += bullet_list


def _name_list(entries: Iterable[tuple[str, str]]) -> nodes.bullet_list:
    """Return a bullet list of names with an explanation, without links."""
    bullet_list = nodes.bullet_list()
    for name, reason in entries:
        item = nodes.list_item()
        paragraph = nodes.paragraph()
        paragraph += nodes.literal(text=name)
        paragraph += nodes.Text(f" ({reason})")
        item += paragraph
        bullet_list += item
    return bullet_list


def _cross_reference(name: str, target: str) -> addnodes.pending_xref:
    """Return a standard-domain cross-reference to *target*."""
    reference = addnodes.pending_xref(
        "",
        refdomain="std",
        reftype="ref",
        reftarget=target,
        refexplicit=True,
    )
    reference += nodes.Text(name)
    return reference


def _node_anchor(node: GraphNode) -> str:
    """Return the cross-reference label of a matched graph node."""
    if node.kind == "task":
        return task_node_id(node.obj)
    return flow_node_id(node.obj)


def _render_subflow_section(
    directive: SphinxDirective,
    parent: nodes.Element,
    node: GraphNode,
) -> RenderDiagnostics:
    """Append a leaf section documenting a matched subflow."""
    subflow = node.obj
    section = make_section(
        directive,
        subflow.name or type(subflow).__name__,
        node_id=flow_node_id(subflow),
        cross_reference=True,
    )
    add_field_list(
        section,
        [
            ("Entrypoint", flow_entrypoint(subflow)),
            ("Signature", str(inspect.signature(subflow.fn))),
        ],
    )

    markers = parse_mainflow_markers(subflow.fn.__doc__)
    errors = _render_section_body(
        directive,
        section,
        subflow.fn,
        subflow.parameters.model_dump(),
        owner=f"subflow {flow_entrypoint(subflow)!r}",
        description=resolve_flow_description(subflow, markers),
    )
    parent += section
    return RenderDiagnostics(
        warnings=with_sources(markers.warnings, subflow.fn),
        errors=(*with_sources(markers.errors, subflow.fn), *errors),
    )


def _render_task_section(
    directive: SphinxDirective,
    parent: nodes.Element,
    node: GraphNode,
) -> RenderDiagnostics:
    """Append a section documenting a matched task."""
    task = node.obj
    section = make_section(
        directive,
        task.name or type(task).__name__,
        node_id=task_node_id(task),
        cross_reference=True,
    )
    add_field_list(
        section,
        [("Signature", str(inspect.signature(task.fn)))],
    )

    # Importing Prefect is deferred until a task section is rendered.
    from prefect.utilities.callables import parameter_schema

    errors = _render_section_body(
        directive,
        section,
        task.fn,
        parameter_schema(task.fn).model_dump(),
        owner=f"task {task.name!r}",
        description=task.description,
    )
    parent += section
    return RenderDiagnostics(errors=errors)


def _render_section_body(
    directive: SphinxDirective,
    section: nodes.Element,
    fn: Callable[..., Any],
    schema: dict[str, Any],
    *,
    owner: str,
    description: str | None,
    models: ModelCollection | None = None,
) -> tuple[str, ...]:
    """Render description and parameters, returning model diagnostics."""
    note_source_dependency(directive, fn)
    if description:
        render_rst_description(directive, section, description)
    if models is None:
        models = collect_callable_models(fn, owner=owner)
    render_parameter_table(directive, section, fn, schema, models)
    render_model_sections(directive, section, models.models)
    return models.errors


def note_source_dependency(
    directive: SphinxDirective,
    fn: Callable[..., Any],
) -> None:
    """Register a related node's source file as a build dependency."""
    source = source_path(fn)
    if source is not None:
        directive.env.note_dependency(source)


def render_flow_section(
    directive: SphinxDirective,
    flow: Flow,
    markers: MarkerResult | None,
    models: ModelCollection,
    *,
    description_from: str | None = None,
    node_id: str | None = None,
    include_description: bool = True,
    include_dag: bool = False,
    cross_reference: bool = False,
) -> RenderResult:
    """Render a flow section for ``prefect-flow`` or ``prefect-params``."""
    section = make_section(
        directive,
        flow.name or type(flow).__name__,
        node_id=node_id,
        cross_reference=cross_reference,
    )

    fields = [("Entrypoint", flow_entrypoint(flow))]
    if flow.version is not None:
        fields.append(("Version", str(flow.version)))
    fields.append(("Signature", str(inspect.signature(flow.fn))))
    add_field_list(section, fields)

    if include_description:
        if description_from is not None:
            description_file = read_description_file(directive, description_from)
            if description_file is not None:
                render_external_description(directive, section, description_file)
        else:
            if markers is None:
                markers = parse_mainflow_markers(flow.fn.__doc__)
            description = resolve_flow_description(flow, markers)
            if description:
                render_rst_description(directive, section, description)

    _render_section_body(
        directive,
        section,
        flow.fn,
        flow.parameters.model_dump(),
        owner=f"flow {flow_entrypoint(flow)!r}",
        description=None,
        models=models,
    )
    diagnostics = RenderDiagnostics()
    if include_dag:
        graph = render_flow_graph(directive, section, flow)
        if graph is not None:
            diagnostics = render_graph_node_sections(directive, section, graph)

    return RenderResult(section, diagnostics)
