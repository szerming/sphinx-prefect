# sphinx-contrib-prefect

A Sphinx extension for documenting Prefect flows, their parameters, Pydantic
models, and the tasks and subflows observed in a flow graph.

The extension resolves flows from importable entrypoints and renders them as
normal Sphinx sections. The v0.1 design renders flow graphs with Prefect's own
runtime Mermaid generation, so no Prefect server or network access is required
for self-contained flows.

**Status:** v0.1 is in development. The package scaffold, the core
`prefect-flow` directive, main-flow docstring markers, and external RST
descriptions are implemented. The remaining work is tracked in
issues [#4–#10](https://github.com/szerming/sphinx-prefect/issues).

## Project context

Read these before changing behavior or architecture:

- **[Usage guide](docs/guide.md)** — complete examples for documenting a flow
  with `prefect-flow`.
- **[v0.1 specification](docs/specs/0001-sphinx-prefect-v0.1.md)** — goals,
  behavior, compatibility, and the ticket map.
- **[Architecture decision records](docs/adr/)** — accepted design decisions:
  - [ADR-0001: Runtime Prefect DAG generation](docs/adr/0001-runtime-prefect-dag.md)
  - [ADR-0002: Standalone Sphinx directives](docs/adr/0002-standalone-directives.md)
  - [ADR-0003: Delegate Pydantic rendering](docs/adr/0003-delegate-pydantic-rendering.md)
  - [ADR-0004: Docstring markers and module scanning](docs/adr/0004-docstring-markers-and-module-scan.md)
- **[Glossary](GLOSSARY.md)** — project vocabulary (Main Flow, Subflow, Task,
  Flow Graph, Runtime DAG, and others).
- **[Ticket drafts](docs/tickets/)** — published as GitHub issues
  [#1–#10](https://github.com/szerming/sphinx-prefect/issues).
- **[Coding guide](coding-guide.md)** — repository layout, coding conventions,
  and the definition of done for changes.
- **[Original requirement](user-requirement.md)** — the initial request that
  motivated the project.

## Installation

```bash
pip install sphinx-contrib-prefect
```

For MyST Markdown external descriptions (planned for
[#4](https://github.com/szerming/sphinx-prefect/issues/4)), install the
`markdown` extra:

```bash
pip install "sphinx-contrib-prefect[markdown]"
```

## Quick start

Add the extension to `conf.py`:

```python
extensions = [
    "sphinx.ext.autodoc",
    "sphinxcontrib.pydantic",
    "sphinxcontrib.mermaid",
    "sphinxcontrib.prefect",
]
```

Document a flow by its importable entrypoint:

```rst
.. prefect-flow:: mypkg.flows.eda

   Optional body content is appended after the generated description.
```

The directive renders the flow's title, entrypoint, optional version,
signature, and reStructuredText description. Both `mypkg.flows.eda` and
`mypkg.flows:eda` entrypoint forms are accepted.

Use an external RST file when the description outgrows the docstring:

```rst
.. prefect-flow:: mypkg.flows.eda
   :description-from: descriptions/eda.rst
```

The path is resolved relative to the Sphinx source directory (the directory
containing `conf.py`). Docstrings may also carry a main-flow marker
(`@mainflow`, YAML frontmatter, or `:mainflow:`); marker syntax is stripped
from the rendered description. Markers will drive `prefect-flow-index` once
issue [#5](https://github.com/szerming/sphinx-prefect/issues/5) lands.

The planned v0.1 interface also includes `prefect-params`, `prefect-dag`, and
`prefect-flow-index`. See the [usage guide](docs/guide.md) for marker syntax,
a complete project, error handling, current limitations, and the full planned
interface.

## Development

### Prerequisites

- Python 3.12 or 3.13
- [`uv`](https://docs.astral.sh/uv/)

### Clone and set up

```bash
git clone git@github.com:szerming/sphinx-prefect.git
cd sphinx-prefect
uv sync --all-extras
```

`--all-extras` installs the optional MyST Markdown dependency as well as the
development tools.

### Run checks

```bash
uv run ruff format --check .
uv run ruff check .
uv run pytest
```

Run `uv run ruff format .` to apply formatting. Tests use
`sphinx.testing.fixtures`; integration test roots live under `tests/roots/`.
See the [coding guide](coding-guide.md) for the architecture, test layout, and
the full definition of done.

## License

MIT. See [LICENSE](LICENSE).
