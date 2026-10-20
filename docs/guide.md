# Usage guide

This guide shows how to document Prefect flows in a Sphinx project with
`sphinx-contrib-prefect`.

The guide describes the currently implemented `prefect-flow`,
`prefect-params`, `prefect-dag`, and `prefect-flow-index` directives and marks
features that are planned for the rest of v0.1. For the full design, see
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
| Source-located diagnostics and rebuild dependencies | Available |
| Parameter tables from Prefect's parameter schema | Available |
| Pydantic model documentation with nested models | Available |
| Runtime Mermaid flow graph with `:show-dag:` and `prefect-dag` | Available |
| Subflow/task sections and cross-references | Available |

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

Supported versions: Python 3.12–3.13, Sphinx 9.x, Prefect 3.x, and Pydantic 2.x.
The package declares `requires-python = ">=3.12,<3.15"`; CI runs Python 3.12
and 3.13.

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

# Optional: runtime DAG generation. It executes the flow body, so it is off by
# default. Sample arguments are keyed by flow entrypoint.
prefect_dag_enabled = False
prefect_dag_sample_args = {
    "flows.eda": {"records": 10},
}
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

- a section titled with `flow.name` and the stable anchor
  `prefect-flow-<entrypoint>`;
- an **Entrypoint** field, formatted as `module.qualname`;
- a **Version** field when `flow.version` is not `None`;
- a **Signature** field from `inspect.signature(flow.fn)`;
- the `flow.description` docstring, normalized with `inspect.cleandoc` and
  parsed as reStructuredText;
- a **Parameters** table when the flow declares parameters;
- a `pydantic-model` block for each Pydantic model used by a parameter,
  including nested models;
- a styled Mermaid flow graph when a runtime DAG is enabled;
- **Subflows**, **Tasks**, and **Unknown nodes** sections for the graph's
  matched and unresolved nodes;
- any directive body content, after all generated content.

A flow with no docstring or description renders normally; the description is
simply omitted. A flow with no parameters omits the parameter table.

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

## Parameters and Pydantic models

Prefect derives `flow.parameters` from the function signature. The directive
reads that schema, sorts parameters by their signature position, and renders a
table with these columns:

| Column | Contents |
| --- | --- |
| Parameter | The parameter name, in code style |
| Type | The annotation, with links to documented Pydantic models |
| Required | `Required` or `Optional` |
| Default | The default value, `factory` for a `default_factory`, or `—` when there is no default |
| Description | Text from the docstring's Google-style `Args:` section |

Descriptions must use Google-style `Args:` sections. Sphinx/NumPy-style
parameter sections do not populate this table automatically. A missing
description leaves the cell empty.

Pydantic v2 models used as parameters are documented with
`sphinxcontrib-pydantic`. For example:

```python
from pydantic import BaseModel, Field


class Address(BaseModel):
    """A postal address."""

    street: str = Field(description="Street line.")
    city: str = Field(default="Springfield", description="City name.")


class Profile(BaseModel):
    """A user profile."""

    name: str = Field(description="Display name.")
    address: Address = Field(description="Where the user lives.")


@flow
def eda(profile: Profile) -> None:
    """Run the analysis.

    Args:
        profile: Profile of the user running the analysis.
    """
```

The `Profile` parameter links to a generated model block. Both `Profile` and
its nested `Address` model get their own block with a field summary, validator
summary, and detailed field documentation, so `Field(description=...)` text
appears. Recursive models terminate safely and are rendered once per build.
The first occurrence in the build indexes the model; repeated models later in
the build use `:noindex:` so Sphinx does not emit duplicate-object warnings.

Only importable module-level Pydantic v2 models can be documented. Local
classes, nested classes, dynamically generated classes that cannot be imported
by name, and Pydantic v1 models are omitted with a diagnostic. Under
`prefect_on_error = "error"` that diagnostic fails the build.

To render the flow's entrypoint and version, signature, parameter table, and
model blocks without the description or flow graph, use `prefect-params`:

```rst
.. prefect-params:: flows.eda
```

The directive accepts the same `module.qualname` and `module:qualname`
entrypoint forms as `prefect-flow`.

## Runtime flow graphs

Flow graphs are produced by Prefect's `Flow.generate_mermaid_graph()`. That API
executes the flow body under Prefect's visualization tracker, so graph
generation is not side-effect-free. It is always opt-in:

- `:show-dag:` on `prefect-flow` or `prefect-flow-index` enables the graph for
  those sections;
