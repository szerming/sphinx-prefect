"""Resolve flow descriptions from docstrings and external files."""

from __future__ import annotations

import inspect
from pathlib import Path
from typing import TYPE_CHECKING

from sphinxcontrib.prefect._errors import report_error

if TYPE_CHECKING:
    from sphinx.util.docutils import SphinxDirective

    from prefect import Flow
    from sphinxcontrib.prefect._markers import MarkerResult


def resolve_flow_description(flow: Flow, markers: MarkerResult) -> str | None:
    """Return *flow*'s description with docstring marker syntax removed."""
    docstring = inspect.getdoc(flow.fn)
    if docstring is not None and flow.description == docstring:
        return markers.description or None
    return flow.description


def read_description_file(
    directive: SphinxDirective,
    path: str,
) -> str | None:
    """Read an external description relative to the Sphinx source directory."""
    source = Path(directive.env.srcdir) / path
    if not source.is_file():
        report_error(
            directive,
            f"Could not find description file {str(source)!r}.",
        )
        return None
    if source.suffix.lower() in {".md", ".markdown"}:
        report_error(
            directive,
            "Markdown description files are not supported yet (see issue #4); "
            "install 'sphinx-contrib-prefect[markdown]' to use MyST once "
            "supported.",
        )
        return None

    try:
        text = source.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        report_error(
            directive,
            f"Could not read description file {str(source)!r}: {exc}",
        )
        return None

    directive.env.note_dependency(str(source))
    return text
