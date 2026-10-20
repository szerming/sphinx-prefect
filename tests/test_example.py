"""Build the shipped example project to guard its documented behavior."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pytest
from docutils import nodes
from helpers import purge_modules
from sphinxcontrib.mermaid import mermaid

ROOT = Path(__file__).parent.parent
EXAMPLE = ROOT / "examples" / "demo"


@pytest.fixture(autouse=True)
def isolate_example_package() -> Any:
    """Import a fresh ``demo`` package from each temporary source tree."""
    purge_modules("demo")
    yield
    purge_modules("demo")


def copy_example(tmp_path: Path) -> Path:
    """Copy the example project so a build never writes into the repository."""
    src = tmp_path / "demo"
    shutil.copytree(
        EXAMPLE,
        src,
        ignore=shutil.ignore_patterns("_build", "__pycache__"),
    )
    return src


def test_example_builds_with_warnings_as_errors(
    make_app: Any,
    tmp_path: Path,
) -> None:
    src = copy_example(tmp_path)
    app = make_app(
        "html",
        srcdir=src,
        builddir=src / "_build",
        warningiserror=True,
    )

    app.build()

    assert app.statuscode == 0
    assert (app.outdir / "index.html").is_file()


def test_example_documents_flows_models_and_graphs(
    make_app: Any,
    tmp_path: Path,
) -> None:
    src = copy_example(tmp_path)
    app = make_app(
        "html",
        srcdir=src,
        builddir=src / "_build",
        warningiserror=True,
    )

    app.build()

    index = app.env.get_doctree("index").astext()
    assert "build-report" in index
    assert "weekly-digest" in index
    assert "health-check" in index
    assert "Parameters" in index
    assert "ReportConfig" in index

    standalone = app.env.get_doctree("standalone")
    section = next(
        section
        for section in standalone.findall(nodes.section)
        if section.next_node(nodes.title).astext() == "build-report"
    )
    assert section.next_node(mermaid) is not None
    assert "Subflows" in section.astext()
    assert "Tasks" in section.astext()

    variants = app.env.get_doctree("variants").astext()
    assert "health-check" in variants
    assert "Parameters" in variants
    assert "Flow graph" in variants
