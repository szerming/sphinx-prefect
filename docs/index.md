# sphinx-contrib-prefect

A Sphinx extension for documenting Prefect flows, their parameters, Pydantic
models, and the tasks and subflows observed in a flow graph.

The extension resolves flows from importable entrypoints and renders them as
normal Sphinx sections. Runtime flow graphs use Prefect's own Mermaid
generation, so no Prefect server or network access is required for
self-contained flows.

```{toctree}
:maxdepth: 2
:caption: Documentation

guide
release
specs/0001-sphinx-prefect-v0.1
adr/0001-runtime-prefect-dag
adr/0002-standalone-directives
adr/0003-delegate-pydantic-rendering
adr/0004-docstring-markers-and-module-scan
```

## Start here

- [Usage guide](guide.md) — installation, configuration, directive examples,
  marker syntax, runtime graphs, and failure modes.
- [Release checklist](release.md) — versioning, packaging, CI, and the manual
  PyPI upload step.
- [v0.1 specification](specs/0001-sphinx-prefect-v0.1.md) — goals, behavior,
  compatibility, and the ticket map.
- [Architecture decision records](adr/0001-runtime-prefect-dag.md) — the
  accepted design decisions behind runtime DAGs, standalone directives,
  Pydantic delegation, and docstring markers.

## Repository documents

These documents live at the repository root and are not part of this Sphinx
build:

- [README](https://github.com/szerming/sphinx-prefect/blob/main/README.md) —
  project summary, quick start, directive reference, and configuration table.
- [Glossary](https://github.com/szerming/sphinx-prefect/blob/main/GLOSSARY.md) —
  project vocabulary.
- [Coding guide](https://github.com/szerming/sphinx-prefect/blob/main/coding-guide.md) —
  repository layout, architecture rules, and the definition of done.
- [Example project](https://github.com/szerming/sphinx-prefect/tree/main/examples/demo) —
  a buildable Sphinx project that exercises every directive.
