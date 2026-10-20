"""Sphinx configuration for the sphinx-contrib-prefect example project."""

import sys
from pathlib import Path

# Make the local ``demo`` package importable by the directives.
sys.path.insert(0, str(Path(__file__).parent))

from demo.models import Owner, ReportConfig

project = "sphinx-contrib-prefect demo"
copyright = "2026, sphinx-contrib-prefect contributors"

extensions = ["sphinxcontrib.prefect"]

# ``prefect-flow-index`` scans this module for flows with a main-flow marker.
prefect_modules = ["demo.flows"]

# Runtime DAG generation is opt-in. The standalone page enables it with
# ``:show-dag:`` and supplies argument values here.
prefect_dag_enabled = False
prefect_dag_sample_args = {
    "demo.flows.build_report": {
        # Prefect passes sample arguments to the flow function as-is, without
        # validating them against the flow's Pydantic parameter model.
        "config": ReportConfig(
            title="Weekly revenue",
            owner=Owner(name="Ada Lovelace", email="ada@example.com"),
            tags=["revenue", "weekly"],
        ),
        "rows": 12,
    },
}

exclude_patterns = ["_build"]
