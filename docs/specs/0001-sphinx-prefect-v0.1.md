# sphinx-contrib-prefect v0.1

- **Status:** Approved for implementation planning
- **Date:** 2026-10-19
- **Package:** `sphinx-contrib-prefect`
- **Import:** `sphinxcontrib.prefect`
- **Repository:** `szerming/sphinx-prefect`
- **License:** MIT
- **ADRs:** [0001](../adr/0001-runtime-prefect-dag.md), [0002](../adr/0002-standalone-directives.md), [0003](../adr/0003-delegate-pydantic-rendering.md), [0004](../adr/0004-docstring-markers-and-module-scan.md)
- **Language:** See [GLOSSARY.md](../../GLOSSARY.md)

## 1. Summary

`sphinx-contrib-prefect` is a Sphinx extension that generates documentation for Prefect flows. Given an importable flow, it renders:

- the flow's description and signature;
- a parameter table, including Pydantic model field documentation;
- a Mermaid flow graph produced by Prefect's runtime visualization;
- sections for the subflows and tasks observed in that graph.

It also supports module scanning: flows marked in their docstrings can be discovered and rendered as an index page.

The extension does not use static AST analysis. It uses Prefect's built-in `Flow.generate_mermaid_graph()`, which executes the flow body. Runtime DAG generation is therefore opt-in.

## 2. Problem

Prefect exposes flow, task, and parameter metadata, but it has no native Sphinx integration. Documenting a flow currently requires hand-writing its description, parameter table, model fields, and graph. Prefect's graph APIs are runtime-oriented, and the existing `sphinxcontrib-prefectviz` extension targets Prefect 1.x and is abandoned.

Docs authors need a directive that turns a flow object into a complete documentation section while keeping the build offline from any Prefect server.

## 3. Goals

- Render a complete flow page from an importable flow object.
- Document scalar parameters and Pydantic model parameters.
- Render Prefect's Mermaid flow graph without requiring a Prefect server.
- Document subflows and tasks observed during graph generation.
- Support explicit flow selection and docstring-marker module scanning.
- Fail predictably: warnings by default, strict mode for CI.
- Work with Sphinx 9 and HTML output; degrade gracefully for text/man and document LaTeX requirements.

## 4. Non-goals

- Replacing Prefect's runtime graph with a static analyzer.
- Recursively executing subflows to build a multi-level graph.
- Capturing flows started through `arun_deployment()` / `run_deployment()`.
- Executing flows or tasks in a subprocess or sandbox.
- Custom rendering of Pydantic fields, validators, or JSON schema.
- A custom Sphinx object domain for flows and tasks.
- Source links (“View source”) in v0.1.
- Supporting Prefect 2, Pydantic v1, or Sphinx 8.
- Automatic creation of one `.rst` file per flow.

## 5. User contract

### 5.1 Installation

```bash
pip install sphinx-contrib-prefect
```

The `markdown` extra adds MyST Markdown support for external descriptions:

```bash
pip install "sphinx-contrib-prefect[markdown]"
```

### 5.2 `conf.py`

```python
extensions = [
    "sphinx.ext.autodoc",
    "sphinxcontrib.pydantic",
    "sphinxcontrib.mermaid",
    "sphinxcontrib.prefect",
]

prefect_modules = ["mypkg.flows"]
prefect_main_flows = ["mypkg.flows.eda"]
prefect_dag_enabled = False
prefect_dag_sample_args = {
    "mypkg.flows.eda": {"seed": 42},
}
prefect_on_error = "warn"
```

`setup()` loads `sphinx.ext.autodoc`, `sphinxcontrib.pydantic`, and `sphinxcontrib.mermaid` itself, so the explicit entries above are not strictly required. Keeping them visible documents the dependency order. `sphinxcontrib.pydantic` must be loaded after `sphinx.ext.autodoc`.

### 5.3 Directives

#### `prefect-flow`

Renders the complete flow section.

```rst
.. prefect-flow:: mypkg.flows.eda

   Optional body content is appended after the generated description.
```

Options:

