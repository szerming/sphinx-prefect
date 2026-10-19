# Usage guide

This guide shows how to document Prefect flows in a Sphinx project with
`sphinx-contrib-prefect`.

The guide describes the currently implemented `prefect-flow` and
`prefect-flow-index` directives and marks features that are planned for the
rest of v0.1. For the full design, see
the [v0.1 specification](specs/0001-sphinx-prefect-v0.1.md).

## Current status

| Feature | Status |
| --- | --- |
| Resolve flows by `module.qualname` or `module:qualname` | Available |
| Flow title, entrypoint, version, signature, and RST description | Available |
| Directive body content appended after the description | Available |
| External RST descriptions with `:description-from:` | Available |
| External MyST Markdown descriptions (opt-in extra) | Available |
| Main-flow docstring markers and stripping | Available |
| Module scanning with `prefect-flow-index` | Available |
| `prefect_on_error` warn/error policy | Available |
| Parameter tables and Pydantic model sections | Planned — [#6](https://github.com/szerming/sphinx-prefect/issues/6) |
| Runtime Mermaid flow graph | Planned — [#7](https://github.com/szerming/sphinx-prefect/issues/7) |
| Subflow/task sections and cross-references | Planned — [#8](https://github.com/szerming/sphinx-prefect/issues/8) |

## Installation

```bash
pip install sphinx-contrib-prefect
```

Install the `markdown` extra to use MyST Markdown descriptions:

```bash
pip install "sphinx-contrib-prefect[markdown]"
```

The extra is optional. Projects that only use RST docstrings and `.rst`
description files do not need it.

Supported versions: Python 3.12–3.14, Sphinx 9.x, Prefect 3.x, and Pydantic 2.x.

## Complete example

Create a Sphinx project with an importable flow package:

```text
my-docs/
├── conf.py
├── index.rst
└── flows/
    ├── __init__.py
    └── eda.py
```

### 1. Write the flow

`flows/eda.py`:

```python
from prefect import flow, task


@task
def extract(records: int) -> list[int]:
    """Extract a small sample."""
    return list(range(records))


@task
def load(rows: list[int]) -> None:
    """Load rows into the warehouse."""


@flow(version="1.0.0")
def eda(records: int = 42, dry_run: bool = False) -> None:
    """Run the exploratory data analysis pipeline.

    The flow extracts a small sample, then loads the result unless
    ``dry_run`` is true.

    Args:
        records: Number of sample records to generate.
        dry_run: Skip the load step when true.
    """
    rows = extract(records)
    if not dry_run:
        load(rows)
```

Prefect turns the function docstring into `flow.description`. The directive
renders that description as reStructuredText, so inline markup such as
``dry_run`` or *emphasis* works.

### 2. Configure Sphinx

`conf.py`:

```python
import sys
from pathlib import Path

# Make the local `flows` package importable by the directive.
sys.path.insert(0, str(Path(__file__).parent))

extensions = [
    "sphinx.ext.autodoc",
    "sphinxcontrib.pydantic",
    "sphinxcontrib.mermaid",
    "sphinxcontrib.prefect",
]

prefect_on_error = "warn"

# Optional: modules scanned by prefect-flow-index, and flows that are main
# flows without a docstring marker.
prefect_modules = ["flows"]
prefect_main_flows = ["flows.eda"]
```

`sphinxcontrib.prefect` loads `sphinx.ext.autodoc`,
`sphinxcontrib.pydantic`, and `sphinxcontrib.mermaid` itself. Listing them
explicitly documents the dependency order; `sphinx.ext.autodoc` must load
before `sphinxcontrib.pydantic`.

### 3. Document the flow

`index.rst`:

```rst
EDA pipeline
============

.. prefect-flow:: flows.eda

   This body content is rendered after the generated description.

   .. note::

      Directive body content is ordinary reStructuredText.
```

The page renders the flow's Prefect name as a section title (`eda`), followed
by its entrypoint, version, signature, docstring description, and the body
content supplied to the directive.

### 4. Build

```bash
sphinx-build -b html . _build/html
```

Open `_build/html/index.html` to inspect the result.

## Selecting a flow

The `prefect-flow` argument is an importable entrypoint. Two forms are
supported:

```rst
.. prefect-flow:: flows.eda

.. prefect-flow:: flows:eda
```

The module is imported only when the directive runs. Importing the module must
therefore be safe during a documentation build; import-time side effects still
happen.

Use the technical entrypoint as the directive argument. The rendered title
comes from `flow.name`, which uses Prefect's hyphenated naming convention
(for example, a function named `fetch_weather` renders as `fetch-weather`).

## What gets rendered

For each flow, the directive emits:

- a section titled with `flow.name`;
- an **Entrypoint** field, formatted as `module.qualname`;
- a **Version** field when `flow.version` is not `None`;
- a **Signature** field from `inspect.signature(flow.fn)`;
- the `flow.description` docstring, normalized with `inspect.cleandoc` and
  parsed as reStructuredText;
- any directive body content, after the description.

A flow with no docstring or description renders normally; the description is
simply omitted.

## Descriptions

By default, the description comes from `flow.description`, which Prefect fills
from the function docstring (or from an explicit `description=` on `@flow`).
Docstrings are always treated as reStructuredText.

Use an external file to keep long descriptions out of the docstring:

```rst
.. prefect-flow:: flows.eda
   :description-from: descriptions/eda.rst
```

To write the description in Markdown, install the `markdown` extra and point
`:description-from:` at a `.md` or `.markdown` file:

```rst
.. prefect-flow:: flows.eda
   :description-from: descriptions/eda.md
```

```markdown
# EDA pipeline

The flow extracts a sample and loads it unless `dry_run` is true.

- reproducible with a seed
- safe to rerun

See [the Prefect docs](https://docs.prefect.io/) for details.
```

The format is chosen by file extension:

- `.rst` files are parsed as reStructuredText.
- `.md` and `.markdown` files are parsed as MyST Markdown when `myst-parser`
  is installed. Headings, lists, code blocks, links, and inline markup render
  as normal Sphinx content. Headings nest beneath the generated flow section.
- Docstrings are always reStructuredText, even if they contain Markdown-like
  syntax. Markdown applies to external files only.
- If a Markdown file is used without the extra, the build warns and omits the
  description. The warning names `sphinx-contrib-prefect[markdown]`, and under
  `prefect_on_error = "error"` the same message fails the build.
- The path is resolved relative to the Sphinx source directory (the directory
  containing `conf.py`), not the current document.
- Successful reads are registered as build dependencies, so editing the
  description rebuilds the page.
- A missing file follows `prefect_on_error` and renders no description.

The external file replaces the docstring description. The directive body is
still appended after it.

## Main-flow markers

A flow can be marked as a **main flow** in its docstring using any of three
forms:

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

Rules:

- `@mainflow` must be a standalone docstring line. It is literal text, not a
  Python decorator.
- YAML frontmatter is parsed only at the start of the docstring.
  `mainflow: true` selects the flow; `mainflow: false` does not.
- `:mainflow:` and `:mainflow: true` select the flow; `:mainflow: false` does
  not. The field must be at the top level of the docstring; an indented
  `:mainflow:` inside a literal block is not a marker.
- Any true marker wins over a false marker, and the conflict emits a warning.
- All marker syntax is stripped from the rendered description.
- Explicit selection with `.. prefect-flow::` always wins. Markers drive
  automatic selection in `prefect-flow-index`.
- Malformed YAML or an invalid marker value follows `prefect_on_error`.

## Indexing main flows

`prefect-flow-index` scans configured modules and renders one
`prefect-flow`-style section per selected flow on the current page. Configure
the scan in `conf.py`:

```python
prefect_modules = ["flows", "more_flows"]
prefect_main_flows = ["flows.eda", "reports.daily"]
```

Then place the directive on the index page:

```rst
Main flows
==========

.. prefect-flow-index::
```

A flow is selected when its docstring has a true main-flow marker or when its
entrypoint appears in `prefect_main_flows`. Explicit entries are useful for
flows you do not want to modify, including flows outside `prefect_modules`.

The directive:

- imports every module in `prefect_modules`;
- inspects module-level attributes for Prefect `Flow` objects;
- deduplicates selections by entrypoint;
- renders sections in `prefect_modules` order, then attribute order;
- appends explicit `prefect_main_flows` entries outside the scanned modules in
  configuration order;
- warns and renders nothing when no flows are selected.

For example, with two marked flows and one unmarked flow in `flows`, only the
two marked flows render. A flow named in both `prefect_main_flows` and a
scanned module still renders once.

The directive takes no arguments. The `:show-dag:` and `:no-dag:` options are
accepted for forward compatibility; they will apply to every generated section
once the runtime DAG lands in
[#7](https://github.com/szerming/sphinx-prefect/issues/7).

Module scanning imports user modules, so import-time side effects run during
the build. Only point `prefect_modules` at modules that are safe to import.

## Error handling

Missing modules, missing attributes, and objects that are not Prefect `Flow`
instances are recoverable errors.

By default they produce a source-located Sphinx warning and the directive
renders nothing:

```python
prefect_on_error = "warn"
```

To fail CI on these failures:

```python
prefect_on_error = "error"
```

With strict mode, the same problems raise a Sphinx error and stop the build.
Typical causes are:

- the flow package is not on `sys.path` in `conf.py`;
- the entrypoint has a typo;
- the directive points at a `@task` or a plain function instead of a `@flow`;
- a `:description-from:` path does not exist or cannot be read;
- a `.md` description is used without the `markdown` extra;
- a docstring marker has malformed YAML or an invalid value;
- a module in `prefect_modules` or a `prefect_main_flows` entry cannot be
  imported or does not name a Prefect flow.

## Current limitations and safety

- Parameter tables, Pydantic models, graphs, and subflow/task sections are
  tracked in the [issue tracker](https://github.com/szerming/sphinx-prefect/issues).
- Docstrings and external `.rst` files are treated as reStructuredText.
  External Markdown descriptions are opt-in through the `markdown` extra and
  are parsed as MyST; MyST docstrings are not supported.
- `prefect-flow-index` imports configured modules during the build. It does not
  sandbox them, so import-time side effects are possible.
- The directive imports the flow's module but does not execute the flow body.
  The planned runtime DAG feature will execute it when explicitly enabled; see
  [ADR-0001](adr/0001-runtime-prefect-dag.md).
- Runtime graph generation observes one execution path, so it cannot show
  branches that were not taken. Subflows are rendered as leaves.
- The extension targets Sphinx 9. It is not tested with Sphinx 8.

## Further reading

- [v0.1 specification](specs/0001-sphinx-prefect-v0.1.md) — full behavior and
  acceptance criteria.
- [ADR-0002](adr/0002-standalone-directives.md) — why the extension uses
  standalone directives instead of autodoc documenters.
- [Glossary](../GLOSSARY.md) — project terminology.
- [Coding guide](../coding-guide.md) — development setup and conventions.
