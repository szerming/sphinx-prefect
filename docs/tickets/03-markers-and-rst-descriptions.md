# 03 — Main-flow markers and RST descriptions

- **Status:** Published — [#3](https://github.com/szerming/sphinx-prefect/issues/3)
- **Labels:** `ready-for-agent`, `enhancement`
- **Depends on:** [#2](https://github.com/szerming/sphinx-prefect/issues/2)
- **Spec:** [`docs/specs/0001-sphinx-prefect-v0.1.md`](../specs/0001-sphinx-prefect-v0.1.md)
- **ADRs:** [0004](../adr/0004-docstring-markers-and-module-scan.md)

## Context

Main-flow selection needs stable docstring metadata, and long descriptions need an external-file escape hatch. The module scan that consumes markers is a separate ticket; this ticket implements parsing and description resolution.

## Scope

- Implement `_markers.py`:
  - standalone `@mainflow` line (`^\s*@mainflow\s*$`), not a Python decorator;
  - YAML frontmatter at the start of the docstring, with `mainflow: true|false`;
  - reST field `:mainflow:` / `:mainflow: true|false`.
  - any true marker wins; conflicting true/false emits a warning; malformed YAML warns/errors per `prefect_on_error`;
  - strip all marker syntax from the rendered description.
- Add `:description-from:` to `prefect-flow`:
  - resolve the path relative to the Sphinx source directory;
  - parse `.rst` with `nested_parse`;
  - `.md` is handled in ticket 04; in this ticket it warns that MyST is required unless ticket 04 has landed.
- Keep docstrings as RST.
- Register marker parsing as a reusable function for the module scan.

## Acceptance criteria

- [ ] A flow with `@mainflow` on its own docstring line is detected and the marker is stripped.
- [ ] YAML frontmatter `mainflow: true` is detected and the whole block is stripped.
- [ ] `:mainflow:` and `:mainflow: true` are detected and the field is stripped.
- [ ] `:mainflow: false` and `mainflow: false` do not select the flow.
- [ ] Conflicting true/false markers emit a warning.
- [ ] `:description-from: description.rst` overrides the docstring and renders RST.
- [ ] A missing external file warns/errors per `prefect_on_error`.
- [ ] `@mainflow` is not interpreted as a decorator or an import.

## Test plan

- Unit tests for each marker form and precedence.
- Sphinx test root with external RST.
- Assert the rendered description does not contain marker text.
- Assert malformed YAML and missing files follow `prefect_on_error`.

## Out of scope

- Module scanning and `prefect-flow-index`.
- MyST parsing (ticket 04).
