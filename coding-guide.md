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
├── _render.py        # doctree helpers and shared flow-section rendering
└── _errors.py        # prefect_on_error handling and source-located diagnostics

tests/
├── conftest.py
├── roots/
│   ├── test-flow/    # flow directive, fixture flows, external descriptions
│   └── test-index/   # module scan and prefect-flow-index
├── test_flow_directive.py
├── test_index_directive.py
├── test_markers.py
├── test_package.py
└── test_scan.py

docs/
├── adr/              # architecture decision records
├── specs/            # approved specifications
├── tickets/          # local ticket drafts
└── guide.md          # user-facing usage guide
```

`src/sphinxcontrib/` is a native PEP 420 namespace package. Do not add
`src/sphinxcontrib/__init__.py`.

The specification names modules for the remaining tickets: `_markers.py`,
`_description.py`, `_params.py`, `_models.py`, `_dag.py`, and `_graph.py`.
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
- `tests/test_markers.py` unit-tests marker forms, precedence, stripping, and
  malformed YAML.
- `tests/test_scan.py` unit-tests scan order, explicit-flow inclusion,
  deduplication, entrypoint normalization, and scan diagnostics.
- `tests/test_index_directive.py` covers rendered order, selection, `:show-dag:`
  and `:no-dag:`, empty scans, and warn/error behavior for scan failures.
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
