"""Unit tests for main-flow docstring markers."""

from __future__ import annotations

import pytest

from sphinxcontrib.prefect._markers import parse_mainflow_markers


def test_no_docstring_has_no_markers() -> None:
    result = parse_mainflow_markers(None)

    assert result.is_main_flow is False
    assert result.description == ""
    assert result.warnings == ()
    assert result.errors == ()


def test_docstring_without_markers_is_unchanged() -> None:
    docstring = """Run the flow.

    This description has no selection metadata.
    """

    result = parse_mainflow_markers(docstring)

    assert result.is_main_flow is False
    assert result.description == (
        "Run the flow.\n\nThis description has no selection metadata."
    )
    assert result.warnings == ()
    assert result.errors == ()


def test_at_mainflow_line_selects_and_is_stripped() -> None:
    docstring = """Run the flow.

    @mainflow
    """

    result = parse_mainflow_markers(docstring)

    assert result.is_main_flow is True
    assert result.description == "Run the flow."
    assert "@mainflow" not in result.description


@pytest.mark.parametrize(
    "line",
    ["Use @mainflow to select the flow.", "@mainflow_extra", "  not @mainflow"],
)
def test_at_mainflow_must_be_a_standalone_line(line: str) -> None:
    result = parse_mainflow_markers(f"Run the flow.\n\n{line}\n")

    assert result.is_main_flow is False
    assert line.strip() in result.description


def test_yaml_frontmatter_true_selects_and_is_stripped() -> None:
    docstring = """---
    mainflow: true
    ---
    Run the flow.

    The frontmatter is not part of the description.
    """

    result = parse_mainflow_markers(docstring)

    assert result.is_main_flow is True
    assert result.description == (
        "Run the flow.\n\nThe frontmatter is not part of the description."
    )
    assert "mainflow" not in result.description
    assert "---" not in result.description


def test_yaml_frontmatter_false_does_not_select_and_is_stripped() -> None:
    docstring = """---
    mainflow: false
    ---
    Run the flow.
    """

    result = parse_mainflow_markers(docstring)

    assert result.is_main_flow is False
    assert result.description == "Run the flow."


def test_malformed_yaml_is_reported() -> None:
    docstring = """---
    mainflow: [true
    ---
    Run the flow.
    """

    result = parse_mainflow_markers(docstring)

    assert result.is_main_flow is False
    assert len(result.errors) == 1
    assert "frontmatter" in result.errors[0]
    assert "mainflow" not in result.description


def test_missing_frontmatter_closing_delimiter_is_reported_and_stripped() -> None:
    docstring = """---
    mainflow: true
    Notes: this is description prose.
    - a list item
    """

    result = parse_mainflow_markers(docstring)

    assert result.is_main_flow is False
    assert len(result.errors) == 1
    assert "missing closing" in result.errors[0]
    assert result.description == ("Notes: this is description prose.\n- a list item")


def test_yaml_mainflow_must_be_boolean() -> None:
    docstring = """---
    mainflow: sometimes
    ---
    Run the flow.
    """

    result = parse_mainflow_markers(docstring)

    assert len(result.errors) == 1
    assert "true or false" in result.errors[0]


@pytest.mark.parametrize(
    ("field", "expected"),
    [
        (":mainflow:", True),
        (":mainflow: true", True),
        (":mainflow: false", False),
    ],
)
def test_rst_field_markers(field: str, expected: bool) -> None:
    docstring = f"""Run the flow.

    {field}
    """

    result = parse_mainflow_markers(docstring)

    assert result.is_main_flow is expected
    assert result.description == "Run the flow."
    assert ":mainflow:" not in result.description


def test_invalid_rst_field_value_is_reported() -> None:
    docstring = """Run the flow.

    :mainflow: maybe
    """

    result = parse_mainflow_markers(docstring)

    assert len(result.errors) == 1
    assert "true or false" in result.errors[0]
    assert result.description == "Run the flow."


def test_indented_field_in_literal_block_is_not_a_marker() -> None:
    docstring = """Run the flow.

    Example::

        :mainflow: true
    """

    result = parse_mainflow_markers(docstring)

    assert result.is_main_flow is False
    assert ":mainflow: true" in result.description


def test_true_marker_wins_over_false_marker_with_a_warning() -> None:
    docstring = """Run the flow.

    @mainflow

    :mainflow: false
    """

    result = parse_mainflow_markers(docstring)

    assert result.is_main_flow is True
    assert len(result.warnings) == 1
    assert "Conflicting main-flow markers" in result.warnings[0]
    assert result.description == "Run the flow."


def test_all_marker_forms_can_coexist() -> None:
    docstring = """---
    mainflow: true
    ---
    Run the flow.

    @mainflow

    :mainflow: true
    """

    result = parse_mainflow_markers(docstring)

    assert result.is_main_flow is True
    assert result.warnings == ()
    assert result.errors == ()
    assert result.description == "Run the flow."
