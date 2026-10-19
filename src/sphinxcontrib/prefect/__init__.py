"""A Sphinx extension for documenting Prefect flows, tasks, and subflows."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sphinx.application import Sphinx

__version__ = "0.1.0"


def setup(app: Sphinx) -> dict[str, Any]:
    """Register the extension with Sphinx."""
    app.require_sphinx("9.0")
    app.setup_extension("sphinx.ext.autodoc")
    app.setup_extension("sphinxcontrib.pydantic")
    app.setup_extension("sphinxcontrib.mermaid")

    return {
        "version": __version__,
        "parallel_read_safe": False,
        "parallel_write_safe": True,
    }
