"""Sphinx directives for documenting Prefect flows."""

from __future__ import annotations

from typing import Any, ClassVar

from docutils import nodes
from docutils.parsers.rst import directives
from sphinx.util.docutils import SphinxDirective

from sphinxcontrib.prefect._errors import (
    report_diagnostics,
    report_error,
    report_warning,
)
from sphinxcontrib.prefect._import import ObjectResolutionError, resolve_flow
from sphinxcontrib.prefect._markers import parse_mainflow_markers
from sphinxcontrib.prefect._render import (
    flow_node_id,
    render_directive_content,
    render_flow_section,
)
from sphinxcontrib.prefect._scan import scan_main_flows


class PrefectFlowDirective(SphinxDirective):
    """Render the description and metadata of a Prefect flow."""

    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = False
    has_content = True
    option_spec: ClassVar[dict[str, Any]] = {
        "description-from": directives.unchanged_required
    }

    def run(self) -> list[nodes.Node]:
        try:
            flow = resolve_flow(self.arguments[0])
        except ObjectResolutionError as exc:
            report_error(self, str(exc))
            return []

        markers = parse_mainflow_markers(flow.fn.__doc__)
        report_diagnostics(
            self,
            warnings=markers.warnings,
            errors=markers.errors,
        )
        section = render_flow_section(
            self,
            flow,
            markers,
            description_from=self.options.get("description-from"),
        )
        if self.content:
            render_directive_content(self, section)
        return [section]


class PrefectFlowIndexDirective(SphinxDirective):
    """Render one flow section per main flow discovered in configured modules."""

    required_arguments = 0
    optional_arguments = 0
    final_argument_whitespace = False
    has_content = False
    option_spec: ClassVar[dict[str, Any]] = {
        "show-dag": directives.flag,
        "no-dag": directives.flag,
    }

    def run(self) -> list[nodes.Node]:
        result = scan_main_flows(
            self.config.prefect_modules,
            self.config.prefect_main_flows,
        )

        report_diagnostics(
            self,
            warnings=result.warnings,
            errors=result.errors,
        )

        if not result.flows:
            report_warning(
                self,
                "prefect-flow-index found no main flows; configure "
                "prefect_modules or prefect_main_flows, or add a main-flow "
                "docstring marker.",
            )
            return []

        return [
            render_flow_section(
                self,
                selection.flow,
                selection.markers,
                node_id=flow_node_id(selection.flow),
            )
            for selection in result.flows
        ]
