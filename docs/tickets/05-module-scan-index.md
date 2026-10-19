# 05 — Module scan and `prefect-flow-index`

- **Status:** Published — [#5](https://github.com/szerming/sphinx-prefect/issues/5)
- **Labels:** `ready-for-agent`, `enhancement`
- **Depends on:** [#3](https://github.com/szerming/sphinx-prefect/issues/3), [#4](https://github.com/szerming/sphinx-prefect/issues/4)
- **Spec:** [`docs/specs/0001-sphinx-prefect-v0.1.md`](../specs/0001-sphinx-prefect-v0.1.md)
- **ADRs:** [0004](../adr/0004-docstring-markers-and-module-scan.md)

## Context

Docstring markers only reduce boilerplate if the extension can discover marked flows. The index directive renders one page with a section per discovered main flow; automatic file generation is out of scope.

## Scope

- Register `prefect_modules: list[str]` and `prefect_main_flows: list[str]`.
- Implement `prefect-flow-index`:
  - import each module in `prefect_modules`;
  - iterate module-level attributes and collect Prefect `Flow` objects;
  - select flows with a true marker or an entry in `prefect_main_flows`;
  - deduplicate by entrypoint;
  - render one `prefect-flow`-equivalent section per flow, in module/attribute order;
  - include `prefect_main_flows` entries outside `prefect_modules` explicitly;
  - warn when no flows are found.
- Accept `:show-dag:` / `:no-dag:` flags for forward compatibility; wire them to the DAG component when ticket 07 lands.
- Import failures and marker failures follow `prefect_on_error`.
- Document that module scanning imports user modules and may trigger import-time side effects.

## Acceptance criteria

- [ ] A module with two marked flows and one unmarked flow renders two sections.
- [ ] A flow listed in `prefect_main_flows` renders without a marker.
- [ ] A flow listed in both places renders once.
- [ ] Flows are ordered by module list order, then attribute order.
- [ ] An empty scan emits a warning.
- [ ] An unimportable module warns/errors per `prefect_on_error`.
- [ ] The index directive takes no required arguments.

## Test plan

- Sphinx test root with a fixture module containing marked and unmarked flows.
- Assert section count, order, and titles in the doctree/HTML.
- Test duplicate selection and an empty `prefect_modules` list.
- Test a module that raises on import.

## Out of scope

- Generating one `.rst` file per flow.
- DAG generation (ticket 07).
