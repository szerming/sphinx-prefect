"""Tests for runtime DAG generation and Mermaid rendering."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest
from docutils import nodes
from helpers import build, copy_test_root, find_section
from sphinx.errors import SphinxError
from sphinxcontrib.mermaid import mermaid

from sphinxcontrib.prefect._graph import (
    parse_mermaid,
    strip_duplicate_suffix,
)

ROOT = Path(__file__).parent / "roots" / "test-dag"
SHOW_DAG_PAGE = (
    "DAG test\n========\n\n.. prefect-flow:: dag_pkg.flows.pipeline\n   :show-dag:\n"
)


@pytest.fixture(autouse=True)
def isolate_dag_package() -> None:
    """Import each temporary ``dag_pkg`` instead of a cached earlier copy."""
    for name in [name for name in sys.modules if name.split(".")[0] == "dag_pkg"]:
        del sys.modules[name]


def make_src(
    tmp_path: Path,
    body: str = SHOW_DAG_PAGE,
    *,
    config: str = "",
) -> Path:
    """Copy the DAG test root and optionally replace the page or config."""
    src = copy_test_root(ROOT, tmp_path, body, config=config)
    # A previous local build may have run a fixture flow in the source root.
    (src / "dag_pkg" / "executed.txt").unlink(missing_ok=True)
    return src


def graph_code(app: Any, title: str = "pipeline") -> str:
    """Return the Mermaid code in the section titled *title*."""
    section = find_section(app.env.get_doctree("index"), title)
    assert section is not None
    diagram = section.next_node(mermaid)
    assert diagram is not None
    return diagram["code"]


def executed(src: Path) -> bool:
    """Return whether a fixture flow wrote its execution marker."""
    return (src / "dag_pkg" / "executed.txt").exists()


def parameter_rows(section: nodes.Element) -> list[list[str]]:
    """Return the text of every parameter-table row in *section*."""
    tables = [
        table
        for table in section.findall(nodes.table)
        if table.next_node(nodes.title) is not None
        and table.next_node(nodes.title).astext() == "Parameters"
    ]
    assert len(tables) == 1
    return [
        [entry.astext() for entry in row.findall(nodes.entry)]
        for row in tables[0].findall(nodes.row)
    ]


def field_names(section: nodes.Element) -> list[str]:
    """Return the field names in *section*."""
    return [field[0].astext() for field in section.findall(nodes.field)]


def test_show_dag_renders_styled_graph(make_app: Any, tmp_path: Path) -> None:
    src = make_src(tmp_path)

    app = build(make_app, src)

    assert app.statuscode == 0
    assert not app.warning.getvalue()
    assert executed(src)

    code = graph_code(app)
    assert code.startswith("flowchart TD")
    assert 'extract_0["extract-0"]' in code
    assert 'clean_0["clean-0"]' in code
    assert 'transform_0["transform-0"]' in code
    assert "extract_0 --> clean_0" in code
    assert "clean_0 --> transform_0" in code

    assert 'prefect_main_flow["pipeline"]' in code
    assert "prefect_main_flow --> extract_0" in code
    assert "class prefect_main_flow prefectMain" in code
    assert "class extract_0 prefectTask" in code
    assert "class clean_0 prefectTask" in code
    assert "class transform_0 prefectSubflow" in code
    for class_name in (
        "prefectMain",
        "prefectSubflow",
        "prefectTask",
        "prefectUnknown",
    ):
        assert f"classDef {class_name}" in code

    html = (app.outdir / "index.html").read_text(encoding="utf-8")
    assert '<pre  class="mermaid">' in html
    assert "flowchart TD" in html
    assert "Legend:" in html
    assert "unknown node" in html


def test_subflow_and_task_sections_render(make_app: Any, tmp_path: Path) -> None:
    src = make_src(tmp_path)

    app = build(make_app, src)

    assert app.statuscode == 0
    assert not app.warning.getvalue()
    doctree = app.env.get_doctree("index")
    titles = [
        title.astext()
        for title in doctree.findall(nodes.title)
        if isinstance(title.parent, nodes.section)
    ]
    assert "Subflows" in titles
    assert "Tasks" in titles

    subflow = find_section(doctree, "transform")
    assert subflow is not None
    assert field_names(subflow) == ["Entrypoint", "Signature"]
    assert "dag_pkg.flows.transform" in subflow.astext()
    assert "Transform rows in a subflow." in subflow.astext()
    assert "rows: 'list[int]'" in subflow.astext()
    assert parameter_rows(subflow)[1][0] == "rows"

    task = find_section(doctree, "extract")
    assert task is not None
    assert field_names(task) == ["Signature"]
    assert "Extract a sample of records." in task.astext()
    assert "records: 'int'" in task.astext()
    assert parameter_rows(task)[1][0] == "records"

    html = (app.outdir / "index.html").read_text(encoding="utf-8")
    assert 'id="prefect-flow-dag-pkg-flows-transform"' in html
    assert 'href="#prefect-flow-dag-pkg-flows-transform"' in html
    assert 'id="prefect-task-dag-pkg-flows-extract"' in html
    assert 'href="#prefect-task-dag-pkg-flows-extract"' in html


def test_repeated_graph_nodes_document_one_section(
    make_app: Any,
    tmp_path: Path,
) -> None:
    src = make_src(
        tmp_path,
        "DAG test\n========\n\n"
        ".. prefect-flow:: dag_pkg.flows.with_repeated_task\n"
        "   :show-dag:\n",
    )

    app = build(make_app, src)

    assert app.statuscode == 0
    assert not app.warning.getvalue()
    code = graph_code(app, "with-repeated-task")
    assert 'extract_0["extract-0"]' in code
    assert 'extract_1["extract-1"]' in code
    titles = [
        title.astext()
        for title in app.env.get_doctree("index").findall(nodes.title)
        if isinstance(title.parent, nodes.section)
    ]
    assert titles.count("extract") == 1


def test_subflow_contents_are_not_expanded(make_app: Any, tmp_path: Path) -> None:
    src = make_src(tmp_path)

    app = build(make_app, src)

    assert app.statuscode == 0
    assert "summarize" not in graph_code(app)
    assert find_section(app.env.get_doctree("index"), "summarize") is None


def test_dag_disabled_does_not_execute_flow(make_app: Any, tmp_path: Path) -> None:
    src = make_src(
        tmp_path,
        "DAG test\n========\n\n.. prefect-flow:: dag_pkg.flows.pipeline\n",
    )

    app = build(make_app, src)

    assert app.statuscode == 0
    assert not app.warning.getvalue()
    assert not executed(src)
    assert any(
        str(path).endswith("dag_pkg/flows.py") for path in app.env.dependencies["index"]
    )
    section = find_section(app.env.get_doctree("index"), "pipeline")
    assert section is not None
    assert section.next_node(mermaid) is None


def test_global_enablement_generates_the_graph(
    make_app: Any,
    tmp_path: Path,
) -> None:
    src = make_src(
        tmp_path,
        "DAG test\n========\n\n.. prefect-flow:: dag_pkg.flows.pipeline\n",
        config="prefect_dag_enabled = True",
    )

    app = build(make_app, src)

    assert app.statuscode == 0
    assert not app.warning.getvalue()
    assert executed(src)
    assert "flowchart TD" in graph_code(app)


def test_no_dag_suppresses_global_enablement(
    make_app: Any,
    tmp_path: Path,
) -> None:
    src = make_src(
        tmp_path,
        "DAG test\n========\n\n.. prefect-flow:: dag_pkg.flows.pipeline\n   :no-dag:\n",
        config="prefect_dag_enabled = True",
    )

    app = build(make_app, src)

    assert app.statuscode == 0
    assert not app.warning.getvalue()
    assert not executed(src)
    section = find_section(app.env.get_doctree("index"), "pipeline")
    assert section is not None
    assert section.next_node(mermaid) is None


def test_show_dag_wins_over_no_dag(make_app: Any, tmp_path: Path) -> None:
    src = make_src(
        tmp_path,
        "DAG test\n========\n\n"
        ".. prefect-flow:: dag_pkg.flows.pipeline\n"
        "   :show-dag:\n"
        "   :no-dag:\n",
    )

    app = build(make_app, src)

    assert app.statuscode == 0
    assert executed(src)
    assert "flowchart TD" in graph_code(app)


def test_prefect_dag_directive_always_generates(
    make_app: Any,
    tmp_path: Path,
) -> None:
    src = make_src(
        tmp_path,
        "DAG test\n========\n\n.. prefect-dag:: dag_pkg.flows.pipeline\n",
    )

    app = build(make_app, src)

    assert app.statuscode == 0
    assert not app.warning.getvalue()
    assert executed(src)
    assert "flowchart TD" in graph_code(app)

    html = (app.outdir / "index.html").read_text(encoding="utf-8")
    assert 'id="prefect-dag-dag-pkg-flows-pipeline"' in html


def test_index_flags_apply_to_every_section(
    make_app: Any,
    tmp_path: Path,
) -> None:
    src = make_src(
        tmp_path,
        "DAG test\n========\n\n.. prefect-flow-index::\n   :show-dag:\n",
        config='prefect_modules = ["dag_pkg.flows"]\nprefect_main_flows = []',
    )

    app = build(make_app, src)

    assert app.statuscode == 0
    assert not app.warning.getvalue()
    assert executed(src)
    assert "flowchart TD" in graph_code(app)
    doctree = app.env.get_doctree("index")
    assert find_section(doctree, "Subflows") is not None
    assert find_section(doctree, "Tasks") is not None
    assert find_section(doctree, "needs-arguments") is None


def test_index_no_dag_suppresses_graphs(
    make_app: Any,
    tmp_path: Path,
) -> None:
    src = make_src(
        tmp_path,
        "DAG test\n========\n\n.. prefect-flow-index::\n   :no-dag:\n",
        config=(
            'prefect_modules = ["dag_pkg.flows"]\n'
            "prefect_main_flows = []\n"
            "prefect_dag_enabled = True"
        ),
    )

    app = build(make_app, src)

    assert app.statuscode == 0
    assert not app.warning.getvalue()
    assert not executed(src)
    section = find_section(app.env.get_doctree("index"), "pipeline")
    assert section is not None
    assert section.next_node(mermaid) is None


def test_empty_graph_renders_a_note(make_app: Any, tmp_path: Path) -> None:
    src = make_src(
        tmp_path,
        "DAG test\n========\n\n.. prefect-flow:: dag_pkg.flows.empty\n   :show-dag:\n",
    )

    app = build(make_app, src)

    assert app.statuscode == 0
    assert not app.warning.getvalue()
    section = find_section(app.env.get_doctree("index"), "empty")
    assert section is not None
    assert section.next_node(mermaid) is None
    assert "No tasks or subflows were observed" in section.astext()
    note = next(
        paragraph
        for paragraph in section.findall(nodes.paragraph)
        if "prefect-dag-empty" in paragraph["classes"]
    )
    assert "No tasks or subflows were observed" in note.astext()


def test_unknown_nodes_are_styled_and_listed_without_a_link(
    make_app: Any,
    tmp_path: Path,
) -> None:
    src = make_src(
        tmp_path,
        "DAG test\n========\n\n"
        ".. prefect-flow:: dag_pkg.flows.with_unknown\n"
        "   :show-dag:\n",
    )

    app = build(make_app, src)

    assert app.statuscode == 0
    code = graph_code(app, "with-unknown")
    assert 'external_task_0["external_task-0"]' in code
    assert "class external_task_0 prefectUnknown" in code

    unknown = find_section(app.env.get_doctree("index"), "Unknown nodes")
    assert unknown is not None
    assert "external_task" in unknown.astext()
    assert "unknown or external" in unknown.astext()

    html = (app.outdir / "index.html").read_text(encoding="utf-8")
    assert 'id="prefect-task-' not in html
    assert 'href="#prefect-task-' not in html


def test_malformed_subflow_marker_warns(make_app: Any, tmp_path: Path) -> None:
    src = make_src(
        tmp_path,
        "DAG test\n========\n\n"
        ".. prefect-flow:: dag_pkg.bad_markers.with_bad_subflow\n"
        "   :show-dag:\n",
    )

    app = build(make_app, src)

    assert app.statuscode == 0
    assert "Malformed main-flow frontmatter" in app.warning.getvalue()
    assert find_section(app.env.get_doctree("index"), "bad-subflow") is not None
    assert any(
        str(path).endswith("dag_pkg/bad_markers.py")
        for path in app.env.dependencies["index"]
    )


def test_malformed_subflow_marker_raises_in_strict_mode(
    make_app: Any,
    tmp_path: Path,
) -> None:
    src = make_src(
        tmp_path,
        "DAG test\n========\n\n"
        ".. prefect-flow:: dag_pkg.bad_markers.with_bad_subflow\n"
        "   :show-dag:\n",
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


def test_task_with_a_pydantic_model_parameter_is_documented(
    make_app: Any,
    tmp_path: Path,
) -> None:
    src = make_src(
        tmp_path,
        "DAG test\n========\n\n"
        ".. prefect-flow:: dag_pkg.flows.with_model_task\n"
        "   :show-dag:\n",
    )

    app = build(make_app, src)

    assert app.statuscode == 0
    assert not app.warning.getvalue()
    task = find_section(app.env.get_doctree("index"), "label")
    assert task is not None
    assert "Label a record." in task.astext()
    assert parameter_rows(task)[1][1] == "Record"
    assert "Record to label." in parameter_rows(task)[1][4]
    assert "Record" in task.astext()
    assert 'href="#prefect-task-dag-pkg-flows-label"' in (
        app.outdir / "index.html"
    ).read_text(encoding="utf-8")


def test_prefect_dag_renders_related_sections(
    make_app: Any,
    tmp_path: Path,
) -> None:
    src = make_src(
        tmp_path,
        "DAG test\n========\n\n.. prefect-dag:: dag_pkg.flows.pipeline\n",
    )

    app = build(make_app, src)

    assert app.statuscode == 0
    assert not app.warning.getvalue()
    doctree = app.env.get_doctree("index")
    assert find_section(doctree, "Subflows") is not None
    assert find_section(doctree, "Tasks") is not None
    assert find_section(doctree, "transform") is not None
    assert find_section(doctree, "extract") is not None


def test_ambiguous_nodes_warn_and_are_styled_unknown(
    make_app: Any,
    tmp_path: Path,
) -> None:
    src = make_src(
        tmp_path,
        "DAG test\n========\n\n"
        ".. prefect-flow:: dag_pkg.flows.with_ambiguous\n"
        "   :show-dag:\n",
    )

    app = build(make_app, src)

    assert app.statuscode == 0
    warnings = app.warning.getvalue()
    assert "matches multiple Flow or Task objects" in warnings
    code = graph_code(app, "with-ambiguous")
    assert "class ambiguous_0 prefectUnknown" in code

    unknown = find_section(app.env.get_doctree("index"), "Unknown nodes")
    assert unknown is not None
    assert "ambiguous name" in unknown.astext()
    html = (app.outdir / "index.html").read_text(encoding="utf-8")
    assert 'id="prefect-task-' not in html
    assert 'id="prefect-flow-dag-pkg-flows-ambiguous"' not in html
    assert 'href="#prefect-flow-dag-pkg-flows-ambiguous"' not in html
    assert 'href="#prefect-task-' not in html


def test_same_named_tasks_warn_and_are_styled_unknown(
    make_app: Any,
    tmp_path: Path,
) -> None:
    src = make_src(
        tmp_path,
        "DAG test\n========\n\n"
        ".. prefect-flow:: dag_pkg.flows.with_same_named_tasks\n"
        "   :show-dag:\n",
    )

    app = build(make_app, src)

    assert app.statuscode == 0
    assert "matches multiple Flow or Task objects" in app.warning.getvalue()
    code = graph_code(app, "with-same-named-tasks")
    assert "class twin_0 prefectUnknown" in code
    assert "class twin_1 prefectUnknown" in code

    unknown = find_section(app.env.get_doctree("index"), "Unknown nodes")
    assert unknown is not None
    assert "twin" in unknown.astext()
    html = (app.outdir / "index.html").read_text(encoding="utf-8")
    assert 'id="prefect-task-' not in html
    assert 'href="#prefect-task-' not in html


def test_missing_sample_arguments_warn_and_omit(
    make_app: Any,
    tmp_path: Path,
) -> None:
    src = make_src(
        tmp_path,
        "DAG test\n========\n\n"
        ".. prefect-flow:: dag_pkg.flows.needs_arguments\n"
        "   :show-dag:\n",
    )

    app = build(make_app, src)

    assert app.statuscode == 0
    warnings = app.warning.getvalue()
    assert "requires sample arguments for 'count'" in warnings
    assert "prefect_dag_sample_args" in warnings
    assert not executed(src)
    section = find_section(app.env.get_doctree("index"), "needs-arguments")
    assert section is not None
    assert section.next_node(mermaid) is None


def test_valid_sample_arguments_generate_the_graph(
    make_app: Any,
    tmp_path: Path,
) -> None:
    src = make_src(
        tmp_path,
        "DAG test\n========\n\n"
        ".. prefect-flow:: dag_pkg.flows.needs_arguments\n"
        "   :show-dag:\n",
        config=(
            'prefect_dag_sample_args = {"dag_pkg.flows.needs_arguments": {"count": 3}}'
        ),
    )

    app = build(make_app, src)

    assert app.statuscode == 0
    assert not app.warning.getvalue()
    assert executed(src)
    code = graph_code(app, "needs-arguments")
    assert 'extract_0["extract-0"]' in code


def test_invalid_sample_arguments_warn_and_omit(
    make_app: Any,
    tmp_path: Path,
) -> None:
    src = make_src(
        tmp_path,
        "DAG test\n========\n\n"
        ".. prefect-flow:: dag_pkg.flows.needs_arguments\n"
        "   :show-dag:\n",
        config=(
            "prefect_dag_sample_args = "
            '{"dag_pkg.flows.needs_arguments": {"unknown": 1}}'
        ),
    )

    app = build(make_app, src)

    assert app.statuscode == 0
    assert "configured sample arguments do not match" in app.warning.getvalue()
    section = find_section(app.env.get_doctree("index"), "needs-arguments")
    assert section is not None
    assert section.next_node(mermaid) is None


def test_invalid_sample_argument_config_warns_and_omits(
    make_app: Any,
    tmp_path: Path,
) -> None:
    src = make_src(
        tmp_path,
        "DAG test\n========\n\n"
        ".. prefect-flow:: dag_pkg.flows.pipeline\n"
        "   :show-dag:\n",
        config="prefect_dag_sample_args = []",
    )

    app = build(make_app, src)

    assert app.statuscode == 0
    assert "prefect_dag_sample_args must be a mapping" in app.warning.getvalue()
    section = find_section(app.env.get_doctree("index"), "pipeline")
    assert section is not None
    assert section.next_node(mermaid) is None


def test_missing_sample_arguments_raise_in_strict_mode(
    make_app: Any,
    tmp_path: Path,
) -> None:
    src = make_src(
        tmp_path,
        "DAG test\n========\n\n"
        ".. prefect-flow:: dag_pkg.flows.needs_arguments\n"
        "   :show-dag:\n",
        config='prefect_on_error = "error"',
    )

    app = make_app(
        "html",
        srcdir=src,
        builddir=src / "_build",
        warningiserror=False,
    )

    with pytest.raises(SphinxError, match="requires sample arguments"):
        app.build()


def test_submit_warns_and_omits_the_graph(
    make_app: Any,
    tmp_path: Path,
) -> None:
    src = make_src(
        tmp_path,
        "DAG test\n========\n\n"
        ".. prefect-flow:: dag_pkg.flows.unsupported_submit\n"
        "   :show-dag:\n",
    )

    app = build(make_app, src)

    assert app.statuscode == 0
    warnings = app.warning.getvalue()
    assert "Could not generate the runtime DAG" in warnings
    assert "asynchronous task call" in warnings
    section = find_section(app.env.get_doctree("index"), "unsupported-submit")
    assert section is not None
    assert section.next_node(mermaid) is None


def test_execution_failure_raises_in_strict_mode(
    make_app: Any,
    tmp_path: Path,
) -> None:
    src = make_src(
        tmp_path,
        "DAG test\n========\n\n"
        ".. prefect-flow:: dag_pkg.flows.unsupported_submit\n"
        "   :show-dag:\n",
        config='prefect_on_error = "error"',
    )

    app = make_app(
        "html",
        srcdir=src,
        builddir=src / "_build",
        warningiserror=False,
    )

    with pytest.raises(SphinxError, match="Could not generate the runtime DAG"):
        app.build()


def test_runtime_context_warns_and_omits_the_graph(
    make_app: Any,
    tmp_path: Path,
) -> None:
    src = make_src(
        tmp_path,
        "DAG test\n========\n\n"
        ".. prefect-flow:: dag_pkg.flows.needs_context\n"
        "   :show-dag:\n",
    )

    app = build(make_app, src)

    assert app.statuscode == 0
    warnings = app.warning.getvalue()
    assert "requires an active Prefect flow-run context" in warnings
    section = find_section(app.env.get_doctree("index"), "needs-context")
    assert section is not None
    assert section.next_node(mermaid) is None


def test_pure_flow_builds_with_a_dead_api_url(
    make_app: Any,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PREFECT_API_URL", "http://127.0.0.1:1/api")
    src = make_src(tmp_path)

    app = build(make_app, src)

    assert app.statuscode == 0
    assert not app.warning.getvalue()
    assert "flowchart TD" in graph_code(app)


def test_text_builder_does_not_crash(make_app: Any, tmp_path: Path) -> None:
    src = make_src(tmp_path)

    app = build(make_app, src, builder="text")

    assert app.statuscode == 0
    text = (app.outdir / "index.txt").read_text(encoding="utf-8")
    assert "[graph]" in text


def test_man_builder_does_not_crash(make_app: Any, tmp_path: Path) -> None:
    src = make_src(
        tmp_path,
        config='man_pages = [("index", "dag-test", "DAG test", ["Author"], 1)]',
    )

    app = build(make_app, src, builder="man")

    assert app.statuscode == 0
    man = (app.outdir / "dag-test.1").read_text(encoding="utf-8")
    assert "[graph]" in man


def test_parse_mermaid_extracts_nodes_and_edges() -> None:
    graph = parse_mermaid(
        "flowchart TD\n"
        '    first_0["first-0"]\n'
        '    second_1["second-1"]\n'
        "    first_0 --> second_1\n"
    )

    assert graph.header == "flowchart TD"
    assert [node.node_id for node in graph.nodes] == ["first_0", "second_1"]
    assert [node.name for node in graph.nodes] == ["first", "second"]
    assert [(edge.source, edge.target) for edge in graph.edges] == [
        ("first_0", "second_1")
    ]


def test_parse_mermaid_preserves_unrecognized_lines() -> None:
    graph = parse_mermaid(
        "flowchart TD\n"
        '    first_0["first-0"]\n'
        "    subgraph cluster\n"
        "    end\n"
        "    first_0 -->|next| second_0\n"
    )

    assert graph.nodes[0].node_id == "first_0"
    assert graph.extra_lines == (
        "subgraph cluster",
        "end",
        "first_0 -->|next| second_0",
    )


@pytest.mark.parametrize(
    ("label", "name"),
    [
        ("extract-0", "extract"),
        ("extract-12", "extract"),
        ("extract", "extract"),
        ("extract-v2-3", "extract-v2"),
    ],
)
def test_strip_duplicate_suffix(label: str, name: str) -> None:
    assert strip_duplicate_suffix(label) == name
