# 08 — Subflow/task discovery and cross-references

- **Status:** Published — [#8](https://github.com/szerming/sphinx-prefect/issues/8)
- **Labels:** `ready-for-agent`, `enhancement`
- **Depends on:** [#6](https://github.com/szerming/sphinx-prefect/issues/6), [#7](https://github.com/szerming/sphinx-prefect/issues/7)
- **Spec:** [`docs/specs/0001-sphinx-prefect-v0.1.md`](../specs/0001-sphinx-prefect-v0.1.md)
- **ADRs:** [0001](../adr/0001-runtime-prefect-dag.md)

## Context

The runtime graph records task and subflow names but does not retain object references. We match those names to `Flow`/`Task` objects in the flow's module, then document the matches. Subflows remain leaves; their internals require a separate directive.

## Scope

- Implement `_graph.py`:
  - parse Mermaid node labels and edges from `generate_mermaid_graph()` output;
  - strip duplicate suffixes (`-0`, `-1`, …);
  - build a name → object map from module-level `Flow` and `Task` objects;
  - return matched, ambiguous, and unknown nodes.
- Render a “Subflows” section and a “Tasks” section:
  - matched subflows: name, entrypoint, description, signature, parameter table, models;
  - matched tasks: name, description, signature, parameter table, models (using `inspect.signature(task.fn)` and `prefect.utilities.callables.parameter_schema(task.fn)`);
  - unknown nodes: listed as unknown/external with no link;
  - ambiguous names: warn and leave unlinked.
- Add stable anchors (`prefect-flow-<slug>`, `prefect-task-<slug>`) and RST cross-references for documented names.
- Do not add hyperlinks inside the Mermaid graph; links live in the sections.
- Do not recursively generate subflow graphs.

## Acceptance criteria

- [ ] A main flow calling a subflow renders a subflow section with its docstring and parameters.
- [ ] A main flow calling tasks renders a task section for each matched task.
- [ ] Unknown graph nodes are listed without a link.
- [ ] Duplicate task/subflow names warn and remain unlinked.
- [ ] Cross-references resolve to the generated sections in HTML.
- [ ] A subflow's internal tasks are not expanded under the main flow.
- [ ] Deployment-spawned flows are absent and the limitation is documented.

## Test plan

- Fixture flow with a subflow containing its own task; assert the subflow is a leaf and the task is not under the main flow.
- Fixture with two same-named tasks; assert warning and no link.
- Fixture with an unknown node (for example a dynamic call); assert unknown listing.
- Assert `href="#prefect-flow-..."` / `href="#prefect-task-..."` in HTML.

## Out of scope

- Recursive subflow graphs.
- `arun_deployment()` / `run_deployment()` edges.
- A custom Sphinx object domain.
