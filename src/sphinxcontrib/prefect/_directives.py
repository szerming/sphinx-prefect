"""Sphinx directives for documenting Prefect flows."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

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
from sphinxcontrib.prefect._models import ModelCollection, collect_flow_models
from sphinxcontrib.prefect._render import (
    flow_node_id,
    params_node_id,
    render_directive_content,
    render_flow_section,
)
from sphinxcontrib.prefect._scan import scan_main_flows

if TYPE_CHECKING:
    from prefect import Flow


def _resolve_or_report(
    directive: SphinxDirective,
    entrypoint: str,
) -> Flow | None:
    """Resolve *entrypoint* and report failures through the error policy."""
    try:
        return resolve_flow(entrypoint)
    except ObjectResolutionError as exc:
        report_error(directive, str(exc))
        return None


def _collect_models_or_report(
    directive: SphinxDirective,
    flow: Flow,
) -> ModelCollection:
    """Collect *flow*'s models and report diagnostics at the directive."""
    models = collect_flow_models(flow)
    report_diagnostics(directive, errors=models.errors)
    return models


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
        flow = _resolve_or_report(self, self.arguments[0])
        if flow is None:
            return []

        markers = parse_mainflow_markers(flow.fn.__doc__)
        report_diagnostics(
            self,
            warnings=markers.warnings,
            errors=markers.errors,
        )
        models = _collect_models_or_report(self, flow)
        section = render_flow_section(
            self,
            flow,
            markers,
            models,
            description_from=self.options.get("description-from"),
        )
        if self.content:
            render_directive_content(self, section)
        return [section]


class PrefectParamsDirective(SphinxDirective):
    """Render a flow's signature, parameter table, and Pydantic models."""

    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = False
    has_content = False

    def run(self) -> list[nodes.Node]:
        flow = _resolve_or_report(self, self.arguments[0])
        if flow is None:
            return []

        models = _collect_models_or_report(self, flow)
        return [
            render_flow_section(
                self,
                flow,
                None,
                models,
                node_id=params_node_id(flow),
                include_description=False,
            )
        ]


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

        sections: list[nodes.Node] = []
        for selection in result.flows:
            models = _collect_models_or_report(self, selection.flow)
            sections.append(
                render_flow_section(
                    self,
                    selection.flow,
                    selection.markers,
                    models,
                    node_id=flow_node_id(selection.flow),
                )
            )
        return sections
