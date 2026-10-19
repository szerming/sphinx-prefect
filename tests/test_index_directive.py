"""Tests for the ``prefect-flow-index`` directive and module scanning."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from helpers import (
    build,
    copy_test_root,
    create_app,
    find_section,
    section_titles,
)
from sphinx.errors import SphinxError

ROOT = Path(__file__).parent / "roots" / "test-index"
INDEX_BODY = "Flow index test\n===============\n\n.. prefect-flow-index::\n"


def make_src(tmp_path: Path, body: str = INDEX_BODY, *, config: str = "") -> Path:
    """Copy the index test root and optionally replace the page or config."""
    return copy_test_root(ROOT, tmp_path, body, config=config)


@pytest.mark.sphinx("html", testroot="index")
def test_index_renders_marked_and_explicit_flows_in_order(app: Any) -> None:
    app.build()

    assert app.statuscode == 0
    assert not app.warning.getvalue()

    doctree = app.env.get_doctree("index")
    assert section_titles(doctree) == [
        "Flow index test",
        "alpha",
        "gamma",
        "delta",
        "explicit-main",
        "outside-flow",
    ]

    alpha = find_section(doctree, "alpha")
    assert alpha is not None
    assert "index_pkg.first.alpha" in alpha.astext()
    assert "Run the alpha flow." in alpha.astext()
    assert "@mainflow" not in alpha.astext()

    gamma = find_section(doctree, "gamma")
    assert gamma is not None
    assert "Run the gamma flow selected with frontmatter." in gamma.astext()
    assert "mainflow: true" not in gamma.astext()

    outside = find_section(doctree, "outside-flow")
    assert outside is not None
    assert "index_pkg.outside.outside_flow" in outside.astext()
    assert "Run a flow outside the scanned modules." in outside.astext()

    html = (app.outdir / "index.html").read_text(encoding="utf-8")
    assert 'id="prefect-flow-index-pkg-first-alpha"' in html
    assert 'id="prefect-flow-index-pkg-second-explicit-main"' in html
    assert 'id="prefect-flow-index-pkg-outside-outside-flow"' in html


@pytest.mark.sphinx("html", testroot="index")
def test_index_omits_unmarked_flows_and_deduplicates(app: Any) -> None:
    app.build()

    doctree = app.env.get_doctree("index")
    titles = section_titles(doctree)
    assert "beta" not in titles
    assert "not-a-main-flow" not in titles
    assert titles.count("alpha") == 1
    assert titles.count("explicit-main") == 1


def test_index_accepts_show_dag_flag(make_app: Any, tmp_path: Path) -> None:
    src = make_src(
        tmp_path,
        "Flow index test\n===============\n\n.. prefect-flow-index::\n   :show-dag:\n",
    )

    app = build(make_app, src)

    assert app.statuscode == 0
    assert not app.warning.getvalue()
    assert find_section(app.env.get_doctree("index"), "alpha") is not None


def test_index_accepts_no_dag_flag(make_app: Any, tmp_path: Path) -> None:
    src = make_src(
        tmp_path,
        "Flow index test\n===============\n\n.. prefect-flow-index::\n   :no-dag:\n",
    )

    app = build(make_app, src)

    assert app.statuscode == 0
    assert not app.warning.getvalue()
    assert find_section(app.env.get_doctree("index"), "alpha") is not None


def test_explicit_alias_keeps_module_order(make_app: Any, tmp_path: Path) -> None:
    src = make_src(
        tmp_path,
        config=(
            'prefect_modules = ["index_pkg.first"]\n'
            'prefect_main_flows = ["index_pkg.first.beta_alias"]'
        ),
    )

    app = build(make_app, src)

    assert app.statuscode == 0
    assert not app.warning.getvalue()
    assert section_titles(app.env.get_doctree("index")) == [
        "Flow index test",
        "alpha",
        "beta",
        "gamma",
    ]


def test_same_named_flows_get_unique_anchors(make_app: Any, tmp_path: Path) -> None:
    src = make_src(
        tmp_path,
        config=(
            'prefect_modules = ["index_pkg.same_one", "index_pkg.same_two"]\n'
            "prefect_main_flows = []"
        ),
    )

    app = build(make_app, src)

    assert app.statuscode == 0
    assert not app.warning.getvalue()
    assert section_titles(app.env.get_doctree("index")) == [
        "Flow index test",
        "duplicate",
        "duplicate",
    ]

    html = (app.outdir / "index.html").read_text(encoding="utf-8")
    assert html.count('id="prefect-flow-index-pkg-same-one-duplicate"') == 1
    assert html.count('id="prefect-flow-index-pkg-same-two-duplicate"') == 1


def test_empty_scan_warns(make_app: Any, tmp_path: Path) -> None:
    src = make_src(
        tmp_path,
        config="prefect_modules = []\nprefect_main_flows = []",
    )

    app = build(make_app, src)

    assert app.statuscode == 0
    assert "found no main flows" in app.warning.getvalue()
    assert section_titles(app.env.get_doctree("index")) == ["Flow index test"]


def test_unimportable_module_warns_by_default(make_app: Any, tmp_path: Path) -> None:
    src = make_src(
        tmp_path,
        config=('prefect_modules = ["index_pkg.missing"]\nprefect_main_flows = []'),
    )

    app = build(make_app, src)

    assert app.statuscode == 0
    warnings = app.warning.getvalue()
    assert "Could not import module 'index_pkg.missing'" in warnings
    assert "index.rst" in warnings


def test_module_that_raises_on_import_warns(make_app: Any, tmp_path: Path) -> None:
    src = make_src(
        tmp_path,
        config=('prefect_modules = ["index_pkg.explodes"]\nprefect_main_flows = []'),
    )

    app = build(make_app, src)

    assert app.statuscode == 0
    warnings = app.warning.getvalue()
    assert "Could not import module 'index_pkg.explodes'" in warnings
    assert "index_pkg.explodes must not be imported" in warnings


def test_unimportable_module_raises_in_strict_mode(
    make_app: Any,
    tmp_path: Path,
) -> None:
    src = make_src(
        tmp_path,
        config=(
            'prefect_modules = ["index_pkg.missing"]\n'
            "prefect_main_flows = []\n"
            'prefect_on_error = "error"'
        ),
    )

    app = create_app(make_app, src)

    with pytest.raises(SphinxError, match="Could not import module"):
        app.build()


def test_main_flow_outside_modules_warns_when_missing(
    make_app: Any,
    tmp_path: Path,
) -> None:
    src = make_src(
        tmp_path,
        config=(
            'prefect_modules = []\nprefect_main_flows = ["index_pkg.missing.flow"]'
        ),
    )

    app = build(make_app, src)

    assert app.statuscode == 0
    assert "Could not import module 'index_pkg.missing'" in app.warning.getvalue()


def test_main_flow_with_wrong_type_warns(make_app: Any, tmp_path: Path) -> None:
    src = make_src(
        tmp_path,
        config=(
            "prefect_modules = []\n"
            'prefect_main_flows = ["index_pkg.wrong_type.not_a_flow"]'
        ),
    )

    app = build(make_app, src)

    assert app.statuscode == 0
    assert "not a Prefect flow" in app.warning.getvalue()


def test_malformed_markers_warn_by_default(make_app: Any, tmp_path: Path) -> None:
    src = make_src(
        tmp_path,
        config=(
            'prefect_modules = ["index_pkg.broken_markers"]\nprefect_main_flows = []'
        ),
    )

    app = build(make_app, src)

    assert app.statuscode == 0
    warnings = app.warning.getvalue()
    assert "Malformed main-flow frontmatter" in warnings
    assert "index.rst" in warnings


def test_malformed_markers_raise_in_strict_mode(
    make_app: Any,
    tmp_path: Path,
) -> None:
    src = make_src(
        tmp_path,
        config=(
            'prefect_modules = ["index_pkg.broken_markers"]\n'
            "prefect_main_flows = []\n"
            'prefect_on_error = "error"'
        ),
    )

    app = create_app(make_app, src)

    with pytest.raises(SphinxError, match="Malformed main-flow frontmatter"):
        app.build()
