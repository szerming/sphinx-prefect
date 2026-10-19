"""Sphinx directives for documenting Prefect flows."""

from __future__ import annotations

import inspect
from typing import TYPE_CHECKING

from docutils import nodes
from sphinx.util.docutils import SphinxDirective

from sphinxcontrib.prefect._errors import report_error
from sphinxcontrib.prefect._import import ObjectResolutionError, resolve_flow
from sphinxcontrib.prefect._render import (
    add_field_list,
    make_section,
    render_directive_content,
    render_rst,
)

if TYPE_CHECKING:
    from prefect import Flow


class PrefectFlowDirective(SphinxDirective):
    """Render the description and metadata of a Prefect flow."""

    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = False
    has_content = True

    def run(self) -> list[nodes.Node]:
        try:
            flow = resolve_flow(self.arguments[0])
        except ObjectResolutionError as exc:
            report_error(self, str(exc))
            return []
        return [self.render_flow(flow)]

    def render_flow(self, flow: Flow) -> nodes.section:
        section = make_section(self, flow.name or type(flow).__name__)

        fields = [("Entrypoint", self.entrypoint(flow))]
        if flow.version is not None:
            fields.append(("Version", str(flow.version)))
        fields.append(("Signature", str(inspect.signature(flow.fn))))
        add_field_list(section, fields)

        description = flow.description
        if description:
            render_rst(self, section, inspect.cleandoc(description))

        if self.content:
            render_directive_content(self, section)

        return section

    @staticmethod
    def entrypoint(flow: Flow) -> str:
        """Return the importable entrypoint of *flow*."""
        return f"{flow.fn.__module__}.{flow.fn.__qualname__}"
