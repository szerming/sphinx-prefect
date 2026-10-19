"""A Sphinx extension for documenting Prefect flows, tasks, and subflows."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sphinxcontrib.prefect._directives import (
    PrefectFlowDirective,
    PrefectFlowIndexDirective,
)

if TYPE_CHECKING:
    from sphinx.application import Sphinx

__version__ = "0.1.0"


def setup(app: Sphinx) -> dict[str, Any]:
    """Register the extension with Sphinx."""
    app.require_sphinx("9.0")
    app.setup_extension("sphinx.ext.autodoc")
    app.setup_extension("sphinxcontrib.pydantic")
    app.setup_extension("sphinxcontrib.mermaid")

    app.add_config_value("prefect_modules", [], "env", types=list)
    app.add_config_value("prefect_main_flows", [], "env", types=list)
    app.add_config_value("prefect_on_error", "warn", "env", types=str)
    app.add_directive("prefect-flow", PrefectFlowDirective)
    app.add_directive("prefect-flow-index", PrefectFlowIndexDirective)

    return {
        "version": __version__,
        "parallel_read_safe": False,
        "parallel_write_safe": True,
    }
