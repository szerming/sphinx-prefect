"""Unit tests for module scanning and main-flow selection."""

from __future__ import annotations

from pathlib import Path

import pytest

from sphinxcontrib.prefect._scan import scan_main_flows

ROOT = Path(__file__).parent / "roots" / "test-index"


@pytest.fixture(autouse=True)
def index_package_on_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make the index fixture package importable for every test."""
    monkeypatch.syspath_prepend(str(ROOT))


def flow_names(modules: list[str], main_flows: list[str]) -> list[str]:
    """Return the selected flow names in scan order."""
    result = scan_main_flows(modules, main_flows)
    return [selection.flow.name for selection in result.flows]


def test_scan_orders_by_module_then_attribute() -> None:
    assert flow_names(
        ["index_pkg.first", "index_pkg.second"],
        [],
    ) == ["alpha", "gamma", "delta"]


def test_scan_includes_explicit_main_flows_and_deduplicates() -> None:
    names = flow_names(
        ["index_pkg.first"],
        [
            "index_pkg.first.alpha",
            "index_pkg.second.explicit_main",
            "index_pkg.outside.outside_flow",
        ],
    )

    assert names == ["alpha", "gamma", "explicit-main", "outside-flow"]


def test_scan_selects_an_aliased_entrypoint_at_module_position() -> None:
    assert flow_names(
        ["index_pkg.first"],
        ["index_pkg.first.beta_alias"],
    ) == ["alpha", "beta", "gamma"]


def test_scan_accepts_colon_entrypoints() -> None:
    assert flow_names(
        [],
        ["index_pkg.outside:outside_flow"],
    ) == ["outside-flow"]


def test_scan_reports_import_errors() -> None:
    result = scan_main_flows(["index_pkg.missing"], [])

    assert result.flows == ()
    assert len(result.errors) == 1
    assert "Could not import module 'index_pkg.missing'" in result.errors[0]


def test_scan_reports_marker_errors() -> None:
    result = scan_main_flows(["index_pkg.broken_markers"], [])

    assert result.flows == ()
    assert len(result.errors) == 1
    assert "Malformed main-flow frontmatter" in result.errors[0]


def test_scan_reports_invalid_main_flow_entrypoint() -> None:
    result = scan_main_flows([], ["not-an-entrypoint"])

    assert result.flows == ()
    assert len(result.errors) == 1
    assert "Invalid flow entrypoint" in result.errors[0]


def test_scan_reports_non_string_main_flow_entrypoint() -> None:
    result = scan_main_flows([], [42])  # type: ignore[list-item]

    assert result.flows == ()
    assert len(result.errors) == 1
    assert "expected a string" in result.errors[0]
