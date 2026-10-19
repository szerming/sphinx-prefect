# Use Prefect's runtime Mermaid generation for flow graphs

- **Status:** Accepted
- **Date:** 2026-10-19

## Context

The requirement asks for flow diagrams generated from Prefect's built-in DAG support. Prefect 3.8 exposes `Flow.generate_mermaid_graph()`, which executes the flow body under `TaskVizTracker` and returns a Mermaid `flowchart TD` string. It can run without a Prefect server for self-contained flows, but it is not a static analyzer: it runs arbitrary flow code, observes one execution path, renders subflows as leaves, and does not track `arun_deployment()` / `run_deployment()` calls or `.submit()` / `.map()`.

The alternative is a custom AST call-graph analyzer, which would avoid execution but would add a large, incomplete static-analysis subsystem and diverge from the requested use of Prefect.

## Decision

Use `Flow.generate_mermaid_graph(**sample_args)` as the only DAG generator in v0.1. Make it opt-in through `:show-dag:` or `prefect_dag_enabled = True`. Supply arguments from `prefect_dag_sample_args`, and warn-and-omit on missing arguments or execution failure. Do not add static analysis.

Subflows and tasks are discovered from the generated graph's node names and matched to `Flow`/`Task` objects in the flow's module. Subflows are documented as leaves; their internal graphs require a separate directive.

## Consequences

- Enabling a DAG is an explicit decision to execute flow code, with possible I/O, credential access, and writes. This must be prominent in the documentation and warnings.
- Graphs represent one observed execution path, not all possible branches.
- Deployment-spawned child flows are invisible unless documented explicitly.
- `.submit()`, `.map()`, and `.apply_async()` cannot be visualized; the extension catches Prefect's `VisualizationUnsupportedError`.
- Flows that rely on `prefect.runtime` may fail without a flow-run context; the extension catches the error and omits the graph.
- `parallel_read_safe` must be `False`.

## Considered options

- **Custom static AST analysis:** avoids execution and expands subflows, but is a much larger project and was explicitly rejected by the maintainer.
- **Custom runtime tracker:** replicate `generate_mermaid_graph()` with a hand-built `TaskVizTracker` for structured nodes. More control, but more coupling to Prefect internals and no additional capability in v0.1.
- **No graph:** not acceptable; the graph is a core requirement.

## References

- Prefect 3.8 `prefect/flows.py`, `Flow.generate_mermaid_graph`
- Prefect 3.8 `prefect/utilities/visualization.py`
- <https://docs.prefect.io/v3/how-to-guides/workflows/visualize-workflow-structure>
