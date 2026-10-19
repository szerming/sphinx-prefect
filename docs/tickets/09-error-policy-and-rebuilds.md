# 09 — Error policy, dependency tracking, and parallel safety

- **Status:** Published — [#9](https://github.com/szerming/sphinx-prefect/issues/9)
- **Labels:** `ready-for-agent`, `enhancement`
- **Depends on:** [#2](https://github.com/szerming/sphinx-prefect/issues/2), [#3](https://github.com/szerming/sphinx-prefect/issues/3), [#4](https://github.com/szerming/sphinx-prefect/issues/4), [#5](https://github.com/szerming/sphinx-prefect/issues/5), [#6](https://github.com/szerming/sphinx-prefect/issues/6), [#7](https://github.com/szerming/sphinx-prefect/issues/7), [#8](https://github.com/szerming/sphinx-prefect/issues/8)
- **Spec:** [`docs/specs/0001-sphinx-prefect-v0.1.md`](../specs/0001-sphinx-prefect-v0.1.md)

## Context

The feature tickets implement happy paths. This ticket makes failure behavior consistent and ensures docs rebuild when flow source changes. Runtime DAG generation executes user code, so the extension must not claim parallel read safety.

## Scope

- Audit every recoverable failure path and route it through one `prefect_on_error` helper:
  - import failure, missing attribute, wrong object type;
  - malformed marker/YAML;
  - missing MyST parser;
  - missing/invalid DAG arguments and DAG execution failures;
  - non-importable or Pydantic v1 models.
- Include directive location and relevant source path in warnings.
- Call `env.note_dependency()` for:
  - flow and task source files (`inspect.getsourcefile` / `__code__.co_filename`);
  - external description files.
- Set extension metadata `parallel_read_safe = False` and `parallel_write_safe = True`.
- Keep no custom cache and no subprocess isolation in v0.1.
- Verify model deduplication across pages uses `app.env` and does not leak between builds.
- Add a failure-modes table to the README or docs.

## Acceptance criteria

- [ ] Every listed failure path warns by default and continues.
- [ ] `prefect_on_error = "error"` fails the build for every listed failure path.
- [ ] Warnings name the directive location and the relevant module/file.
- [ ] Flow/task source files and external descriptions are registered as dependencies.
- [ ] Editing a flow source file causes a rebuild in Sphinx incremental mode.
- [ ] `parallel_read_safe` is `False`; `parallel_write_safe` is `True`.
- [ ] No custom cache or subprocess is present.
- [ ] Duplicate models across pages still produce no warnings.

## Test plan

- Parameterized tests over each failure path with both `warn` and `error`.
- Unit-test the dependency-registration helper with a mocked `env`.
- Integration test: build, touch a flow source file, rebuild, assert the flow page is rewritten.
- Assert `setup()` metadata.
- Two-page model duplication test.

## Out of scope

- Subprocess isolation, timeouts, and caching (future work).
- Parallel read safety for a future static mode.
