# 07 — Runtime DAG generation and Mermaid rendering

- **Status:** Published — [#7](https://github.com/szerming/sphinx-prefect/issues/7)
- **Labels:** `ready-for-agent`, `enhancement`
- **Depends on:** [#2](https://github.com/szerming/sphinx-prefect/issues/2)
- **Spec:** [`docs/specs/0001-sphinx-prefect-v0.1.md`](../specs/0001-sphinx-prefect-v0.1.md)
- **ADRs:** [0001](../adr/0001-runtime-prefect-dag.md)

## Context

Prefect's `Flow.generate_mermaid_graph(**sample_args)` produces a Mermaid graph by executing the flow under `TaskVizTracker`. It is offline for self-contained flows but not side-effect-free. DAG generation is therefore opt-in.

## Scope

- Register `prefect_dag_enabled: bool = False` and `prefect_dag_sample_args: dict[str, dict[str, object]] = {}`.
- Implement `_dag.py`:
  - look up sample arguments by flow entrypoint;
  - call `flow.generate_mermaid_graph(**args)`;
  - catch missing/invalid arguments, `VisualizationUnsupportedError`, `MissingContextError`, and other execution errors;
  - warn-and-omit by default, fail under `prefect_on_error = "error"`;
  - emit a `sphinxcontrib.mermaid.mermaid` node with `code` and `options`;
  - add `classDef` styles for main flow, subflow, task, and unknown nodes;
  - add a main-flow node if Prefect's output omits it, with edges to root nodes;
  - render a legend;
  - render a short note when no tasks/subflows were observed.
- Implement `prefect-dag` (always attempts generation).
- Wire `prefect-flow` `:show-dag:` and `:no-dag:` and `prefect-flow-index` flags.
- Document that DAG generation executes the flow body and may perform I/O.
- Verify text/man behavior and document the `mmdc` requirement for LaTeX/PDF.

## Acceptance criteria

- [ ] With `:show-dag:`, a pure flow with tasks and a subflow renders a Mermaid node containing the expected nodes and edges.
- [ ] Without `:show-dag:` and with `prefect_dag_enabled = False`, no flow code executes.
- [ ] `prefect_dag_enabled = True` enables the graph; `:no-dag:` suppresses it.
- [ ] Missing sample arguments for a required parameter warn and omit the graph.
- [ ] A flow using `.submit()` warns and omits the graph.
- [ ] A flow requiring `prefect.runtime` context warns and omits the graph.
- [ ] A pure flow builds with `PREFECT_API_URL` pointing at a dead port.
- [ ] The text builder builds without crashing.
- [ ] Styling and legend appear in HTML.

## Test plan

- Sphinx test roots for `:show-dag:`, global enablement, and `:no-dag:`.
- Fixture pure flow with two tasks and one subflow; assert `<pre class="mermaid">` and `flowchart`.
- Error tests for missing args, `.submit()`, and a runtime-context flow.
- Offline test with a dead `PREFECT_API_URL`.
- Text builder test.

## Out of scope

- Subflow/task documentation sections (ticket 08).
- Recursive subflow graphs.
- `arun_deployment()` edges.
- Subprocess isolation and caching.
