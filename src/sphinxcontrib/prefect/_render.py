"""Shared helpers for building directive doctrees."""

from __future__ import annotations

from typing import TYPE_CHECKING

from docutils import nodes

if TYPE_CHECKING:
    from collections.abc import Iterable

    from sphinx.util.docutils import SphinxDirective


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


def render_rst(
    directive: SphinxDirective,
    section: nodes.Element,
    text: str,
) -> None:
    """Parse RST *text* and append the resulting nodes to *section*."""
    section.extend(directive.parse_text_to_nodes(text, allow_section_headings=True))


def render_directive_content(
    directive: SphinxDirective,
    section: nodes.Element,
) -> None:
    """Parse the directive body and append it to *section*."""
    section.extend(directive.parse_content_to_nodes(allow_section_headings=True))
