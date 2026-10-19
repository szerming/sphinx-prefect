# Delegate Pydantic model rendering to sphinxcontrib-pydantic

- **Status:** Accepted
- **Date:** 2026-10-19

## Context

Prefect builds `flow.parameters` from Pydantic v2 models and exposes field descriptions, defaults, and constraints. Rendering that schema as readable Sphinx documentation is a solved problem, but the solutions differ in maintenance and Sphinx 9 compatibility:

- `sphinxcontrib-pydantic` 0.4.0 is current, MIT, Pydantic v2 only, and uses a `pydantic-model` directive plus autodoc event handlers.
- `autodoc_pydantic` 2.2.0 has not been released since 2024 and depends on the legacy class-based autodoc path that Sphinx 9 is moving away from.

`sphinxcontrib-pydantic` does not recursively expand nested models, and its directive accepts only importable module-level classes. It also requires `sphinx.ext.autodoc` to load before it.

## Decision

Use `sphinxcontrib-pydantic>=0.4,<0.5` as a required dependency. Load `sphinx.ext.autodoc` and `sphinxcontrib.pydantic` from our `setup()`. Discover model classes from `typing.get_type_hints(flow.fn, include_extras=True)`, recurse through annotations and `model_fields`, and emit nested `pydantic-model` blocks with `:show-field-summary:`, `:show-validator-summary:`, and `:show-members:`.

Support importable module-level models in v0.1. Warn and omit local, nested, dynamically generated, and Pydantic v1 models. Deduplicate models across the build: the first occurrence indexes, later occurrences use `:noindex:`.

## Consequences

- We add a dependency that is young, uses private Sphinx helpers, and must be pinned below 0.5. Integration tests are required.
- We still implement model traversal and emission; we do not reimplement field/validator tables.
- Nested models are emitted as separate blocks, not expanded inline inside a parent model.
- Computed fields are not rendered in v0.1.
- A runtime-class adapter (synthetic module or private directive subclass) is future work if non-importable models become a requirement.

## Considered options

- **`autodoc_pydantic`:** richer, but unmaintained and tied to legacy autodoc.
- **Custom field tables:** more control, but reinvents a solved problem.
- **`autoclass`:** works, but `Field(description=...)` fields are often not rendered/registered on the autodoc path.

## References

- <https://github.com/mscheltienne/sphinxcontrib-pydantic>
- <https://github.com/mansenfranzen/autodoc_pydantic>
- Sphinx autodoc rewrite: <https://github.com/sphinx-doc/sphinx/issues/14089>