- `:show-dag:` — enable the runtime DAG for this flow.
- `:no-dag:` — suppress the DAG when `prefect_dag_enabled = True`.
- `:description-from: <path>` — use an external RST or MyST file for the description.

The directive accepts `module.qualname` or `module:qualname`.

#### `prefect-params`

Renders the flow signature, scalar parameter table, and Pydantic model sections without the description or DAG.

```rst
.. prefect-params:: mypkg.flows.eda
```

#### `prefect-dag`

Renders the runtime Mermaid graph and the observed subflow/task sections, without the flow description or parameter table.

```rst
.. prefect-dag:: mypkg.flows.eda
```

Using `prefect-dag` explicitly opts into execution; the global `prefect_dag_enabled` flag is not required.

#### `prefect-flow-index`

Scans `prefect_modules` for marked flows and renders one `prefect-flow` section per flow on the current page.

```rst
.. prefect-flow-index::
```

The directive takes no arguments. It also includes flows named in `prefect_main_flows`. Separate pages remain an explicit choice: put one `prefect-flow` directive in each `.rst` file.

Options:

- `:show-dag:` / `:no-dag:` — apply to every generated section.

### 5.4 Configuration values

| Name | Type | Default | Rebuild | Purpose |
| --- | --- | --- | --- | --- |
| `prefect_modules` | `list[str]` | `[]` | `env` | Modules scanned by `prefect-flow-index` |
| `prefect_main_flows` | `list[str]` | `[]` | `env` | Entrypoints that are main flows regardless of markers |
| `prefect_dag_enabled` | `bool` | `False` | `env` | Enable runtime DAG generation for `prefect-flow` |
| `prefect_dag_sample_args` | `dict[str, dict[str, object]]` | `{}` | `env` | Sample arguments keyed by flow entrypoint |
| `prefect_on_error` | `str` | `"warn"` | `env` | `"warn"` continues; `"error"` fails the build |

## 6. Behavioral specification

### 6.1 Object resolution

1. Split the directive argument on the last `:` if present; otherwise split on the last `.`.
2. Import the module with `importlib.import_module()` lazily inside the directive.
3. Traverse the remaining dotted path with `getattr`.
4. Require the resolved object to be a Prefect `Flow`; otherwise report an error.
5. Report a source-located warning or error for import failures, missing attributes, and wrong object types.

The extension must not import user modules during `setup()`.

### 6.2 Flow metadata

The section contains:

