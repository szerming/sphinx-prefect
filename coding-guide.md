# Coding guide

This guide is for contributors and coding agents working on
`sphinx-contrib-prefect`. Read the [README](README.md), the
[v0.1 specification](docs/specs/0001-sphinx-prefect-v0.1.md), the
[ADRs](docs/adr/), and the [glossary](GLOSSARY.md) before changing behavior.

## Development setup

Requirements: Python 3.12 or 3.13 and [`uv`](https://docs.astral.sh/uv/).

```bash
git clone git@github.com:szerming/sphinx-prefect.git
cd sphinx-prefect
uv sync --all-extras
```

Run the same checks as CI:

```bash
uv run ruff format --check .
uv run ruff check .
uv run pytest
```

Apply formatting with `uv run ruff format .`.

## Repository layout

```text
src/sphinxcontrib/prefect/
├── __init__.py       # setup(), config registration, directive registration
├── _directives.py    # directive classes and option handling
├── _import.py        # lazy module/flow resolution
├── _markers.py       # main-flow docstring marker parsing
├── _scan.py          # module scanning and main-flow selection
├── _description.py   # docstring and external-file description resolution
├── _params.py        # parameter table rendering
├── _models.py        # Pydantic model discovery and pydantic-model emission
├── _dag.py           # runtime DAG invocation and graph section rendering
├── _graph.py         # Mermaid parsing, node classification, and styling
├── _render.py        # doctree helpers and shared flow-section rendering
└── _errors.py        # prefect_on_error handling and source-located diagnostics

tests/
├── conftest.py
├── roots/
│   ├── test-flow/    # flow directive, fixture flows, models, descriptions
│   ├── test-index/   # module scan and prefect-flow-index
│   └── test-dag/     # runtime DAG graph, errors, and builder coverage
├── test_dag.py
├── test_flow_directive.py
├── test_index_directive.py
├── test_markers.py
├── test_package.py
├── test_parameters.py
└── test_scan.py

docs/
├── adr/              # architecture decision records
├── specs/            # approved specifications
├── tickets/          # local ticket drafts
└── guide.md          # user-facing usage guide
```

`src/sphinxcontrib/` is a native PEP 420 namespace package. Do not add
`src/sphinxcontrib/__init__.py`.

The specification names the remaining modules `_dag.py` and `_graph.py`.
Keep each concern in its module rather than growing `_directives.py`.

## Architecture rules

### Lazy imports

`setup()` must not import Prefect or any user flow module. Import Prefect and
user modules inside directive execution:

```python
def run(self):
    flow = resolve_flow(self.arguments[0])  # imports the user module here
    ...
```

`_import.py` owns entrypoint parsing and flow resolution. It accepts:
- `module.qualname`
- `module:qualname`

Resolution failures raise `ObjectResolutionError`, which directives convert to
warnings or build errors through `report_error()`.

### Directives

Use `SphinxDirective` from `sphinx.util.docutils`. Render with standard docutils
nodes and Sphinx parsing helpers:

```python
section.extend(directive.parse_text_to_nodes(text, allow_section_headings=True))
section.extend(directive.parse_content_to_nodes(allow_section_headings=True))
```

Every generated `nodes.section` needs a non-empty id. `_render.make_section()`
sets one from the title by default; pass `node_id=` for stable anchors when a
directive needs a namespaced id.

Build shared doctree behavior in `_render.py` instead of duplicating node
construction in directives.

### Descriptions and markers

`_markers.parse_mainflow_markers()` is a pure parser: it returns selection
state plus separate `warnings` (conflicts) and `errors` (malformed syntax).
Callers route `errors` through `report_error()`; conflicts use
`report_warning()` because they stay warnings under strict mode.

Keep marker parsing in `_markers.py` so the module scan can reuse it without
depending on a directive. Marker syntax is parsed from the raw docstring
(`flow.fn.__doc__`); when the description comes from that docstring, the
marker-stripped text is rendered. An explicit description that differs from
the docstring is rendered unchanged.

Resolve external descriptions in `_description.py`:

- paths are relative to `directive.env.srcdir`;
- external files replace the docstring description;
- `.rst` (and other non-Markdown files) are parsed as reStructuredText;
- `.md`/`.markdown` files are parsed with MyST's `SphinxRenderer`; import
  `myst_parser` lazily so the core package does not depend on the extra;
- successful reads call `env.note_dependency()`;
- missing/unreadable files and Markdown files without `myst-parser` install
  follow `prefect_on_error`.

Docstrings are always reStructuredText. Do not auto-detect Markdown in a
docstring, and do not pass Markdown through `inspect.cleandoc`.

### Parameters and models

Keep parameter table construction in `_params.py` and model discovery in
`_models.py`.

- Read parameter metadata from `flow.parameters.model_dump()` and order it by
  each property's `position`.
- Use the signature annotations (`typing.get_type_hints(..., include_extras=True)`)
  for display types and for identifying model parameters; use the Prefect schema
  for requiredness, defaults, and descriptions. `collect_flow_models()` returns
  the resolved hints so the table and model walker share one lookup.
- Link documented Pydantic models with Python-domain `pending_xref` nodes. Do
  not hand-write URLs.
- `_models.collect_flow_models()` walks `Annotated`, unions, container
  generics, and `model_fields`, keyed by `(module, qualname)` so recursive
  models terminate.
- Accept only importable module-level Pydantic v2 classes. Pydantic v1, local,
  nested, and non-importable dynamic models are diagnostics routed through
  `prefect_on_error`.
- Emit models as `pydantic-model` blocks parsed into the flow section, with
  `:show-field-summary:`, `:show-validator-summary:`, and `:show-members:`.
- Deduplicate models by checking the Python domain's registered objects: the
  first occurrence indexes, later ones add `:noindex:`.
- Directives call `collect_flow_models()` and route its errors through
  `report_diagnostics()`; `render_flow_section()` only assembles nodes.

`render_flow_section()` owns the shared order: metadata fields, optional
description, parameter table and models, optional runtime graph, then directive
body content.

### Module scanning

`_scan.scan_main_flows()` imports `prefect_modules`, collects module-level
`Flow` objects, and returns selected flows plus marker warnings and errors. It
does not report diagnostics itself; the directive routes them through
`report_diagnostics()` so they carry the directive location.

Selection is by true marker or membership in `prefect_main_flows`. Keep these
rules in `_scan.py`:

- deduplicate by canonical flow entrypoint (`_import.flow_entrypoint()`);
- preserve module order, then attribute order;
- import explicit main flows outside the scanned modules afterwards, in config
  order;
- parse each flow's markers once, even when it appears in several modules or
  under an alias;
- never import Prefect or user modules until the directive runs.

### Runtime DAGs

Keep graph execution in `_dag.py` and pure Mermaid work in `_graph.py`.

- `_dag.generate_graph()` resolves sample arguments from
  `prefect_dag_sample_args` by canonical entrypoint. A flow with required
  parameters and no entry is an error; a flow with no required parameters runs
  with `{}`.
- Call `flow.generate_mermaid_graph(**args)` only after a directive opts in.
  Catch execution failures, including Prefect's `VisualizationUnsupportedError`
  and `MissingContextError`, and route them through `report_error()`.
- `_graph.parse_mermaid()` is pure. It parses Prefect's node and edge lines,
  strips the `-0`, `-1`, ... duplicate-node suffix, and preserves unrecognized
  lines so a newer Prefect graph is not silently truncated.
- `_graph.classify_nodes()` matches stripped labels to module-level `Flow` and
  `Task` objects by `obj.name`. Unknown or ambiguous names are styled as
  unknown nodes, and ambiguous names produce a warning that the directive
  reports through `report_diagnostics()`.
- `_graph.build_diagram()` adds the main-flow node when Prefect omits it, draws
  edges to root nodes, and appends `classDef` styles. Pass the result of
  `classify_nodes()` with `preclassified=True` so the flow module is scanned
  once. Do not add links inside the Mermaid source; subflow/task links belong
  in rendered sections.
- `prefect-flow` enablement lives in `_directives._include_dag()`:
  `:show-dag:` wins, otherwise `prefect_dag_enabled` applies unless `:no-dag:`
  is present. `prefect-dag` always attempts generation.
- Render a note instead of a diagram when the flow body calls no tasks or
  subflows. Follow the Mermaid node with a text legend.
- Subflow graphs are leaves. Do not recurse.

### Error policy

Recoverable failures go through `_errors.report_error()`:

```python
from sphinxcontrib.prefect._errors import report_error

report_error(self, "Could not import module 'pkg.flows'")
```

- `prefect_on_error = "warn"` (default) logs a warning with the directive
  source location and lets the build continue.
- `prefect_on_error = "error"` raises `SphinxError` and fails the build.

Parsers and scan helpers return warnings and errors instead of reporting them.
Directives route both collections through `_errors.report_diagnostics()` so
every message carries the directive source location.

Do not print to stdout or use generic exceptions for user errors.

### Parallel safety

`setup()` must return:

```python
{
    "version": __version__,
    "parallel_read_safe": False,
    "parallel_write_safe": True,
}
```

Reading is unsafe because future DAG generation executes user flow code.

## Testing

Tests use `sphinx.testing.fixtures`. The shared `rootdir` fixture maps test
roots as `tests/roots/test-<name>`.

- `tests/roots/test-flow/` contains a fixture flow package with:
  - a flow with a description and version;
  - a flow without a description;
  - flows using each main-flow marker form, including conflicts and malformed
    frontmatter;
  - a task and a plain function for wrong-type coverage;
  - a module that raises on import to guard setup-time imports;
  - external RST and Markdown descriptions (excluded from the source scan).
- `tests/roots/test-index/` contains scanned modules, an explicit flow outside
  them, unmarked flows, duplicate flow names, malformed markers, a wrong-type
  object, and a module that raises on import.
- `tests/roots/test-dag/` contains a pure flow with two tasks and a subflow,
  an empty flow, a flow with required sample arguments, a `.submit()` flow, a
  flow that needs a Prefect run context, a task defined outside the flow's
  module for unknown-node styling, and ambiguous names (a flow and task that
  share a name, plus two distinct tasks with the same name). Its flows write a
  marker file so tests can prove whether the body executed.
- `tests/test_markers.py` unit-tests marker forms, precedence, stripping, and
  malformed YAML.
- `tests/test_scan.py` unit-tests scan order, explicit-flow inclusion,
  deduplication, entrypoint normalization, and scan diagnostics.
- `tests/test_index_directive.py` covers rendered order, selection, `:show-dag:`
  and `:no-dag:`, empty scans, and warn/error behavior for scan failures.
- `tests/test_dag.py` covers `:show-dag:`, global enablement, `:no-dag:`,
  `prefect-dag`, styled nodes and legend, unknown and ambiguous nodes, empty
  graphs, missing and invalid sample arguments, `.submit()` and
  runtime-context failures, offline builds, the text and man builders, and
  Mermaid parsing.
- `tests/test_parameters.py` covers scalar rows, Google-style descriptions,
  model cross-references, nested and recursive models, RootModel unwrapping,
  dynamic and Pydantic v1 diagnostics, cross-page model deduplication, and
  `prefect-params` output.
- Directive tests assert both doctree nodes and rendered HTML. Description
  tests cover overrides, missing files, MyST rendering when `myst-parser` is
  installed, and the missing-parser warn/error paths. The MyST happy-path test
  is skipped when the `markdown` extra is absent; CI runs the extra in a
  dedicated job.
- Error tests build a temporary copy of a test root so the same fixture package
  can be reused for warn and strict modes.

Useful patterns:

```python
@pytest.mark.sphinx("html", testroot="flow")
def test_renders_flow_metadata(app):
    app.build()
    assert app.statuscode == 0
    assert "Entrypoint" in app.env.get_doctree("index").astext()
```

For strict mode, append `prefect_on_error = "error"` to the copied `conf.py`
and assert that `app.build()` raises `SphinxError`.

When adding a test root, keep its `conf.py` able to import its fixture package:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

extensions = ["sphinxcontrib.prefect"]
```

## Adding a feature

Checklist for a new directive or rendering feature:

1. Read the relevant ticket, spec section, and ADR.
2. Put domain logic in the module named by the specification; keep
   `_directives.py` focused on Sphinx integration.
3. Use `report_error()` for recoverable user errors and include actionable
   messages.
4. Add or extend a test root under `tests/roots/`.
5. Test the happy path in the doctree and HTML, plus the warn and strict error
   paths.
6. Confirm `setup()` still does not import Prefect or user modules.
7. Run formatting, lint, and tests.
8. Update the user-facing documentation (see below).

## Documentation upkeep

After every code implementation, before considering the work complete:

1. **Review and update [`README.md`](README.md).** Keep the project summary and
   status accurate, and keep links to the spec, ADRs, issues, and guides
   current.
2. **Update [`docs/guide.md`](docs/guide.md)** when user-facing behavior,
   configuration, or examples change.
3. **Update this guide** when setup, architecture, conventions, or testing
   change.
4. **Add or amend an ADR** for a significant architectural decision, and update
   [`GLOSSARY.md`](GLOSSARY.md) when introducing or changing domain vocabulary.
5. **Update the ticket draft** under `docs/tickets/` when an implementation
   changes a ticket's scope or acceptance criteria.

## Definition of done

- `uv run ruff format --check .` passes.
- `uv run ruff check .` passes.
- `uv run pytest` passes.
- New behavior has integration coverage in a Sphinx test root.
- `README.md` and the usage guide reflect the new behavior.
- No user flow module is imported during `setup()`.
- Error messages honor `prefect_on_error`.
