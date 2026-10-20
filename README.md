# sphinx-contrib-prefect

A Sphinx extension for documenting Prefect flows, their parameters, Pydantic
models, and the tasks and subflows observed in a flow graph.

The extension resolves flows from importable entrypoints and renders them as
normal Sphinx sections. The v0.1 design renders flow graphs with Prefect's own
runtime Mermaid generation, so no Prefect server or network access is required
for self-contained flows.

**Status:** v0.1 is ready for release. The package scaffold, the core
`prefect-flow` and `prefect-params` directives, main-flow docstring markers,
external RST and MyST Markdown descriptions, module scanning with
`prefect-flow-index`, parameter tables, Pydantic model documentation,
runtime Mermaid flow graphs with `:show-dag:` and `prefect-dag`, subflow/task
sections with cross-references, the unified error, dependency-tracking, and
parallel-safety policy, and the documentation, example, and release
preparation are implemented. See the [release checklist](docs/release.md) and
[CHANGELOG](CHANGELOG.md). PyPI publishing runs through a manually triggered,
human-approved GitHub Actions workflow.

## Project context

Read these before changing behavior or architecture:

- **[Usage guide](docs/guide.md)** — complete examples for documenting flows
  with `prefect-flow`, `prefect-params`, `prefect-dag`, and
  `prefect-flow-index`.
- **[Example project](examples/demo/)** — a buildable Sphinx project with a
  main flow, subflow, tasks, scalar and nested Pydantic parameters, all three
  marker forms, an index page, and a standalone flow page.
- **[Release checklist](docs/release.md)** — versioning, packaging, CI checks,
  and the manual PyPI upload step.
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

Document a flow by its importable entrypoint in `index.rst`:

```rst
EDA pipeline
============

.. prefect-flow:: mypkg.flows.eda
```

Build the page with `sphinx-build -b html . _build/html`. The directive renders
the flow's title, entrypoint, optional version, signature, reStructuredText
description, parameter table, and Pydantic model documentation. Both
`mypkg.flows.eda` and `mypkg.flows:eda` entrypoint forms are accepted.

Prefect reads parameter descriptions from Google-style `Args:` sections. Each
row shows the parameter name, type, required/optional status, default, and
description. Pydantic parameter models are rendered by
`sphinxcontrib-pydantic`, including nested models and `Field(description=...)`
text. Only importable module-level Pydantic v2 models can be documented; local,
nested, dynamically generated, and Pydantic v1 models are omitted with a
diagnostic. Use `prefect-params` to render the flow's metadata fields,
parameter table, and model sections without the description:

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

## Directive reference

| Directive | Arguments | Options | Renders |
| --- | --- | --- | --- |
| `prefect-flow` | Flow entrypoint (`module.qualname` or `module:qualname`) | `:show-dag:`, `:no-dag:`, `:description-from:` | Title, entrypoint, version, signature, description, parameter table, models, optional graph, subflow/task sections, and body content |
| `prefect-params` | Flow entrypoint | — | Entrypoint, version, signature, parameter table, and model sections |
| `prefect-dag` | Flow entrypoint | — | Runtime graph plus the observed subflow/task/unknown-node sections |
| `prefect-flow-index` | — | `:show-dag:`, `:no-dag:` | One `prefect-flow`-style section per selected main flow |

## Configuration

All values are registered with rebuild type `env`.

| Name | Type | Default | Purpose |
| --- | --- | --- | --- |
| `prefect_modules` | `list[str]` | `[]` | Modules scanned by `prefect-flow-index` |
| `prefect_main_flows` | `list[str]` | `[]` | Entrypoints selected as main flows regardless of markers |
| `prefect_dag_enabled` | `bool` | `False` | Enable runtime graph generation for `prefect-flow` |
| `prefect_dag_sample_args` | `dict[str, dict[str, object]]` | `{}` | Sample arguments keyed by flow entrypoint |
| `prefect_on_error` | `str` | `"warn"` | `"warn"` continues with a warning; `"error"` fails the build |

## Main-flow markers

A flow becomes a main flow in `prefect-flow-index` when its docstring uses any
of these forms:

```python
@flow
def eda(seed: int = 1):
    """Run the EDA build.

    @mainflow
    """
```

```python
@flow
def eda(seed: int = 1):
    """---
    mainflow: true
    ---
    Run the EDA build.
    """
```

```python
@flow
def eda(seed: int = 1):
    """Run the EDA build.

    :mainflow:
    """
```

