"""Shared helpers for building directive doctrees."""

from __future__ import annotations

import inspect
from typing import TYPE_CHECKING

from docutils import nodes

from sphinxcontrib.prefect._description import (
    read_description_file,
    render_external_description,
    render_rst_description,
    resolve_flow_description,
)
from sphinxcontrib.prefect._import import flow_entrypoint
from sphinxcontrib.prefect._markers import parse_mainflow_markers
from sphinxcontrib.prefect._models import ModelCollection, render_model_sections
from sphinxcontrib.prefect._params import render_parameter_table

if TYPE_CHECKING:
    from collections.abc import Iterable

    from sphinx.util.docutils import SphinxDirective

    from prefect import Flow
    from sphinxcontrib.prefect._markers import MarkerResult


def make_section(
    directive: SphinxDirective,
    title: str,
    *,
    node_id: str | None = None,
) -> nodes.section:
    """Create a section with *title*, optionally assigning a stable id."""
    section = nodes.section()
    section["ids"].append(node_id if node_id is not None else nodes.make_id(title))
    directive.set_source_info(section)
    section += nodes.title(text=title)
    return section


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


def params_node_id(flow: Flow) -> str:
    """Return a stable, unique section id for *flow*'s parameter section."""
    return nodes.make_id(f"prefect-params-{flow_entrypoint(flow)}")


def render_flow_section(
    directive: SphinxDirective,
    flow: Flow,
    markers: MarkerResult | None,
    models: ModelCollection,
    *,
    description_from: str | None = None,
    node_id: str | None = None,
    include_description: bool = True,
) -> nodes.section:
    """Render a flow section for ``prefect-flow`` or ``prefect-params``."""
    section = make_section(
        directive,
        flow.name or type(flow).__name__,
        node_id=node_id,
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

    render_parameter_table(directive, section, flow, models)
    render_model_sections(directive, section, models.models)

    return section
