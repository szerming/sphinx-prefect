# 02 — Core `prefect-flow` directive and flow metadata

- **Status:** Published — [#2](https://github.com/szerming/sphinx-prefect/issues/2)
- **Labels:** `ready-for-agent`, `enhancement`
- **Depends on:** [#1](https://github.com/szerming/sphinx-prefect/issues/1)
- **Spec:** [`docs/specs/0001-sphinx-prefect-v0.1.md`](../specs/0001-sphinx-prefect-v0.1.md)
- **ADRs:** [0002](../adr/0002-standalone-directives.md)

## Context

The extension needs a directive that resolves an importable flow and renders its basic metadata before parameters, models, or graphs are added.

## Scope

- Implement lazy object resolution:
  - accept `module.qualname` and `module:qualname`;
  - import the module with `importlib.import_module()` inside `run()`;
  - traverse attributes with `getattr`;
  - require a Prefect `Flow`.
- Implement `prefect-flow` as a `SphinxDirective`:
  - section title from `flow.name`;
  - entrypoint from `flow.fn.__module__` and `flow.fn.__qualname__`;
  - version when `flow.version` is not `None`;
  - signature from `inspect.signature(flow.fn)`;
  - description from `flow.description`, normalized with `inspect.cleandoc` and parsed as RST;
  - append directive body content after the generated description.
- Add shared doctree/section helpers in `_render.py`.
- Register `prefect_on_error` (`"warn"` default, `"error"` strict) and a helper that emits source-located warnings/errors.
- Register `prefect-flow` in `setup()`.

## Acceptance criteria

- [ ] `.. prefect-flow:: fixture_pkg.flows.main` renders a section with title, description, entrypoint, version, and signature.
- [ ] A flow with no docstring/description renders without a traceback.
- [ ] Missing module, missing attribute, and non-`Flow` objects warn by default.
- [ ] The same failures raise and fail the build under `prefect_on_error = "error"`.
- [ ] No user flow module is imported during `setup()`.
- [ ] Directive body content is rendered after the generated description.

## Test plan

- Sphinx test root with a fixture flow module.
- Assert doctree section/paragraph nodes and HTML text.
- Error tests for missing module, missing object, and a `@task` passed instead of a `@flow`.
- A module that raises on import is not imported by `setup()`.

## Out of scope

- Docstring markers, external descriptions, parameter tables, Pydantic models, DAG, module scanning.
