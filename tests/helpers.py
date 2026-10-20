"""Shared helpers for Sphinx integration tests."""

from __future__ import annotations

import shutil
from typing import TYPE_CHECKING

from docutils import nodes

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Any


def copy_test_root(
    root: Path,
    tmp_path: Path,
    body: str,
    *,
    config: str = "",
) -> Path:
    """Copy *root* to a temporary source tree and replace its index page."""
    src = tmp_path / "src"
    shutil.copytree(
        root,
        src,
        ignore=shutil.ignore_patterns("_build", "__pycache__"),
    )
    (src / "index.rst").write_text(body, encoding="utf-8")
    if config:
        with (src / "conf.py").open("a", encoding="utf-8") as conf:
            conf.write(f"\n{config}\n")
    return src


def create_app(
    make_app: Any,
    src: Path,
    *,
    builder: str = "html",
) -> Any:
    """Create a test app for *src* without building it."""
    return make_app(
        builder,
        srcdir=src,
        builddir=src / "_build",
        warningiserror=False,
    )


def build(make_app: Any, src: Path, *, builder: str = "html") -> Any:
    """Build *src* with *builder* and return the test app."""
    app = create_app(make_app, src, builder=builder)
    app.build()
    return app


def find_section(doctree: nodes.document, title: str) -> nodes.section | None:
    """Return the section whose title is *title*, if present."""
    for section in doctree.findall(nodes.section):
        section_title = section.next_node(nodes.title)
        if section_title is not None and section_title.astext() == title:
            return section
    return None


def section_titles(doctree: nodes.document) -> list[str]:
    """Return every section title in document order."""
    return [
        title.astext()
        for title in doctree.findall(nodes.title)
        if isinstance(title.parent, nodes.section)
    ]
