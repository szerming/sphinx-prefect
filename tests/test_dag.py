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


def test_dag_disabled_does_not_execute_flow(make_app: Any, tmp_path: Path) -> None:
    src = make_src(
        tmp_path,
        "DAG test\n========\n\n.. prefect-flow:: dag_pkg.flows.pipeline\n",
    )

    app = build(make_app, src)

    assert app.statuscode == 0
    assert not app.warning.getvalue()
    assert not executed(src)
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
    assert find_section(app.env.get_doctree("index"), "needs-arguments") is None


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


def test_unknown_nodes_are_styled(make_app: Any, tmp_path: Path) -> None:
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
