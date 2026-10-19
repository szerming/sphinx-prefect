# Select main flows with docstring markers and module scanning

- **Status:** Accepted
- **Date:** 2026-10-19

## Context

Prefect has no concept of a “main flow”. The requirement offers several identification mechanisms: a namespace convention, a marker decorator, or a docstring marker. A namespace convention is brittle and a decorator couples runtime flow code to a documentation package. A docstring marker keeps selection in the documentation surface, but needs a scan to be useful.

## Decision

Support explicit selection first:

- `.. prefect-flow:: mypkg.flows.eda` always documents the named flow.
- `prefect_main_flows` lists entrypoints that are main flows regardless of markers.

For module scanning, support three docstring markers:

- a standalone `@mainflow` line (literal text, not a Python decorator);
- YAML frontmatter with `mainflow: true`;
- a reST field `:mainflow:` or `:mainflow: true`.

`prefect-flow-index` imports `prefect_modules`, finds `Flow` objects, selects those with a true marker or a `prefect_main_flows` entry, and renders one section per flow. Any true marker wins over a false marker; conflicts warn. All marker syntax is stripped from the rendered description.

## Consequences

- Flow code does not import a documentation package.
- Docstrings carry selection metadata, which is less visible than a decorator and can be misused. The exact marker syntax is documented and parsed strictly.
- YAML frontmatter requires parsing, but is supported without requiring MyST for docstrings.
- Module scanning imports user modules; import side effects are documented.
- The index renders one page with sections. Separate pages remain explicit.

## Considered options

- **`@mainflow` decorator:** would couple runtime code to this package; rejected.
- **Namespace convention:** too brittle; rejected.
- **Explicit directives/config only:** simple, but no automatic discovery; rejected because the requirement asks for it.

## References

- `docs/specs/0001-sphinx-prefect-v0.1.md` §6.8–6.9