- `prefect_dag_enabled = True` enables it for every `prefect-flow` section
  unless the directive uses `:no-dag:`;
- `prefect-dag` always attempts generation and renders the graph without the
  flow description or parameter table;
- `:show-dag:` wins when a directive has both `:show-dag:` and `:no-dag:`.

```rst
.. prefect-flow:: flows.eda
   :show-dag:
```

```rst
.. prefect-dag:: flows.eda
```

The graph needs sample arguments for required flow parameters. Configure them
by canonical entrypoint:

```python
prefect_dag_sample_args = {
    "flows.eda": {"records": 10},
}
```

A flow without required parameters runs with `{}`. If required parameters have
no configured values, the directive warns and omits the graph. Invalid
argument names or values, `.submit()` / `.map()` / `.apply_async()` calls,
code that needs an active flow-run context, and other execution failures also
warn and omit the graph by default. Under `prefect_on_error = "error"` they
fail the build instead.

Prefect passes sample argument values directly to the flow function. It does
not validate them against the flow's Pydantic parameter model, so a parameter
whose annotation is a model needs a model instance in `conf.py`:

```python
from flows.models import ReportConfig

prefect_dag_sample_args = {
    "flows.eda": {"config": ReportConfig(title="Weekly revenue")},
}
```

A plain dictionary is not coerced and usually fails while the flow body runs.
The [example project](https://github.com/szerming/sphinx-prefect/tree/main/examples/demo)
has a complete `prefect_dag_sample_args` entry with a nested model.

The rendered diagram adds a main-flow node when Prefect's output omits it,
draws edges from the main flow to the graph's root nodes, and applies
`classDef` styles: indigo for the main flow, blue for subflows, green for
tasks, and amber for unknown nodes. It appears under a **Flow graph** heading,
and a text legend names each color. The `prefect-dag` directive gives its
section the stable anchor `prefect-dag-<slug>`. When the flow body calls
neither tasks nor subflows, the directive renders a short note instead of an
empty diagram.

Unknown nodes are graph names that cannot be matched to a `Flow` or `Task`
object in the flow's module. A name that matches more than one object is also
styled as unknown and emits a warning.

### Subflow and task sections

When a runtime graph runs, every node that matches a module-level `Flow` or
`Task` object is also documented below the graph. `prefect-flow` renders these
sections only when the graph is enabled; `prefect-dag` always attempts the
graph and therefore always documents the nodes it observes.

The generated **Subflows** section contains one child section per matched
subflow with its title, entrypoint, signature, description, parameter table,
and Pydantic model blocks. The **Tasks** section does the same for tasks, using
`inspect.signature(task.fn)` and Prefect's `parameter_schema(task.fn)` for the
signature and parameter metadata. Task descriptions come from
`task.description`, which Prefect fills from the task docstring or an explicit
`description=` on the task decorator.

Each section starts with a short bullet list whose names link to the detailed
sections. The anchors are stable and entrypoint-based:
`prefect-flow-<entrypoint>` for flows and `prefect-task-<entrypoint>` for
tasks. The Mermaid graph itself contains no links; links live in these lists.

A subflow is a leaf. Its section documents the subflow object, but its internal
tasks are not listed under the main flow and no recursive graph is generated.
To document a subflow's internals, use a separate `prefect-flow` or
`prefect-dag` directive for that subflow.

Nodes that cannot be matched are listed under **Unknown nodes** without links,
with a note saying whether the name was ambiguous or external. A name shared
by multiple `Flow` or `Task` objects emits a warning and stays unlinked. Flows
started through `arun_deployment()` or `run_deployment()` never appear in the
graph, so they are not documented automatically; add explicit directives for
them.

### Graph limitations and safety

- Enabling a graph is an explicit decision to execute user flow code. The body
  may perform I/O, read credentials, or write files. There is no sandbox.
- One execution path is observed. Branches that the sample arguments do not
  take do not appear.
- Subflows appear as leaf nodes. Their internal tasks are not expanded; use a
  separate directive to document a subflow's internals.
- Flows started with `arun_deployment()` or `run_deployment()` are not tracked.
- A pure flow needs no Prefect server. The build can run with
  `PREFECT_API_URL` pointing at an unreachable address.
- The HTML builder uses `sphinxcontrib-mermaid`'s inline rendering. The
  text/man builders emit its `[graph]` placeholder. LaTeX/PDF output needs the
  `mmdc` Mermaid CLI binary on `PATH`; without it, `sphinxcontrib-mermaid`
  warns and skips the image.
- The extension does not cache generated graphs or run flow code in a
  subprocess. Sphinx incremental rebuilds and dependency tracking apply.

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

The directive takes no arguments. The `:show-dag:` and `:no-dag:` options
apply to every generated section and follow the same enablement rules as
`prefect-flow`.

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
Warnings and errors include the directive's source location (`path:line`) and,
where available, the flow, task, module, or description file involved.

### Failure modes

| Failure | Default (`"warn"`) | `"error"` |
| --- | --- | --- |
| Module cannot be imported | Warn; omit the affected section(s) | Fail the build |
| Missing attribute or callable path | Warn; omit the affected section(s) | Fail the build |
| Object is not a Prefect `Flow` (for example a task or plain function) | Warn; omit the affected section(s) | Fail the build |
| Malformed marker YAML or invalid marker value | Warn; omit the marker and render the rest | Fail the build |
| External description file missing or unreadable | Warn; omit the description | Fail the build |
| Markdown description without MyST | Warn; omit the description | Fail the build |
| Required DAG sample arguments missing | Warn; omit the graph | Fail the build |
| Invalid `prefect_dag_sample_args` or arguments that do not match the signature | Warn; omit the graph | Fail the build |
| DAG execution failure, including `.submit()` / `.map()` and missing run context | Warn; omit the graph | Fail the build |
| Pydantic model is not importable (local, nested, or dynamic) | Warn; omit the model block | Fail the build |
| Pydantic v1 model | Warn; omit the model block | Fail the build |
| `prefect-flow-index` finds no flows | Warn; render nothing | Warn; render nothing |

A missing description or an empty parameter list is not a failure: the
directive renders nothing for that part.

Typical causes of a diagnostic are:

- the flow package is not on `sys.path` in `conf.py`;
- the entrypoint has a typo;
- the directive points at a `@task` or a plain function instead of a `@flow`;
- a `:description-from:` path does not exist or cannot be read;
- a `.md` description is used without the `markdown` extra;
- a docstring marker has malformed YAML or an invalid value;
- a runtime DAG has no sample arguments for a required parameter, receives
  invalid arguments, or fails while executing the flow body;
- a parameter's Pydantic model is a Pydantic v1 model, a local or nested
  class, or a dynamically generated class that cannot be imported by name;
- a module in `prefect_modules` or a `prefect_main_flows` entry cannot be
  imported or does not name a Prefect flow.

### Rebuilds and dependencies

Every documented flow, subflow, and task registers its source file with
`env.note_dependency()`, and a successfully read external description file is
registered too. Editing those files makes the next incremental build rewrite
the affected page. The extension does not add its own cache, so Sphinx's
dependency tracking is the single rebuild mechanism.

Runtime DAG generation executes user code, so the extension sets
`parallel_read_safe = False`. It sets `parallel_write_safe = True` and does not
use subprocess isolation in v0.1.

## Current limitations and safety

- Parameter tables and Pydantic model documentation cover flows, documented
  subflows, and observed tasks. Tasks and subflows are only documented when a
  runtime graph observes them.
- Docstrings and external `.rst` files are treated as reStructuredText.
  External Markdown descriptions are opt-in through the `markdown` extra and
  are parsed as MyST; MyST docstrings are not supported.
- `prefect-flow-index` imports configured modules during the build. It does not
  sandbox them, so import-time side effects are possible.
- `prefect-flow` imports the flow's module but does not execute the flow body
  unless a runtime DAG is enabled. Graph generation executes arbitrary flow code
  and may perform I/O; see [ADR-0001](adr/0001-runtime-prefect-dag.md).
- Runtime graph generation observes one execution path, so it cannot show
  branches that were not taken. Subflows are rendered as leaves.
- The extension targets Sphinx 9. It is not tested with Sphinx 8.

## Further reading

- [v0.1 specification](specs/0001-sphinx-prefect-v0.1.md) — full behavior and
  acceptance criteria.
- [ADR-0002](adr/0002-standalone-directives.md) — why the extension uses
  standalone directives instead of autodoc documenters.
- [Glossary](https://github.com/szerming/sphinx-prefect/blob/main/GLOSSARY.md) — project terminology.
- [Coding guide](https://github.com/szerming/sphinx-prefect/blob/main/coding-guide.md) — development setup and conventions.
