# sphinx-contrib-prefect

A Sphinx extension for documenting Prefect flows, their parameters, Pydantic
models, and the tasks and subflows observed in a flow graph.

**Status:** v0.1 in development. The package scaffold, tooling, and CI are in
place. The directives described below are not available yet; they are tracked
in issues [#2–#9](https://github.com/szerming/sphinx-prefect/issues).

## Installation

```bash
pip install sphinx-contrib-prefect
```

For MyST Markdown descriptions, install the `markdown` extra:

```bash
pip install "sphinx-contrib-prefect[markdown]"
```

## Quickstart

The planned v0.1 interface adds the extension to `conf.py`:

```python
extensions = [
    "sphinx.ext.autodoc",
    "sphinxcontrib.pydantic",
    "sphinxcontrib.mermaid",
    "sphinxcontrib.prefect",
]
```

Then document a flow by its entrypoint:

```rst
.. prefect-flow:: mypkg.flows.eda

   Optional body content is appended after the generated description.
```

The planned interface also includes `prefect-params`, `prefect-dag`, and
`prefect-flow-index`. See the [v0.1 specification](docs/specs/0001-sphinx-prefect-v0.1.md)
for the full design.

## Development

```bash
uv sync --all-extras
uv run ruff format --check .
uv run ruff check .
uv run pytest
```

- [v0.1 specification](docs/specs/0001-sphinx-prefect-v0.1.md)
- [Architecture decisions](docs/adr/)
- [Ticket drafts](docs/tickets/) — published as GitHub issues [#1–#10](https://github.com/szerming/sphinx-prefect/issues)
- [Glossary](GLOSSARY.md)
