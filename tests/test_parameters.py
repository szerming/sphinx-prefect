"""Tests for parameter tables and Pydantic model documentation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from docutils import nodes
from helpers import build, copy_test_root, create_app, find_section
from sphinx import addnodes

ROOT = Path(__file__).parent / "roots" / "test-flow"


def make_src(tmp_path: Path, body: str, *, config: str = "") -> Path:
    """Copy the flow test root and replace its index page."""
    return copy_test_root(ROOT, tmp_path, body, config=config)


def parameter_table(section: nodes.Element) -> nodes.table:
    """Return the parameter table inside *section*."""
    tables = [
        table
        for table in section.findall(nodes.table)
        if table.next_node(nodes.title) is not None
        and table.next_node(nodes.title).astext() == "Parameters"
    ]
    assert len(tables) == 1
    return tables[0]


def row_texts(table: nodes.table) -> list[list[str]]:
    """Return the text of every table row."""
    return [
        [entry.astext() for entry in row.findall(nodes.entry)]
        for row in table.findall(nodes.row)
    ]


def model_names(doctree: nodes.document) -> list[str]:
    """Return the rendered Pydantic model class names in document order."""
    names: list[str] = []
    for desc_name in doctree.findall(addnodes.desc_name):
        signature = desc_name.parent
        description = signature.parent if signature is not None else None
        if (
            description is not None
            and description.get("domain") == "py"
            and description.get("objtype") == "class"
        ):
            names.append(desc_name.astext())
    return names


def test_renders_scalar_and_model_parameters(make_app: Any, tmp_path: Path) -> None:
    src = make_src(
        tmp_path,
        "Parameters\n==========\n\n"
        ".. prefect-flow:: fixture_pkg.flows.with_parameters\n",
    )

    app = build(make_app, src)

    assert app.statuscode == 0
    assert not app.warning.getvalue()
    section = find_section(app.env.get_doctree("index"), "with-parameters")
    assert section is not None

    table = parameter_table(section)
    assert row_texts(table) == [
        ["Parameter", "Type", "Required", "Default", "Description"],
        [
            "count",
            "int",
            "Required",
            "—",
            "Number of records to generate.",
        ],
        [
            "profile",
            "Profile",
            "Required",
            "—",
            "Profile of the user running the analysis.",
        ],
        [
            "label",
            "str | None",
            "Optional",
            "None",
            "Optional run label.",
        ],
    ]

    links = [
        reference["reftarget"]
        for reference in table.findall(addnodes.pending_xref)
        if reference.get("reftype") == "class"
    ]
    assert links == ["fixture_pkg.models.Profile"]


def test_renders_pydantic_models_with_fields(make_app: Any, tmp_path: Path) -> None:
    src = make_src(
        tmp_path,
        "Models\n======\n\n.. prefect-flow:: fixture_pkg.flows.with_parameters\n",
    )

    app = build(make_app, src)

    assert app.statuscode == 0
    assert not app.warning.getvalue()
    doctree = app.env.get_doctree("index")
    assert model_names(doctree) == ["Profile", "Address"]

    html = (app.outdir / "index.html").read_text(encoding="utf-8")
    assert "fixture_pkg.models.Profile" in html
    assert "Display name." in html
    assert "Free-form tags." in html
    assert "fixture_pkg.models.Address" in html
    assert "Street line." in html
    assert "Springfield" in html


def test_renders_factory_defaults(make_app: Any, tmp_path: Path) -> None:
    src = make_src(
        tmp_path,
        "Factory\n=======\n\n"
        ".. prefect-flow:: fixture_pkg.flows.with_factory_parameter\n",
    )

    app = build(make_app, src)

    assert app.statuscode == 0
    assert not app.warning.getvalue()
    section = find_section(app.env.get_doctree("index"), "with-factory-parameter")
    assert section is not None
    assert row_texts(parameter_table(section))[1] == [
        "tags",
        "list[str]",
        "Optional",
        "factory",
        "Tags to attach.",
    ]


def test_renders_signature_default_factories(make_app: Any, tmp_path: Path) -> None:
    src = make_src(
        tmp_path,
        "Factory\n=======\n\n"
        ".. prefect-flow:: fixture_pkg.flows.with_field_default_factory\n",
    )

    app = build(make_app, src)

    assert app.statuscode == 0
    assert not app.warning.getvalue()
    section = find_section(
        app.env.get_doctree("index"),
        "with-field-default-factory",
    )
    assert section is not None
    assert row_texts(parameter_table(section))[1] == [
        "tags",
        "list[str]",
        "Optional",
        "factory",
        "Tags to attach.",
    ]


@pytest.mark.parametrize(
    ("entrypoint", "title", "model"),
    [
        (
            "fixture_pkg.flows.local_model_flow",
            "local-model-flow",
            "LocalConfig",
        ),
        (
            "fixture_pkg.flows.with_nested_class",
            "with-nested-class",
            "Outer.Nested",
        ),
    ],
)
def test_local_and_nested_models_warn_and_are_omitted(
    make_app: Any,
    tmp_path: Path,
    entrypoint: str,
    title: str,
    model: str,
) -> None:
    src = make_src(
        tmp_path,
        f"Unimportable model\n==================\n\n.. prefect-flow:: {entrypoint}\n",
    )

    app = build(make_app, src)

    assert app.statuscode == 0
    warnings = app.warning.getvalue()
    assert model in warnings
    assert "not an importable class" in warnings
    assert not list(app.env.get_doctree("index").findall(addnodes.desc_name))
    assert find_section(app.env.get_doctree("index"), title) is not None


def test_text_builder_renders_parameters(make_app: Any, tmp_path: Path) -> None:
    src = make_src(
        tmp_path,
        "Text\n====\n\n.. prefect-flow:: fixture_pkg.flows.with_parameters\n",
    )

    app = make_app(
        "text",
        srcdir=src,
        builddir=src / "_build",
        warningiserror=False,
    )
    app.build()

    assert app.statuscode == 0
    assert not app.warning.getvalue()
    text = (app.outdir / "index.txt").read_text(encoding="utf-8")
    assert "Parameters" in text
    assert "fixture_pkg.models.Profile" in text


def test_renders_nested_and_recursive_models(make_app: Any, tmp_path: Path) -> None:
    src = make_src(
        tmp_path,
        "Nested models\n=============\n\n"
        ".. prefect-flow:: fixture_pkg.flows.with_nested_models\n",
    )

    app = build(make_app, src)

    assert app.statuscode == 0
    assert not app.warning.getvalue()
    doctree = app.env.get_doctree("index")
    assert model_names(doctree) == ["Profile", "Address", "Node"]
    assert model_names(doctree).count("Node") == 1

    html = (app.outdir / "index.html").read_text(encoding="utf-8")
    assert "Nested child." in html
    assert "Where the user lives." in html


def test_renders_models_nested_in_root_models(make_app: Any, tmp_path: Path) -> None:
    src = make_src(
        tmp_path,
        "Root model\n==========\n\n"
        ".. prefect-flow:: fixture_pkg.flows.with_root_model\n",
    )

    app = build(make_app, src)

    assert app.statuscode == 0
    assert not app.warning.getvalue()
    assert model_names(app.env.get_doctree("index")) == [
        "ProfileList",
        "Profile",
        "Address",
    ]


def test_dynamic_model_warns_and_is_omitted(make_app: Any, tmp_path: Path) -> None:
    src = make_src(
        tmp_path,
        "Dynamic model\n=============\n\n"
        ".. prefect-flow:: fixture_pkg.flows.with_dynamic_model\n",
    )

    app = build(make_app, src)

    assert app.statuscode == 0
    warnings = app.warning.getvalue()
    assert "DynamicParameter" in warnings
    assert "not an importable class" in warnings
    assert "index.rst" in warnings
    assert not list(app.env.get_doctree("index").findall(addnodes.desc_name))
    section = find_section(app.env.get_doctree("index"), "with-dynamic-model")
    assert section is not None
    assert row_texts(parameter_table(section))[1][0:2] == [
        "config",
        "DynamicParameter",
    ]


def test_dynamic_model_raises_in_strict_mode(make_app: Any, tmp_path: Path) -> None:
    from sphinx.errors import SphinxError

    src = make_src(
        tmp_path,
        "Dynamic model\n=============\n\n"
        ".. prefect-flow:: fixture_pkg.flows.with_dynamic_model\n",
        config='prefect_on_error = "error"',
    )

    app = create_app(make_app, src)

    with pytest.raises(SphinxError, match="not an importable class"):
        app.build()


def test_pydantic_v1_model_warns_and_is_omitted(
    make_app: Any,
    tmp_path: Path,
) -> None:
    src = make_src(
        tmp_path,
        "Legacy model\n============\n\n"
        ".. prefect-flow:: fixture_pkg.legacy.legacy_flow\n",
    )

    app = build(make_app, src)

    assert app.statuscode == 0
    warnings = app.warning.getvalue()
    assert "LegacyConfig" in warnings
    assert "uses Pydantic v1" in warnings
    assert "index.rst" in warnings
    assert not list(app.env.get_doctree("index").findall(addnodes.desc_name))
    section = find_section(app.env.get_doctree("index"), "legacy-flow")
    assert section is not None
    assert len(list(parameter_table(section).findall(nodes.row))) == 2


def test_pydantic_v1_model_raises_in_strict_mode(
    make_app: Any,
    tmp_path: Path,
) -> None:
    from sphinx.errors import SphinxError

    src = make_src(
        tmp_path,
        "Legacy model\n============\n\n"
        ".. prefect-flow:: fixture_pkg.legacy.legacy_flow\n",
        config='prefect_on_error = "error"',
    )

    app = create_app(make_app, src)

    with pytest.raises(SphinxError, match="uses Pydantic v1"):
        app.build()


def test_duplicate_models_across_pages_are_not_indexed_twice(
    make_app: Any,
    tmp_path: Path,
) -> None:
    src = make_src(
        tmp_path,
        "Duplicate models\n================\n\n"
        ".. prefect-flow:: fixture_pkg.flows.with_parameters\n\n"
        ".. toctree::\n\n"
        "   second\n",
    )
    (src / "second.rst").write_text(
        "Second page\n===========\n\n"
        ".. prefect-flow:: fixture_pkg.flows.with_nested_models\n",
        encoding="utf-8",
    )

    app = build(make_app, src)

    assert app.statuscode == 0
    assert "duplicate" not in app.warning.getvalue().lower()
    first_html = (app.outdir / "index.html").read_text(encoding="utf-8")
    second_html = (app.outdir / "second.html").read_text(encoding="utf-8")
    assert 'id="fixture_pkg.models.Profile"' in first_html
    assert 'id="fixture_pkg.models.Profile"' not in second_html
    assert "Display name." in second_html


def test_prefect_params_omits_description_and_dag(
    make_app: Any,
    tmp_path: Path,
) -> None:
    src = make_src(
        tmp_path,
        "Parameters only\n===============\n\n"
        ".. prefect-params:: fixture_pkg.flows.with_parameters\n",
    )

    app = build(make_app, src)

    assert app.statuscode == 0
    assert not app.warning.getvalue()
    doctree = app.env.get_doctree("index")
    section = find_section(doctree, "with-parameters")
    assert section is not None
    assert "Run a flow with scalar and model parameters." not in section.astext()
    assert parameter_table(section) is not None
    assert model_names(doctree) == ["Profile", "Address"]
    assert not list(doctree.findall(nodes.raw))
    assert 'id="prefect-params-fixture-pkg-flows-with-parameters"' in (
        app.outdir / "index.html"
    ).read_text(encoding="utf-8")


def test_index_renders_parameters_and_models(make_app: Any, tmp_path: Path) -> None:
    src = make_src(
        tmp_path,
        "Flow index\n==========\n\n.. prefect-flow-index::\n",
        config=(
            "prefect_modules = []\n"
            'prefect_main_flows = ["fixture_pkg.flows.with_parameters"]'
        ),
    )

    app = build(make_app, src)

    assert app.statuscode == 0
    assert not app.warning.getvalue()
    doctree = app.env.get_doctree("index")
    section = find_section(doctree, "with-parameters")
    assert section is not None
    assert row_texts(parameter_table(section))[1][0] == "count"
    assert model_names(doctree) == ["Profile", "Address"]


def test_parameter_table_is_omitted_without_parameters(
    make_app: Any,
    tmp_path: Path,
) -> None:
    src = make_src(
        tmp_path,
        "No parameters\n=============\n\n"
        ".. prefect-flow:: fixture_pkg.flows.undocumented\n",
    )

    app = build(make_app, src)

    assert app.statuscode == 0
    assert not app.warning.getvalue()
    section = find_section(app.env.get_doctree("index"), "undocumented")
    assert section is not None
    assert not list(section.findall(nodes.table))
    assert model_names(app.env.get_doctree("index")) == []
