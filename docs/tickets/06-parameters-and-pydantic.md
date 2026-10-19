# 06 — Parameter tables and Pydantic model documentation

- **Status:** Published — [#6](https://github.com/szerming/sphinx-prefect/issues/6)
- **Labels:** `ready-for-agent`, `enhancement`
- **Depends on:** [#2](https://github.com/szerming/sphinx-prefect/issues/2)
- **Spec:** [`docs/specs/0001-sphinx-prefect-v0.1.md`](../specs/0001-sphinx-prefect-v0.1.md)
- **ADRs:** [0003](../adr/0003-delegate-pydantic-rendering.md)

## Context

Flow parameters are the strongest offline metadata Prefect provides. `flow.parameters` contains an OpenAPI-style schema with descriptions, defaults, and required fields. Pydantic model rendering is delegated to `sphinxcontrib-pydantic`; this ticket implements discovery and emission.

## Scope

- Implement `_params.py`:
  - read `flow.parameters.model_dump()`;
  - sort by `position`;
  - render name, type, required/optional, default, and description;
  - link Pydantic model types to their generated sections;
  - omit the table when there are no parameters.
- Implement `_models.py`:
  - read `typing.get_type_hints(flow.fn, include_extras=True)`;
  - unwrap `Annotated`, `Optional`/`Union`, `list`, `dict`, `tuple`, `set`, and `RootModel`;
  - collect Pydantic v2 `BaseModel` subclasses;
  - recurse through `model_fields` with a seen set keyed by `(module, qualname)`;
  - verify each model is an importable module-level class;
  - emit nested `pydantic-model` blocks with `:show-field-summary:`, `:show-validator-summary:`, and `:show-members:`;
  - deduplicate across the build using `app.env`: first occurrence indexes, later occurrences use `:noindex:`;
  - warn and omit Pydantic v1, non-importable, local, and dynamically generated models.
- Implement `prefect-params` to render the signature, parameter table, and model sections without description or DAG.
- Ensure `sphinx.ext.autodoc` and `sphinxcontrib.pydantic` are loaded by `setup()` before use.

## Acceptance criteria

- [ ] A flow with scalar parameters renders name, type, required, default, and description.
- [ ] Parameter descriptions from Google-style `Args:` sections appear.
- [ ] A Pydantic parameter renders a `pydantic-model` section with fields, types, defaults, and `Field(description=...)` text.
- [ ] Nested models each get a section; cycles terminate.
- [ ] A non-importable/dynamic model warns and does not break the build.
- [ ] A Pydantic v1 model warns.
- [ ] Repeating a model on another page does not produce a duplicate-object warning.
- [ ] `prefect-params` omits description and DAG output.

## Test plan

- Fixture flow with `int`, `str | None`, and a Pydantic model parameter.
- Fixture model with a nested model and field descriptions.
- Test dynamic model via `pydantic.create_model`.
- Test duplicate models across two pages.
- Assert HTML tables and model sections; assert no warnings in the happy path.

## Out of scope

- Task parameter rendering (ticket 08).
- Computed fields, validators beyond what `sphinxcontrib-pydantic` provides.
- Runtime-class adapters for non-importable models.
