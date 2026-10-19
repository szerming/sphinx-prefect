# 01 — Scaffold package, tooling, and CI

- **Status:** Published — [#1](https://github.com/szerming/sphinx-prefect/issues/1)
- **Labels:** `ready-for-agent`, `enhancement`
- **Depends on:** none
- **Spec:** [`docs/specs/0001-sphinx-prefect-v0.1.md`](../specs/0001-sphinx-prefect-v0.1.md)
- **ADRs:** [0002](../adr/0002-standalone-directives.md), [0003](../adr/0003-delegate-pydantic-rendering.md)

## Context

The repository is a bare `uv` scaffold (`pyproject.toml`, `main.py`, empty `README.md`). It has no package layout, dependencies, tests, CI, or license.

## Scope

- Replace the scaffold `pyproject.toml` with the real project metadata:
  - distribution `sphinx-contrib-prefect`, version `0.1.0`, MIT license;
  - `requires-python = ">=3.12,<3.15"`;
  - runtime dependencies: `sphinx>=9,<10`, `prefect>=3,<4`, `pydantic>=2.10,<3`, `sphinxcontrib-mermaid>=2.1,<3`, `sphinxcontrib-pydantic>=0.4,<0.5`;
  - optional `markdown` extra for `myst-parser`;
  - dev dependencies: `pytest`, `ruff`, `beautifulsoup4`.
- Create the `src` layout: `src/sphinxcontrib/prefect/__init__.py` with a minimal `setup(app)` returning version and parallel flags. Do **not** add `src/sphinxcontrib/__init__.py`; it is a PEP 420 namespace.
- Remove the scaffold `main.py` or leave it outside the package with a clear purpose.
- Add `LICENSE` (MIT), `README.md` quickstart stub, `.gitignore`, and ruff/pytest configuration.
- Add `tests/conftest.py` with `pytest_plugins = ("sphinx.testing.fixtures",)` and a `rootdir` fixture.
- Add a minimal test root that loads `sphinxcontrib.prefect` and builds an empty page.
- Add GitHub Actions CI: Python 3.12 and 3.13, `uv sync --all-extras`, `ruff format --check`, `ruff check`, `pytest`.

## Acceptance criteria

- [ ] `uv sync --all-extras` succeeds.
- [ ] `uv run ruff format --check .` and `uv run ruff check .` pass.
- [ ] `uv run pytest` passes.
- [ ] A minimal Sphinx project with `extensions = ["sphinxcontrib.prefect"]` builds.
- [ ] `src/sphinxcontrib/__init__.py` does not exist.
- [ ] CI is green on Python 3.12 and 3.13.
- [ ] `LICENSE` is MIT and `pyproject.toml` declares the license.

## Test plan

- `tests/test_package.py`: assert the extension version and parallel flags from `setup()`.
- Sphinx test root: build with the extension enabled and no directives.
- Verify the built wheel contains `sphinxcontrib/prefect/` and no `sphinxcontrib/__init__.py`.

## Out of scope

- Directives, flow rendering, DAG generation, model rendering.
- Publishing to PyPI.
