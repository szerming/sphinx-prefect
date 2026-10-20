"""Generate and render Prefect's runtime Mermaid flow graphs."""

from __future__ import annotations

import re
import warnings
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from docutils import nodes

from sphinxcontrib.prefect._errors import report_diagnostics, report_error
from sphinxcontrib.prefect._graph import build_diagram, classify_nodes, parse_mermaid
from sphinxcontrib.prefect._import import flow_entrypoint

if TYPE_CHECKING:
    from sphinx.util.docutils import SphinxDirective

    from prefect import Flow
    from sphinxcontrib.prefect._graph import ParsedGraph

_PREFECT_EXECUTION_WARNING = re.escape(
    "`flow.generate_mermaid_graph()` will execute code"
)


def render_flow_graph(
    directive: SphinxDirective,
    section: nodes.Element,
    flow: Flow,
) -> ParsedGraph | None:
    """Append a runtime flow graph and return its classified nodes.

    Returns ``None`` when the graph could not be generated or the flow body
    called no tasks or subflows.
    """
    code = generate_graph(directive, flow)
    if code is None:
        return None

    graph = parse_mermaid(code)
    if not graph.nodes:
        note = nodes.paragraph(
            text=(
                "No tasks or subflows were observed when the runtime DAG "
                "executed, so no flow graph is rendered."
            ),
            classes=["prefect-dag-empty"],
        )
        section += note
        return None

    from sphinxcontrib.mermaid import mermaid

    classified = classify_nodes(flow, graph)
    report_diagnostics(directive, warnings=classified.warnings)

    section += nodes.rubric(text="Flow graph")
    diagram = mermaid()
    diagram["code"] = build_diagram(flow, classified, preclassified=True)
    diagram["options"] = {}
    section += diagram
    section += _legend()
    return classified


def generate_graph(directive: SphinxDirective, flow: Flow) -> str | None:
    """Execute *flow* under Prefect's visualizer and return its Mermaid graph."""
    arguments = _sample_arguments(directive, flow)
    if arguments is None:
        return None

    try:
        # Prefect warns that graph generation executes flow code. The extension
        # documents that behavior and enables it explicitly, so the duplicate
        # warning would only add noise to every build.
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message=_PREFECT_EXECUTION_WARNING,
                category=UserWarning,
            )
            return flow.generate_mermaid_graph(**arguments)
    except Exception as exc:
        report_error(directive, _execution_failure(flow, exc))
        return None


def _sample_arguments(
    directive: SphinxDirective,
    flow: Flow,
) -> dict[str, Any] | None:
    """Resolve sample arguments for *flow* from the extension configuration."""
    entrypoint = flow_entrypoint(flow)
    configured = directive.config.prefect_dag_sample_args
    if not isinstance(configured, Mapping):
        report_error(
            directive,
            "prefect_dag_sample_args must be a mapping of flow entrypoints to "
            "argument mappings.",
        )
        return None

    if entrypoint in configured:
        arguments = configured[entrypoint]
        if not isinstance(arguments, Mapping):
            report_error(
                directive,
                f"prefect_dag_sample_args[{entrypoint!r}] must be a mapping of "
                "parameter names to values.",
            )
            return None
        return dict(arguments)

    required = list(flow.parameters.model_dump().get("required") or ())
    if required:
        names = ", ".join(repr(name) for name in required)
        report_error(
            directive,
            f"The runtime DAG for {entrypoint!r} requires sample arguments for "
            f"{names}. Configure prefect_dag_sample_args[{entrypoint!r}].",
        )
        return None
    return {}


def _execution_failure(flow: Flow, exc: Exception) -> str:
    """Return an actionable message for a failed graph generation."""
    entrypoint = flow_entrypoint(flow)
    detail = str(exc).strip()

    from prefect.exceptions import MissingContextError
    from prefect.utilities.visualization import VisualizationUnsupportedError

    if isinstance(exc, VisualizationUnsupportedError) or _is_async_task_error(
        exc, detail
    ):
        reason = (
            "the flow uses .submit(), .map(), .apply_async(), or another "
            "asynchronous task call that Prefect cannot visualize"
        )
    elif isinstance(exc, MissingContextError):
        reason = "the flow requires an active Prefect flow-run context"
    elif isinstance(exc, TypeError):
        reason = "the configured sample arguments do not match the flow signature" + (
            f" ({detail})" if detail else ""
        )
    else:
        reason = f"{type(exc).__name__}: {detail}" if detail else type(exc).__name__

    return (
        f"Could not generate the runtime DAG for {entrypoint!r}: {reason}. "
        "The graph was omitted."
    )


def _is_async_task_error(exc: Exception, detail: str) -> bool:
    """Return whether *exc* looks like an unsupported asynchronous task call."""
    if not isinstance(exc, (AttributeError, RuntimeError)):
        return False
    lowered = detail.lower()
    if "unable to determine task runner" in lowered:
        return True
    if "viztask" in lowered:
        return any(
            operation in lowered for operation in ("submit", "map", "apply_async")
        )
    return any(
        operation in lowered for operation in (".submit(", ".map(", ".apply_async(")
    )


def _legend() -> nodes.paragraph:
    """Return a text legend describing the graph's node colors."""
    legend = nodes.paragraph(classes=["prefect-dag-legend"])
    legend += nodes.strong(text="Legend:")
    legend += nodes.Text(" ")
    entries = (
        ("main flow", "indigo", "main"),
        ("subflow", "blue", "subflow"),
        ("task", "green", "task"),
        ("unknown node", "amber", "unknown"),
    )
    for index, (label, color, kind) in enumerate(entries):
        if index:
            legend += nodes.Text(" · ")
        legend += nodes.inline(
            text=f"{label} ({color})",
            classes=["prefect-dag-legend", f"prefect-dag-legend-{kind}"],
        )
    return legend
