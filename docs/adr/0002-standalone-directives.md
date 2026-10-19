# Implement documentation as standalone Sphinx directives

- **Status:** Accepted
- **Date:** 2026-10-19

## Context

Sphinx 9 rewrote autodoc. Its default member discovery classifies a Prefect `Flow` as a function because `inspect.isroutine()` returns true, and it ignores custom `Documenter` subclasses during `automodule :members:`. A custom `FunctionDocumenter` would work only with the legacy class-based path or by monkey-patching private Sphinx internals.

Flow documentation also needs output that autodoc's function model does not provide: a parameter/model section, a Mermaid graph, and subflow/task sections.

## Decision

Implement four standalone `SphinxDirective` classes:

- `prefect-flow`
- `prefect-params`
- `prefect-dag`
- `prefect-flow-index`

They import user objects lazily and build sections with `nested_parse` and standard doctree nodes. Do not register custom `Documenter` classes and do not patch Sphinx's autodoc internals.

## Consequences

- Users opt in with explicit directives rather than `automodule :members:`.
- The extension is stable across Sphinx 8/9 in principle, though v0.1 targets Sphinx 9.
- Basic flow signatures and docstrings remain available through ordinary autodoc, but flow-specific output comes from these directives.
- Testing uses `sphinx.testing.fixtures` and directive-level doctree assertions.

## Considered options

- **Custom `FunctionDocumenter`:** fragile on Sphinx 9 and ignored by `automodule :members:`.
- **Monkey-patching `_best_object_type_for_member`:** relies on private internals; rejected.
- **`autosummary` stubs:** adds file generation and does not solve flow-specific rendering.

## References

- Sphinx 9.0 changelog: <https://www.sphinx-doc.org/en/master/changes/9.0.html>
- Sphinx autodoc rewrite issue: <https://github.com/sphinx-doc/sphinx/issues/14089>
