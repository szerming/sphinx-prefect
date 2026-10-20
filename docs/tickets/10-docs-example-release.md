# 10 — Documentation, example project, and release

- **Status:** Implemented — [#10](https://github.com/szerming/sphinx-prefect/issues/10)
- **Labels:** `ready-for-agent`, `documentation`
- **Depends on:** [#1](https://github.com/szerming/sphinx-prefect/issues/1), [#2](https://github.com/szerming/sphinx-prefect/issues/2), [#3](https://github.com/szerming/sphinx-prefect/issues/3), [#4](https://github.com/szerming/sphinx-prefect/issues/4), [#5](https://github.com/szerming/sphinx-prefect/issues/5), [#6](https://github.com/szerming/sphinx-prefect/issues/6), [#7](https://github.com/szerming/sphinx-prefect/issues/7), [#8](https://github.com/szerming/sphinx-prefect/issues/8), [#9](https://github.com/szerming/sphinx-prefect/issues/9)
- **Spec:** [`docs/specs/0001-sphinx-prefect-v0.1.md`](../specs/0001-sphinx-prefect-v0.1.md)

## Context

The extension needs a usable quickstart, an example that exercises every feature, and release artifacts. Publishing to PyPI requires maintainer credentials and is a human gate.

## Scope

- Write `README.md`:
  - install, quickstart `conf.py`, and a minimal `index.rst`;
  - directive reference (`prefect-flow`, `prefect-params`, `prefect-dag`, `prefect-flow-index`);
  - configuration table;
  - marker syntax and precedence;
  - runtime DAG side effects, one-path limitation, subflow leaves, deployment-call limitation, `.submit`/`.map` limitation;
  - Pydantic/importability limitations;
  - HTML/text/LaTeX support and the `mmdc` requirement.
- Build the extension's own docs under `docs/` with `-W`.
- Add an example project (for example `examples/demo/`) with:
  - a main flow, subflow, tasks, scalar parameters, and a nested Pydantic model;
  - all three marker forms demonstrated;
  - a `prefect-flow-index` page and a standalone `prefect-flow` page;
  - a working `prefect_dag_sample_args` entry.
- Verify packaging:
  - `uv build` produces wheel and sdist;
  - wheel contains `sphinxcontrib/prefect/` and no `sphinxcontrib/__init__.py`;
  - metadata declares Python/Sphinx/Prefect ranges, MIT license, classifiers.
- Add a release checklist: version bump, changelog, tag, build, upload (human), verify install from PyPI.

## Acceptance criteria

- [x] README quickstart builds a working page in a fresh environment.
- [x] `sphinx-build -W` for the extension docs succeeds.
- [x] The example project builds and demonstrates description, params, models, DAG, subflows/tasks, and index scanning.
- [x] `uv build` succeeds; wheel/sdist contents are correct.
- [x] Package metadata matches the spec's compatibility matrix.
- [x] Release checklist is documented.
- [x] PyPI upload is explicitly marked as a human step.

## Test plan

- CI job that builds `docs/` with `-W`.
- CI job that builds `examples/demo/`.
- Inspect wheel contents (`unzip -l`).
- Install the built wheel into a clean virtual environment and build the example.

## Out of scope

- Actual PyPI upload, which requires maintainer credentials.
- Marketing site or theme customization.
