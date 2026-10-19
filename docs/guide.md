# Usage guide

This guide shows how to document Prefect flows in a Sphinx project with
`sphinx-contrib-prefect`.

The guide describes the currently implemented `prefect-flow` directive and
marks features that are planned for the rest of v0.1. For the full design, see
the [v0.1 specification](specs/0001-sphinx-prefect-v0.1.md).

## Current status

| Feature | Status |
| --- | --- |
| Resolve flows by `module.qualname` or `module:qualname` | Available |
| Flow title, entrypoint, version, signature, and RST description | Available |
| Directive body content appended after the description | Available |
| `prefect_on_error` warn/error policy | Available |
| Parameter tables and Pydantic model sections | Planned — [#6](https://github.com/szerming/sphinx-prefect/issues/6) |
| Runtime Mermaid flow graph | Planned — [#7](https://github.com/szerming/sphinx-prefect/issues/7) |
| Subflow/task sections and cross-references | Planned — [#8](https://github.com/szerming/sphinx-prefect/issues/8) |
| Module scanning with `prefect-flow-index` | Planned — [#5](https://github.com/szerming/sphinx-prefect/issues/5) |
| External RST/MyST descriptions | Planned — [#3](https://github.com/szerming/sphinx-prefect/issues/3), [#4](https://github.com/szerming/sphinx-prefect/issues/4) |

## Installation

```bash
pip install sphinx-contrib-prefect
```

Install the `markdown` extra if you plan to use MyST Markdown descriptions once
that feature lands:

```bash
pip install "sphinx-contrib-prefect[markdown]"
```

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
- the directive points at a `@task` or a plain function instead of a `@flow`.

## Current limitations and safety

- Only `prefect-flow` metadata rendering is implemented. Parameter tables,
  Pydantic models, graphs, subflow/task sections, and module scanning are
  tracked in the [issue tracker](https://github.com/szerming/sphinx-prefect/issues).
- Docstrings are treated as reStructuredText. External MyST descriptions are
  not implemented yet.
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
