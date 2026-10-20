"""Sphinx configuration for the sphinx-contrib-prefect documentation."""

project = "sphinx-contrib-prefect"
copyright = "2026, sphinx-contrib-prefect contributors"
author = "sphinx-contrib-prefect contributors"

extensions = ["myst_parser"]

source_suffix = {
    ".md": "markdown",
    ".rst": "restructuredtext",
}

myst_enable_extensions = ["colon_fence", "deflist"]
myst_heading_anchors = 3

# Internal planning documents are not part of the published documentation.
exclude_patterns = ["_build", "agents", "tickets"]

html_theme = "alabaster"
