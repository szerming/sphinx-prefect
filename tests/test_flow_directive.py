"""Tests for the ``prefect-flow`` directive and flow metadata."""

from __future__ import annotations

import importlib.util
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


def hide_myst(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make MyST unavailable, whether or not the extra is installed."""
    if importlib.util.find_spec("myst_parser") is not None:
        monkeypatch.setattr(
            "sphinxcontrib.prefect._description._load_myst",
            lambda: None,
        )


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
    ("entrypoint", "title", "description"),
    [
        (
            "fixture_pkg.flows.marked_with_at",
            "marked-with-at",
            "Run a flow selected with a standalone marker.",
        ),
        (
            "fixture_pkg.flows.marked_with_frontmatter",
            "marked-with-frontmatter",
            "Run a flow selected with YAML frontmatter.",
        ),
        (
            "fixture_pkg.flows.marked_with_field",
            "marked-with-field",
            "Run a flow selected with a reST field.",
        ),
    ],
)
def test_mainflow_markers_are_stripped_from_descriptions(
    make_app: Any,
    tmp_path: Path,
    entrypoint: str,
    title: str,
    description: str,
) -> None:
    src = make_src(
        tmp_path,
        f"Markers\n=======\n\n.. prefect-flow:: {entrypoint}\n",
    )

    app = build(make_app, src)

    assert app.statuscode == 0
    assert not app.warning.getvalue()
    section = find_section(app.env.get_doctree("index"), title)
    assert section is not None
    text = section.astext()
    assert description in text
    assert "@mainflow" not in text
    assert ":mainflow:" not in text
    assert "mainflow: true" not in text

    html = (app.outdir / "index.html").read_text(encoding="utf-8")
    assert description in html
    assert "@mainflow" not in html
    assert ":mainflow:" not in html


def test_conflicting_markers_warn_and_still_render(
    make_app: Any,
    tmp_path: Path,
) -> None:
    src = make_src(
        tmp_path,
        "Conflict\n========\n\n"
        ".. prefect-flow:: fixture_pkg.flows.conflicting_markers\n",
    )

    app = build(make_app, src)

    assert app.statuscode == 0
    warnings = app.warning.getvalue()
    assert "Conflicting main-flow markers" in warnings
    assert "index.rst" in warnings
    section = find_section(app.env.get_doctree("index"), "conflicting-markers")
    assert section is not None
    assert "Run a flow with conflicting markers." in section.astext()


def test_conflicting_markers_stay_warnings_in_strict_mode(
    make_app: Any,
    tmp_path: Path,
) -> None:
    src = make_src(
        tmp_path,
        "Conflict\n========\n\n"
        ".. prefect-flow:: fixture_pkg.flows.conflicting_markers\n",
        config='prefect_on_error = "error"',
    )

    app = build(make_app, src)

    assert app.statuscode == 0
    assert "Conflicting main-flow markers" in app.warning.getvalue()


def test_explicit_description_does_not_contain_docstring_marker(
    make_app: Any,
    tmp_path: Path,
) -> None:
    src = make_src(
        tmp_path,
        "Explicit\n========\n\n"
        ".. prefect-flow:: fixture_pkg.flows.explicit_description\n",
    )

    app = build(make_app, src)

    assert app.statuscode == 0
    assert not app.warning.getvalue()
    section = find_section(app.env.get_doctree("index"), "explicit-description")
    assert section is not None
    text = section.astext()
    assert "Explicit description with emphasis." in text
    assert "must not leak" not in text
    assert "@mainflow" not in text

    html = (app.outdir / "index.html").read_text(encoding="utf-8")
    assert "Explicit description with <em>emphasis</em>." in html
    assert "@mainflow" not in html


def test_malformed_frontmatter_warns_by_default(
    make_app: Any,
    tmp_path: Path,
) -> None:
    src = make_src(
        tmp_path,
        "Malformed\n=========\n\n"
        ".. prefect-flow:: fixture_pkg.flows.malformed_markers\n",
    )

    app = build(make_app, src)

    assert app.statuscode == 0
    warnings = app.warning.getvalue()
    assert "Malformed main-flow frontmatter" in warnings
    assert "index.rst" in warnings
    section = find_section(app.env.get_doctree("index"), "malformed-markers")
    assert section is not None
    assert "Run a flow with malformed frontmatter." in section.astext()


def test_malformed_frontmatter_raises_in_strict_mode(
    make_app: Any,
    tmp_path: Path,
) -> None:
    src = make_src(
        tmp_path,
        "Malformed\n=========\n\n"
        ".. prefect-flow:: fixture_pkg.flows.malformed_markers\n",
        config='prefect_on_error = "error"',
    )

    app = make_app(
        "html",
        srcdir=src,
        builddir=src / "_build",
        warningiserror=False,
    )

    with pytest.raises(SphinxError, match="Malformed main-flow frontmatter"):
        app.build()


def test_missing_frontmatter_closing_warns_and_preserves_prose(
    make_app: Any,
    tmp_path: Path,
) -> None:
    src = make_src(
        tmp_path,
        "Missing closing\n===============\n\n"
        ".. prefect-flow:: fixture_pkg.flows.missing_frontmatter_closing\n",
    )

    app = build(make_app, src)

    assert app.statuscode == 0
    warnings = app.warning.getvalue()
    assert "missing closing" in warnings
    assert "index.rst" in warnings
    section = find_section(
        app.env.get_doctree("index"),
        "missing-frontmatter-closing",
    )
    assert section is not None
    text = section.astext()
    assert "Notes: this is description prose." in text
    assert "mainflow: true" not in text


def test_indented_field_in_a_literal_block_is_not_a_marker(
    make_app: Any,
    tmp_path: Path,
) -> None:
    src = make_src(
        tmp_path,
        "Literal\n=======\n\n"
        ".. prefect-flow:: fixture_pkg.flows.indented_field_literal\n",
    )

    app = build(make_app, src)

    assert app.statuscode == 0
    assert not app.warning.getvalue()
    section = find_section(app.env.get_doctree("index"), "indented-field-literal")
    assert section is not None
    assert ":mainflow: true" in section.astext()
    assert section.findall(nodes.literal_block)


def test_description_from_rst_overrides_the_docstring(
    make_app: Any,
    tmp_path: Path,
) -> None:
    src = make_src(
        tmp_path,
        "External\n========\n\n"
        ".. prefect-flow:: fixture_pkg.flows.main\n"
        "   :description-from: description.rst\n",
    )

    app = build(make_app, src)

    assert app.statuscode == 0
    assert not app.warning.getvalue()
    section = find_section(app.env.get_doctree("index"), "main")
    assert section is not None
    text = section.astext()
    assert "This description comes from an external file." in text
    assert "first item" in text
    assert "Run the main fixture flow." not in text
    assert "reStructuredText" not in text

    emphasis = [node.astext() for node in section.findall(nodes.emphasis)]
    assert "file" in emphasis
    assert "reStructuredText" not in emphasis

    html = (app.outdir / "index.html").read_text(encoding="utf-8")
    assert "This description comes from an external <em>file</em>." in html
    assert any(
        str(path).endswith("description.rst") for path in app.env.dependencies["index"]
    )


def test_description_from_is_relative_to_the_source_directory(
    make_app: Any,
    tmp_path: Path,
) -> None:
    src = make_src(
        tmp_path,
        "Root\n====\n\n.. toctree::\n\n   nested/page\n",
    )
    nested = src / "nested"
    nested.mkdir()
    (nested / "page.rst").write_text(
        "Nested page\n===========\n\n"
        ".. prefect-flow:: fixture_pkg.flows.main\n"
        "   :description-from: description.rst\n",
        encoding="utf-8",
    )

    app = build(make_app, src)

    assert app.statuscode == 0
    assert not app.warning.getvalue()
    section = find_section(app.env.get_doctree("nested/page"), "main")
    assert section is not None
    assert "This description comes from an external file." in section.astext()

    html = (app.outdir / "nested" / "page.html").read_text(encoding="utf-8")
    assert "This description comes from an external <em>file</em>." in html


def test_missing_description_file_warns_and_omits_the_description(
    make_app: Any,
    tmp_path: Path,
) -> None:
    src = make_src(
        tmp_path,
        "Missing\n=======\n\n"
        ".. prefect-flow:: fixture_pkg.flows.main\n"
        "   :description-from: missing.rst\n",
    )

    app = build(make_app, src)

    assert app.statuscode == 0
    warnings = app.warning.getvalue()
    assert "Could not find description file" in warnings
    assert "index.rst" in warnings
    section = find_section(app.env.get_doctree("index"), "main")
    assert section is not None
    assert "fixture_pkg.flows.main" in section.astext()
    assert "Run the main fixture flow." not in section.astext()


def test_missing_description_file_raises_in_strict_mode(
    make_app: Any,
    tmp_path: Path,
) -> None:
    src = make_src(
        tmp_path,
        "Missing\n=======\n\n"
        ".. prefect-flow:: fixture_pkg.flows.main\n"
        "   :description-from: missing.rst\n",
        config='prefect_on_error = "error"',
    )

    app = make_app(
        "html",
        srcdir=src,
        builddir=src / "_build",
        warningiserror=False,
    )

    with pytest.raises(SphinxError, match="Could not find description file"):
        app.build()


def test_docstrings_remain_restructured_text(
    make_app: Any,
    tmp_path: Path,
) -> None:
    src = make_src(
        tmp_path,
        "Docstring\n=========\n\n"
        ".. prefect-flow:: fixture_pkg.flows.markdown_looking_docstring\n",
    )

    app = build(make_app, src)

    assert app.statuscode == 0
    assert not app.warning.getvalue()
    doctree = app.env.get_doctree("index")
    assert find_section(doctree, "This is a docstring, not a Markdown heading") is None
    section = find_section(doctree, "markdown-looking-docstring")
    assert section is not None
    assert "# This is a docstring, not a Markdown heading" in section.astext()


MARKDOWN_PAGE = (
    "Markdown\n========\n\n"
    ".. prefect-flow:: fixture_pkg.flows.main\n"
    "   :description-from: description.md\n"
)


def test_markdown_description_renders_with_myst(
    make_app: Any,
    tmp_path: Path,
) -> None:
    pytest.importorskip("myst_parser")
    src = make_src(tmp_path, MARKDOWN_PAGE)

    app = build(make_app, src)

    assert app.statuscode == 0
    assert not app.warning.getvalue()
    doctree = app.env.get_doctree("index")
    section = find_section(doctree, "main")
    assert section is not None
    assert "This description is written in Markdown with strong text." in (
        section.astext()
    )
    assert find_section(doctree, "Markdown description") is not None
    assert find_section(doctree, "Details") is not None

    bullet_list = list(section.findall(nodes.bullet_list))
    assert len(bullet_list) == 1
    items = [item.astext() for item in bullet_list[0].findall(nodes.list_item)]
    assert items == ["first item", "second item with a link."]

    links = list(section.findall(nodes.reference))
    assert [link["refuri"] for link in links] == ["https://www.prefect.io"]

    literal_blocks = list(section.findall(nodes.literal_block))
    assert [block.astext().strip() for block in literal_blocks] == ['print("hello")']

    html = (app.outdir / "index.html").read_text(encoding="utf-8")
    assert 'id="markdown-description"' in html
    assert 'id="details"' in html
    assert "<li><p>first item</p></li>" in html
    assert 'href="https://www.prefect.io"' in html
    assert "<strong>strong</strong>" in html
    assert any(
        str(path).endswith("description.md") for path in app.env.dependencies["index"]
    )


def test_markdown_description_warns_when_myst_is_missing(
    make_app: Any,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hide_myst(monkeypatch)
    src = make_src(tmp_path, MARKDOWN_PAGE)

    app = build(make_app, src)

    assert app.statuscode == 0
    warnings = app.warning.getvalue()
    assert "sphinx-contrib-prefect[markdown]" in warnings
    assert "index.rst" in warnings
    section = find_section(app.env.get_doctree("index"), "main")
    assert section is not None
    assert "Run the main fixture flow." not in section.astext()


def test_markdown_description_raises_when_myst_is_missing_in_strict_mode(
    make_app: Any,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hide_myst(monkeypatch)
    src = make_src(
        tmp_path,
        MARKDOWN_PAGE,
        config='prefect_on_error = "error"',
    )

    app = make_app(
        "html",
        srcdir=src,
        builddir=src / "_build",
        warningiserror=False,
    )

    with pytest.raises(SphinxError, match=r"sphinx-contrib-prefect\[markdown\]"):
        app.build()


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