- `@mainflow` is a literal standalone docstring line, not a Python decorator.
- YAML frontmatter is parsed only at the start of the docstring;
  `mainflow: false` does not select the flow.
- `:mainflow:` and `:mainflow: true` select the flow; `:mainflow: false` does
  not.
- A true marker wins over a false marker and emits a conflict warning.
- Explicit selection with `prefect_main_flows` or a `prefect-flow` directive
  overrides markers.
- All marker syntax is stripped from the rendered description.
- Malformed YAML or an invalid marker value follows `prefect_on_error`.

The [example project](examples/demo/) demonstrates all three forms.

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
renders the graph without the flow description or parameter table:

```rst
.. prefect-dag:: mypkg.flows.eda
```

The graph styles the main flow, subflows, tasks, and unknown nodes, and adds a
legend. Missing sample arguments, unsupported `.submit()` / `.map()` calls,
missing Prefect run context, and execution failures follow `prefect_on_error`
and omit the graph.

Limitations and safety:

- **One execution path.** Only the branches taken with the configured sample
  arguments appear. Change the sample arguments to document a different path.
- **Subflows are leaves.** A subflow's internal tasks are not expanded and no
  recursive graph is generated. Add a separate directive for its internals.
- **Deployment calls are invisible.** Flows started with `arun_deployment()` or
  `run_deployment()` are not tracked; document them with explicit directives.
- **Asynchronous task calls are unsupported.** `.submit()`, `.map()`, and
  `.apply_async()` raise Prefect's `VisualizationUnsupportedError`, so the
  graph is omitted.
- **The flow body executes.** Enabling a graph is an explicit decision to run
  user code that may perform I/O, read credentials, or write files. There is no
  sandbox.
- **Sample arguments are passed as-is.** Prefect calls the flow function with
  the configured values without validating them against the flow's Pydantic
  parameter model. When a parameter is a model, construct the model instance in
  `conf.py`; a plain dictionary is not coerced.

Graph nodes that match module-level `Flow` and `Task` objects also get
**Subflows** and **Tasks** sections with their description, signature,
parameter table, and Pydantic models. Their names link to stable
`prefect-flow-<entrypoint>` and `prefect-task-<entrypoint>` anchors from a
short list in each section; the Mermaid source itself stays unlinked. Names
that match no object, or more than one object, are listed under **Unknown
nodes** without a link. Subflows are documented as leaves: their internal
tasks are not expanded and no recursive graph is generated.

The text/man builders render Mermaid's `[graph]` placeholder, and LaTeX/PDF
output needs the `mmdc` binary. See the
[usage guide](docs/guide.md#runtime-flow-graphs) for enablement, sample
arguments, failure behavior, and limitations.

## Errors, rebuilds, and parallelism

Recoverable failures warn and omit the affected part of the page by default.
Set `prefect_on_error = "error"` to fail the build instead. Every diagnostic
names the directive's `path:line` and, where available, the flow, task, module,
or description file involved; the complete list is in the
[usage guide's failure-modes table](docs/guide.md#failure-modes).

Flow and task source files and external description files are registered with
`env.note_dependency()`, so editing them rebuilds the page in Sphinx
incremental mode. The extension declares `parallel_read_safe = False` because
runtime DAG generation executes user code, and `parallel_write_safe = True`.
v0.1 has no custom DAG cache and no subprocess isolation.

## Documentation and example

The extension's own documentation lives under `docs/` and builds with
`-W` (warnings are errors):

```bash
uv sync --extra markdown
uv run sphinx-build -W -b html docs docs/_build/html
```

The [example project](examples/demo/) exercises every directive, all three
main-flow marker forms, scalar and nested Pydantic parameters, a runtime graph,
subflows, tasks, an index page, and a standalone flow page. Its `conf.py`
contains a working `prefect_dag_sample_args` entry:

```bash
uv run sphinx-build -W -b html examples/demo examples/demo/_build/html
```

CI builds both projects with `-W`, inspects the wheel and sdist, and installs
the built wheel into a clean virtual environment before rebuilding the example.
Every CI run also uploads the generated example HTML as the downloadable
`example-html` artifact, so the rendered pages can be inspected without a local
build. The [`Publish to PyPI`](.github/workflows/publish.yml) workflow is
started manually from a `v*` tag, reruns those checks, and then waits for
approval in the protected `pypi` GitHub environment before publishing. See the
[release checklist](docs/release.md) for the one-time environment and PyPI
trusted-publisher setup.

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
