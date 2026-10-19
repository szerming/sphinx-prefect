# 04 — MyST Markdown descriptions

- **Status:** Published — [#4](https://github.com/szerming/sphinx-prefect/issues/4)
- **Labels:** `ready-for-agent`, `enhancement`, `documentation`
- **Depends on:** [#3](https://github.com/szerming/sphinx-prefect/issues/3)
- **Spec:** [`docs/specs/0001-sphinx-prefect-v0.1.md`](../specs/0001-sphinx-prefect-v0.1.md)

## Context

Prefect descriptions are Markdown-oriented, and the requirement allows rich Markdown prose for long flow descriptions. Sphinx does not parse Markdown without an extension. MyST support must be optional so the core package does not force `myst-parser`.

## Scope

- Add an optional `markdown` extra with `myst-parser`.
- When `:description-from:` points at a `.md` file:
  - parse it with MyST when `myst-parser` is importable;
  - render headings, lists, code blocks, links, and inline markup;
  - otherwise emit an actionable warning (or error under `prefect_on_error = "error"`) naming the extra.
- Keep docstrings as RST; do not silently treat Markdown docstrings as RST or vice versa.
- Document the format rules.
- Add a CI job that installs the `markdown` extra and runs the MyST test.

## Acceptance criteria

- [ ] A `.md` description renders headings, lists, code, and links in HTML.
- [ ] Missing `myst-parser` produces a warning that names `sphinx-contrib-prefect[markdown]`.
- [ ] Under `prefect_on_error = "error"`, a missing parser fails the build with the same actionable message.
- [ ] RST descriptions are unchanged.
- [ ] Docstrings remain RST and are not auto-detected as Markdown.

## Test plan

- Sphinx test root with `description.md`; run in the extra-dependency CI job.
- Test the missing-parser path by isolating an environment without `myst-parser` or by monkeypatching the import.
- Assert rendered HTML contains the expected heading/list/code elements.

## Out of scope

- MyST docstrings.
- Frontmatter-driven description selection beyond the marker rules.
