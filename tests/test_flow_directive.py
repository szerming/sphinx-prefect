"""Tests for the ``prefect-flow`` directive and flow metadata."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from docutils import nodes
from sphinx.errors import SphinxError

from sphinxcontrib.prefect._import import ObjectResolutionError, split_entrypoint

ROOT = Path(__file__).parent / "roots" / "test-flow"


def make_src(tmp_path: Path, body: str, *, config: str = "") -> Path:
    """Copy the flow test root and replace its index page."""
    src = tmp_path / "src"
    shutil.copytree(
        ROOT,
        src,
        ignore=shutil.ignore_patterns("_build", "__pycache__"),
    )
    (src / "index.rst").write_text(body, encoding="utf-8")
    if config:
        with (src / "conf.py").open("a", encoding="utf-8") as conf:
            conf.write(f"\n{config}\n")
    return src


def build(make_app: Any, src: Path) -> Any:
    """Build *src* with the HTML builder and return the test app."""
    app = make_app(
        "html",
        srcdir=src,
        builddir=src / "_build",
        warningiserror=False,
    )
    app.build()
    return app


def find_section(doctree: nodes.document, title: str) -> nodes.section | None:
    """Return the section whose title is *title*, if present."""
    for section in doctree.findall(nodes.section):
        section_title = section.next_node(nodes.title)
        if section_title is not None and section_title.astext() == title:
            return section
    return None


@pytest.mark.sphinx("html", testroot="flow")
def test_renders_flow_metadata(app: Any) -> None:
    app.build()

    assert app.statuscode == 0
    assert not app.warning.getvalue()

    section = find_section(app.env.get_doctree("index"), "main")
    assert section is not None
    assert section.next_node(nodes.title).astext() == "main"

    field_names = [field[0].astext() for field in section.findall(nodes.field)]
    assert field_names == ["Entrypoint", "Version", "Signature"]

    text = section.astext()
    assert "fixture_pkg.flows.main" in text
    assert "1.2.3" in text
    assert "(seed: int = 1)" in text
    assert "Run the main fixture flow." in text
    assert "This description uses reStructuredText." in text
    assert "This is the directive body." in text

    emphasis = [node.astext() for node in section.findall(nodes.emphasis)]
    assert "reStructuredText" in emphasis
    assert "body" in emphasis

    children = [child.astext() for child in section.children]
    description_index = next(
        index
        for index, child in enumerate(children)
        if child.startswith("Run the main fixture flow.")
    )
    body_index = children.index("This is the directive body.")
    assert body_index > description_index

    html = (app.outdir / "index.html").read_text(encoding="utf-8")
    assert "fixture_pkg.flows.main" in html
    assert "1.2.3" in html


def test_accepts_colon_entrypoint(make_app: Any, tmp_path: Path) -> None:
    src = make_src(
        tmp_path,
        "Colon entrypoint\n================\n\n"
        ".. prefect-flow:: fixture_pkg.flows:main\n",
    )

    app = build(make_app, src)

    assert app.statuscode == 0
    section = find_section(app.env.get_doctree("index"), "main")
    assert section is not None
    assert "fixture_pkg.flows.main" in section.astext()


def test_flow_without_description_renders(make_app: Any, tmp_path: Path) -> None:
    src = make_src(
        tmp_path,
        "No description\n==============\n\n"
        ".. prefect-flow:: fixture_pkg.flows.undocumented\n",
    )

    app = build(make_app, src)

    assert app.statuscode == 0
    assert not app.warning.getvalue()
    section = find_section(app.env.get_doctree("index"), "undocumented")
    assert section is not None
    assert "fixture_pkg.flows.undocumented" in section.astext()


@pytest.mark.parametrize(
    ("entrypoint", "message"),
    [
        ("fixture_pkg.missing.main", "Could not import module"),
        ("fixture_pkg.flows.missing", "Could not find"),
        ("fixture_pkg.flows.not_a_flow", "not a Prefect flow"),
        ("fixture_pkg.flows.plain_function", "not a Prefect flow"),
        ("fixture_pkg.explodes.main", "Could not import module"),
    ],
)
def test_resolution_failures_warn_by_default(
    make_app: Any,
    tmp_path: Path,
    entrypoint: str,
    message: str,
) -> None:
    src = make_src(
        tmp_path,
        f"Broken flow\n===========\n\n.. prefect-flow:: {entrypoint}\n",
    )

    app = build(make_app, src)

    assert app.statuscode == 0
    warnings = app.warning.getvalue()
    assert message in warnings
    assert "index.rst" in warnings
    assert find_section(app.env.get_doctree("index"), "main") is None


@pytest.mark.parametrize(
    ("entrypoint", "message"),
    [
        ("fixture_pkg.missing.main", "Could not import module"),
        ("fixture_pkg.flows.missing", "Could not find"),
        ("fixture_pkg.flows.not_a_flow", "not a Prefect flow"),
    ],
)
def test_resolution_failures_raise_in_strict_mode(
    make_app: Any,
    tmp_path: Path,
    entrypoint: str,
    message: str,
) -> None:
    src = make_src(
        tmp_path,
        f"Broken flow\n===========\n\n.. prefect-flow:: {entrypoint}\n",
        config='prefect_on_error = "error"',
    )

    app = make_app(
        "html",
        srcdir=src,
        builddir=src / "_build",
        warningiserror=False,
    )

    with pytest.raises(SphinxError, match=message):
        app.build()


@pytest.mark.parametrize(
    ("entrypoint", "module_name", "attribute_path"),
    [
        ("fixture_pkg.flows.main", "fixture_pkg.flows", "main"),
        ("fixture_pkg.flows:main", "fixture_pkg.flows", "main"),
        ("fixture_pkg.flows:Flows.Main", "fixture_pkg.flows", "Flows.Main"),
    ],
)
def test_split_entrypoint(
    entrypoint: str,
    module_name: str,
    attribute_path: str,
) -> None:
    assert split_entrypoint(entrypoint) == (module_name, attribute_path)


@pytest.mark.parametrize("entrypoint", ["", "main", ":main", "module:"])
def test_split_entrypoint_rejects_invalid_values(entrypoint: str) -> None:
    with pytest.raises(ObjectResolutionError):
        split_entrypoint(entrypoint)


def test_setup_does_not_import_user_modules() -> None:
    code = f"""
import sys

sys.path.insert(0, {str(ROOT)!r})

import sphinxcontrib.prefect


class FakeApp:
    def require_sphinx(self, version):
        pass

    def setup_extension(self, name):
        pass

    def add_config_value(self, name, default, rebuild, types=()):
        pass

    def add_directive(self, name, directive):
        pass


sphinxcontrib.prefect.setup(FakeApp())
assert "fixture_pkg.flows" not in sys.modules
assert "fixture_pkg.explodes" not in sys.modules
assert "prefect" not in sys.modules
"""

    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