- **Title:** `flow.name` (Prefect's flow name, e.g. `eda`).
- **Entrypoint:** `f"{flow.fn.__module__}.{flow.fn.__qualname__}"`.
- **Version:** `flow.version` when not `None`.
- **Signature:** `inspect.signature(flow.fn)`.
- **Description:** resolved as described in §6.3.

Prefect names use hyphens where the Python function uses underscores; display the Prefect name as the title and the entrypoint as the technical identifier.

### 6.3 Description resolution

1. If `:description-from:` is present, read that file relative to the Sphinx source directory (`conf.py`).
2. Otherwise use `flow.description`; Prefect sets this to the explicit `description=` value or the function docstring.
3. If `Flow.description` is explicit and the docstring contains a marker, the marker is still used for selection but is not part of the description.
4. Strip all marker syntax (§6.8) from the rendered description.
5. Normalize indentation with `inspect.cleandoc`.
6. Parse RST with `nested_parse`.
7. For a `.md` file, use MyST when `myst-parser` is installed; otherwise emit a warning (or error under `prefect_on_error = "error"`).
8. Docstrings are treated as RST in v0.1. MyST applies to external files only.

External description paths are resolved relative to the Sphinx source directory, not the current document.

### 6.4 Parameter table

Use `flow.parameters.model_dump()` for the canonical parameter metadata. Sort by the schema's `position` field.

Each row shows:

- parameter name;
- type;
- required/optional;
- default value (or “factory” where applicable);
- description.

Prefect extracts descriptions from Google-style `Args:` sections. Sphinx/NumPy-style parameter sections will not populate descriptions automatically; document this. When the annotation is a Pydantic model, the type links to the generated model section.

If the flow has no parameters, omit the table.

### 6.5 Pydantic model documentation

Model rendering is delegated to `sphinxcontrib-pydantic` (see ADR-0003). The extension:

1. Reads annotations with `typing.get_type_hints(flow.fn, include_extras=True)`.
2. Recursively unwraps `Annotated`, `Optional`/`Union`, `list`, `dict`, `tuple`, `set`, and `RootModel`.
3. Collects classes that are Pydantic v2 `BaseModel` subclasses.
4. Recurses through `model_fields` annotations, using a seen set keyed by `(module, qualname)` to handle cycles.
5. Accepts only importable module-level classes: `getattr(importlib.import_module(cls.__module__), cls.__name__) is cls`.
6. Emits a nested `pydantic-model` block for each model:

```rst
.. pydantic-model:: mypkg.models.Config
   :show-field-summary:
   :show-validator-summary:
   :show-members:
```

`:show-members:` is required for `Field(description=...)` text; the summary table has no description column.

Deduplicate models across the build. The first occurrence registers Python-domain objects; later occurrences use `:noindex:` so Sphinx does not warn about duplicates. Do not use `:noindex:` on the first occurrence.

Pydantic v2 only. Pydantic v1 models, dynamically generated models, local classes, and models that are not importable produce a warning and are omitted. Computed fields are not rendered in v0.1.

Scalar parameters use the parameter table, not a model block.

### 6.6 Runtime DAG

The DAG is generated with Prefect's `Flow.generate_mermaid_graph(**sample_args)`. This executes the flow body.

Enablement:

- `prefect-flow` generates the DAG when `:show-dag:` is present, or when `prefect_dag_enabled = True` and `:no-dag:` is absent.
- `prefect-dag` always attempts generation.
- `prefect-flow-index` applies its `:show-dag:` / `:no-dag:` option to every section.

Arguments:

- Look up `prefect_dag_sample_args[entrypoint]`.
- If the flow has required parameters and no entry exists, warn and omit the DAG.
- If the flow has no required parameters, `{}` is valid.
- Missing or invalid arguments produce a warning (or an error under strict mode), not a traceback.

Rendering:

- Emit a `sphinxcontrib.mermaid.mermaid` node with `code` and `options` attributes.
- Parse the returned Mermaid to identify node names and edges.
- Strip Prefect's duplicate-node suffix (`-0`, `-1`, …) when matching names to objects.
- Add `classDef` styles for main flow, subflow, task, and unknown nodes, and render a legend.
- Add a main-flow node if Prefect's graph does not include one, with edges to root nodes.
- If no tasks or subflows were observed, render a short note instead of an empty diagram.
- Do not add hyperlinks inside the Mermaid graph in v0.1. Links belong in the subflow/task sections.

Limitations that must be documented:

- One execution path is observed; branches not taken do not appear.
- A subflow is a leaf; its internal tasks are not expanded.
- `arun_deployment()` / `run_deployment()` children are not tracked.
- `.submit()`, `.map()`, and `.apply_async()` raise Prefect's `VisualizationUnsupportedError`; warn and omit the graph.
- Code relying on `prefect.runtime` may fail without a flow-run context; warn and omit the graph.
- The flow body may perform I/O, read credentials, or write files. Enabling the DAG is an explicit trust decision.

### 6.7 Subflow and task sections

Subflow/task discovery depends on the runtime DAG. If the DAG is disabled, only the flow's own documentation is generated.

For each node in the generated graph:

1. Strip the duplicate suffix and match the name against `Flow.name` and `Task.name` in the flow's module.
2. If exactly one match exists, render a section for it.
3. If multiple matches exist, warn and show the name without a link.
4. If no match exists, list it as an unknown node without a link.

A subflow section contains its title, entrypoint, description, signature, parameter table, and Pydantic model sections. A task section contains its title, description, signature, parameter table, and Pydantic model sections. Task metadata comes from `task.fn`; Task has no `.parameters`, so use `inspect.signature(task.fn)` and `prefect.utilities.callables.parameter_schema(task.fn)`.

Subflows are not recursively graphed. To document a subflow's internals, add a separate `prefect-flow` or `prefect-dag` directive for it.

Each documented flow and task gets a stable anchor (`prefect-flow-<slug>`, `prefect-task-<slug>`). Matching names in prose and tables use RST cross-references; unknown names remain plain text.

### 6.8 Main-flow markers

A flow is marked as a main flow by any of:

1. A standalone `@mainflow` line in the docstring:

```python
@flow
def eda(seed: int = 1):
    """Run the EDA build.

    @mainflow
    """
```

2. YAML frontmatter at the start of the docstring:

```python
@flow
def eda(seed: int = 1):
    """---
    mainflow: true
    ---
    Run the EDA build.
    """
```

3. A reST field anywhere in the docstring:

```python
@flow
def eda(seed: int = 1):
    """Run the EDA build.

    :mainflow:
    """
```

Rules:

- `@mainflow` is a literal docstring line, not a Python decorator. Match `^\s*@mainflow\s*$`.
- YAML frontmatter is parsed only at the start of the docstring. `mainflow: true` selects; `mainflow: false` does not.
- `:mainflow:` and `:mainflow: true` select; `:mainflow: false` does not.
- Any true marker wins over a false marker; conflicting markers emit a warning.
- Explicit selection (directive or `prefect_main_flows`) overrides markers.
- All marker syntax is stripped from the rendered description.
- Malformed YAML produces a warning (or an error under strict mode).

### 6.9 Module scan and index

`prefect-flow-index`:

1. Imports each module in `prefect_modules`.
2. Iterates module-level attributes and collects `Flow` objects.
3. Selects flows that have a true marker and flows named in `prefect_main_flows`.
4. Deduplicates by entrypoint.
5. Renders one section per selected flow, in module order and attribute order.
6. Notes source dependencies for every imported flow and task.
7. Warns if no flows are found.

`prefect_main_flows` entries outside `prefect_modules` are imported explicitly and included. A flow named in `prefect_main_flows` is a main flow even without a marker.

### 6.10 Errors and diagnostics

`prefect_on_error` controls recoverable failures:

- `"warn"` (default): emit a Sphinx warning with the directive location and continue.
- `"error"`: raise a Sphinx error and fail the build.

Errors include: import failure, missing attribute, wrong object type, malformed marker, missing MyST parser, missing/invalid DAG arguments, DAG execution failure, non-importable Pydantic model, and Pydantic v1 model.

A missing description or empty parameter list is not an error; render nothing for that part.

### 6.11 Incremental builds and parallelism

- Register configuration values with rebuild type `"env"`.
- Call `env.note_dependency()` for flow and task source files, and for external description files.
- Set `parallel_read_safe = False` because DAG generation executes user code.
- Set `parallel_write_safe = True`.
- Do not add a custom DAG cache in v0.1; rely on Sphinx incremental rebuilds and dependency tracking.

### 6.12 Builders

- **HTML:** primary target; Mermaid renders via `sphinxcontrib-mermaid`.
- **text/man:** tables and sections render; Mermaid degrades to the placeholder emitted by `sphinxcontrib-mermaid`.
- **LaTeX/PDF:** Mermaid requires the `mmdc` binary; document this and rely on `sphinxcontrib-mermaid`'s warning/skip behavior when it is absent.

## 7. Architecture

```
src/
  sphinxcontrib/
    prefect/
      __init__.py       # setup(), config registration, directives
      _import.py        # lazy module/object resolution
      _markers.py       # docstring marker parsing
      _description.py   # RST/MyST description rendering
      _params.py        # parameter table
      _models.py        # Pydantic model discovery and pydantic-model output
      _dag.py           # Prefect runtime DAG invocation and Mermaid post-processing
      _graph.py         # Mermaid parsing, styling, node matching
      _render.py        # shared doctree/section helpers
      _directives.py    # prefect-flow, prefect-params, prefect-dag, prefect-flow-index
tests/
  conftest.py
  roots/
    test-flow/
    test-index/
    test-dag/
    test-errors/
  test_*.py
docs/
  ...
```

`src/sphinxcontrib/` has no `__init__.py`; it is a native PEP 420 namespace package.

`setup()` must:

- call `app.require_sphinx("9.0")`;
- load `sphinx.ext.autodoc`, `sphinxcontrib.pydantic`, and `sphinxcontrib.mermaid`;
- register the config values;
- register the four directives;
- return `parallel_read_safe: False`, `parallel_write_safe: True`, and the package version.

Import Prefect and user modules lazily inside directive execution, not during extension import.

## 8. Compatibility

| Component | Supported |
| --- | --- |
| Python | `>=3.12,<3.15` (development on 3.13) |
| Sphinx | `>=9,<10` |
| Prefect | `>=3,<4` (tested against 3.8.x) |
| Pydantic | `>=2.10,<3` |
| PyYAML | `>=5.4,<7` |
| sphinxcontrib-mermaid | `>=2.1,<3` |
| sphinxcontrib-pydantic | `>=0.4,<0.5` |
| MyST | optional, only for `.md` descriptions |

## 9. Testing

Use `sphinx.testing.fixtures` with test roots under `tests/roots/`.

Required integration cases:

- A flow with a docstring, scalar parameters, a Pydantic parameter, two tasks, and one subflow renders all sections.
- The Mermaid node exists and contains the expected `flowchart` text.
- The graph's task/subflow nodes match module objects and produce sections.
- `prefect-flow-index` discovers marked flows from `prefect_modules`.
- All three marker forms work; explicit selection overrides a marker; markers are stripped.
- `:description-from:` renders an RST file; `.md` renders when MyST is installed and warns when it is not.
- Missing module, missing attribute, wrong object type, missing DAG args, DAG execution failure, and non-importable Pydantic model follow `prefect_on_error`.
- Text builder builds without crashing.
- No Prefect server is required: run DAG tests with `PREFECT_API_URL` pointing at a dead port for a pure flow.
- A flow using `.submit()` produces a warning and no graph.
- Duplicate Pydantic models across pages do not produce duplicate-object warnings.

Commands (planned):

```bash
uv sync --all-extras
uv run ruff format --check .
uv run ruff check .
uv run pytest
```

CI matrix: Python 3.12 and 3.13, Sphinx 9.x, Prefect 3.8.x, plus a job with the `markdown` extra. Build the extension's own docs with `-W`.

## 10. Acceptance criteria

- [ ] A minimal Sphinx project can load `sphinxcontrib.prefect` and build a flow page.
- [ ] The page shows the flow description, entrypoint, signature, and parameter table.
- [ ] Pydantic parameter models render with fields, types, defaults, and descriptions.
- [ ] A runtime Mermaid graph renders when explicitly enabled with sample arguments.
- [ ] Observed subflows and tasks get sections and cross-references.
- [ ] `prefect-flow-index` renders marked flows from `prefect_modules`.
- [ ] All three marker forms select a flow and are stripped from the description.
- [ ] DAG generation requires no Prefect server for pure flows.
- [ ] Missing imports, DAG failures, and unsupported models warn by default and fail under `prefect_on_error = "error"`.
- [ ] The text builder does not crash.
- [ ] The happy-path docs build is warning-free with `-W`.
- [ ] No implementation imports user flow modules during `setup()`.

## 11. Risks and limitations

| Risk | Mitigation |
| --- | --- |
| Runtime DAG executes arbitrary flow code | Opt-in; document side effects; sample args; warn/skip; no default execution |
| Only one execution path is observed | Document; users can provide different sample args per build |
| Subflows are leaves | Document; separate directive for subflow internals; recursive graphs are future work |
| Deployment-spawned flows are invisible | Document; explicit directives for child flows |
| `.submit`/`.map`/`.apply_async` unsupported | Catch `VisualizationUnsupportedError`; warn and omit |
| `prefect.runtime` requires a flow-run context | Catch `MissingContextError`; warn and omit |
| `sphinxcontrib-pydantic` is young and uses private Sphinx helpers | Pin `<0.5`; integration tests; delegate only rendering |
| `sphinxcontrib-mermaid` node API is not formally stable | Pin `<3`; assert rendered HTML in tests |
| Import-time side effects in user modules | Lazy imports; warnings; document; no sandbox in v0.1 |
| Name collisions in Mermaid nodes | Strip suffixes; ambiguous matches warn and stay unlinked |

## 12. Ticket map

| # | Ticket | Depends on |
| --- | --- | --- |
| [01](https://github.com/szerming/sphinx-prefect/issues/1) | Scaffold package, tooling, and CI | — |
| [02](https://github.com/szerming/sphinx-prefect/issues/2) | Core `prefect-flow` directive | [#1](https://github.com/szerming/sphinx-prefect/issues/1) |
| [03](https://github.com/szerming/sphinx-prefect/issues/3) | Markers and RST descriptions | [#2](https://github.com/szerming/sphinx-prefect/issues/2) |
| [04](https://github.com/szerming/sphinx-prefect/issues/4) | MyST Markdown descriptions | [#3](https://github.com/szerming/sphinx-prefect/issues/3) |
| [05](https://github.com/szerming/sphinx-prefect/issues/5) | Module scan and `prefect-flow-index` | [#3](https://github.com/szerming/sphinx-prefect/issues/3), [#4](https://github.com/szerming/sphinx-prefect/issues/4) |
| [06](https://github.com/szerming/sphinx-prefect/issues/6) | Parameters and Pydantic models | [#2](https://github.com/szerming/sphinx-prefect/issues/2) |
| [07](https://github.com/szerming/sphinx-prefect/issues/7) | Runtime DAG and Mermaid rendering | [#2](https://github.com/szerming/sphinx-prefect/issues/2) |
| [08](https://github.com/szerming/sphinx-prefect/issues/8) | Subflow/task discovery and cross-references | [#6](https://github.com/szerming/sphinx-prefect/issues/6), [#7](https://github.com/szerming/sphinx-prefect/issues/7) |
| [09](https://github.com/szerming/sphinx-prefect/issues/9) | Error policy, dependencies, and parallel safety | [#2](https://github.com/szerming/sphinx-prefect/issues/2)–[#8](https://github.com/szerming/sphinx-prefect/issues/8) |
| [10](https://github.com/szerming/sphinx-prefect/issues/10) | Documentation, example project, and release | [#1](https://github.com/szerming/sphinx-prefect/issues/1)–[#9](https://github.com/szerming/sphinx-prefect/issues/9) |

Published tickets: [#1](https://github.com/szerming/sphinx-prefect/issues/1)–[#10](https://github.com/szerming/sphinx-prefect/issues/10). Local drafts live in [`docs/tickets/`](../tickets/) and carry the same issue links.

## 13. Future work

- Opt-in static analysis as an alternative to runtime DAG generation.
- Recursive subflow graphs with per-flow sample arguments.
- Hooks for `run_deployment()` / `arun_deployment()` edges.
- MyST docstrings (not only external files).
- Source links and `viewcode` integration.
- A custom `prefect` Sphinx domain for flows and tasks.
- Subprocess isolation with timeouts for runtime DAG generation.
- DAG caching keyed by source hash and sample arguments.
- Cross-page model links and computed-field rendering.
- Pydantic v1 compatibility.
- Sphinx 8 support.

## 14. References

- Prefect, “Visualize workflow structure”: <https://docs.prefect.io/v3/how-to-guides/workflows/visualize-workflow-structure>
- Prefect `Flow.generate_mermaid_graph`: `prefect/flows.py` in Prefect 3.8.x
- Sphinx, “Developing extensions”: <https://www.sphinx-doc.org/en/master/extdev/index.html>
- Sphinx, “Testing extensions”: <https://www.sphinx-doc.org/en/master/extdev/testing.html>
- Sphinx 9 autodoc rewrite: <https://www.sphinx-doc.org/en/master/changes/9.0.html>
- `sphinxcontrib-mermaid`: <https://github.com/mgaitan/sphinxcontrib-mermaid>
- `sphinxcontrib-pydantic`: <https://github.com/mscheltienne/sphinxcontrib-pydantic>
- Obsolete prior art, `sphinxcontrib-prefectviz`: <https://github.com/sphinx-contrib/prefectviz>
