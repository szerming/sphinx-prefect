# sphinx-contrib-prefect

A Sphinx extension for documenting Prefect flows, their parameters, Pydantic
models, and the tasks and subflows observed in a flow graph.

The extension resolves flows from importable entrypoints and renders them as
normal Sphinx sections. The v0.1 design renders flow graphs with Prefect's own
runtime Mermaid generation, so no Prefect server or network access is required
for self-contained flows.

**Status:** v0.1 is in development. The package scaffold, the core
`prefect-flow` and `prefect-params` directives, main-flow docstring markers,
external RST and MyST Markdown descriptions, module scanning with
`prefect-flow-index`, parameter tables, Pydantic model documentation, and
runtime Mermaid flow graphs with `:show-dag:` and `prefect-dag` are
implemented. The remaining work is tracked in
issues [#8–#10](https://github.com/szerming/sphinx-prefect/issues).

## Project context

Read these before changing behavior or architecture:

- **[Usage guide](docs/guide.md)** — complete examples for documenting flows
  with `prefect-flow`, `prefect-params`, `prefect-dag`, and
  `prefect-flow-index`.
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

For MyST Markdown external descriptions, install the `markdown` extra:

```bash
pip install "sphinx-contrib-prefect[markdown]"
```

The core package does not depend on MyST. Without the extra, `.md` and
`.markdown` description files warn and are omitted (or fail the build under
`prefect_on_error = "error"`).

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
signature, reStructuredText description, parameter table, and Pydantic model
documentation. Both `mypkg.flows.eda` and `mypkg.flows:eda` entrypoint forms
are accepted.

Prefect reads parameter descriptions from Google-style `Args:` sections. Each
row shows the parameter name, type, required/optional status, default, and
description. Pydantic parameter models are rendered by
`sphinxcontrib-pydantic`, including nested models and `Field(description=...)`
text. Use `prefect-params` to render the flow's metadata fields, parameter
table, and model sections without the description:

```rst
.. prefect-params:: mypkg.flows.eda
```

Use an external RST file when the description outgrows the docstring:

```rst
.. prefect-flow:: mypkg.flows.eda
   :description-from: descriptions/eda.rst
```

The path is resolved relative to the Sphinx source directory (the directory
containing `conf.py`). `.rst` files are parsed as reStructuredText. With the
`markdown` extra installed, `.md` and `.markdown` files are parsed as MyST
Markdown, so headings, lists, code blocks, links, and inline markup work.
Docstrings always remain reStructuredText; Markdown applies only to external
files. See the [usage guide](docs/guide.md#descriptions) for the format rules.

Docstrings may also carry a main-flow marker (`@mainflow`, YAML frontmatter, or
`:mainflow:`); marker syntax is stripped from the rendered description. Markers
drive flow selection in `prefect-flow-index`.

Configure one or more scanned modules in `conf.py`:

```python
prefect_modules = ["mypkg.flows"]
prefect_main_flows = ["mypkg.flows.eda"]
```

Then render every selected main flow on the current page:

```rst
.. prefect-flow-index::
```

The index imports each configured module and renders one `prefect-flow`-style
section per flow that has a true marker or an entry in `prefect_main_flows`.
Flows are ordered by module list order and then attribute order; explicit
flows outside `prefect_modules` follow in configuration order. Module scanning
imports user code, so import-time side effects may run during the build.
`:show-dag:` and `:no-dag:` apply to every generated section.

## Runtime flow graphs

Flow graphs come from Prefect's runtime visualization. Generating one executes
the flow body, so it is opt-in and may perform I/O, read credentials, or write
files. Enable it for one directive:

```rst
.. prefect-flow:: mypkg.flows.eda
   :show-dag:
```

Or enable it globally, with sample arguments for required parameters:

```python
prefect_dag_enabled = False
prefect_dag_sample_args = {
    "mypkg.flows.eda": {"seed": 42},
}
```

`:no-dag:` suppresses a globally enabled graph. `prefect-dag` always opts in and
renders only the graph:

```rst
.. prefect-dag:: mypkg.flows.eda
```

The graph styles the main flow, subflows, tasks, and unknown nodes, and adds a
legend. Missing sample arguments, unsupported `.submit()` / `.map()` calls,
missing Prefect run context, and execution failures follow `prefect_on_error`
and omit the graph. A graph records one execution path; subflows are leaves.
The text/man builders render Mermaid's `[graph]` placeholder, and LaTeX/PDF
output needs the `mmdc` binary. See the
[usage guide](docs/guide.md#runtime-flow-graphs) for enablement, sample
arguments, failure behavior, and limitations.

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
