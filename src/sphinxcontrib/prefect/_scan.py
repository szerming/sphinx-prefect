"""Discover main flows by scanning configured modules."""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sphinxcontrib.prefect._import import (
    ObjectResolutionError,
    flow_entrypoint,
    normalize_entrypoint,
    resolve_flow,
)
from sphinxcontrib.prefect._markers import MarkerResult, parse_mainflow_markers

if TYPE_CHECKING:
    from collections.abc import Iterable

    from prefect import Flow


@dataclass(frozen=True)
class FlowSelection:
    """A flow selected for documentation and the markers used to select it."""

    flow: Flow
    markers: MarkerResult


@dataclass(frozen=True)
class ScanResult:
    """Selected flows plus diagnostics collected while scanning modules."""

    flows: tuple[FlowSelection, ...] = ()
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()


def scan_main_flows(
    modules: Iterable[str],
    main_flows: Iterable[str],
) -> ScanResult:
    """Import *modules* and return the flows selected for documentation.

    A flow is selected when its docstring carries a true main-flow marker or
    when its entrypoint appears in *main_flows*. Explicit entrypoints outside
    *modules* are imported too. Flows keep module order, then attribute order;
    explicit flows outside the scanned modules follow in configuration order.
    """
    # Importing Prefect is deferred until a scan actually runs.
    from prefect import Flow

    warnings: list[str] = []
    errors: list[str] = []
    selections: list[FlowSelection] = []
    selected: set[str] = set()
    markers_by_entrypoint: dict[str, MarkerResult] = {}
    explicit: set[str] = set()
    explicit_entries: list[tuple[str, str]] = []

    for entrypoint in main_flows:
        try:
            canonical = normalize_entrypoint(entrypoint)
        except ObjectResolutionError as exc:
            errors.append(str(exc))
            continue
        explicit.add(canonical)
        explicit_entries.append((entrypoint, canonical))

    def markers_for(flow: Flow, entrypoint: str) -> MarkerResult:
        """Parse *flow*'s markers once and collect their diagnostics."""
        if entrypoint not in markers_by_entrypoint:
            markers = parse_mainflow_markers(flow.fn.__doc__)
            warnings.extend(markers.warnings)
            errors.extend(markers.errors)
            markers_by_entrypoint[entrypoint] = markers
        return markers_by_entrypoint[entrypoint]

    for module_name in modules:
        try:
            module = importlib.import_module(module_name)
        except Exception as exc:
            errors.append(
                f"Could not import module {module_name!r} for the main-flow scan: {exc}"
            )
            continue

        for attribute_name, obj in vars(module).items():
            if not isinstance(obj, Flow):
                continue
            entrypoint = flow_entrypoint(obj)
            if entrypoint in selected:
                continue
            markers = markers_for(obj, entrypoint)
            configured = normalize_entrypoint(f"{module.__name__}.{attribute_name}")
            if not (
                markers.is_main_flow or entrypoint in explicit or configured in explicit
            ):
                continue
            selected.add(entrypoint)
            selections.append(FlowSelection(obj, markers))

    for entrypoint, canonical in explicit_entries:
        if canonical in selected:
            continue
        try:
            flow = resolve_flow(entrypoint)
        except ObjectResolutionError as exc:
            errors.append(str(exc))
            continue
        resolved = flow_entrypoint(flow)
        if resolved in selected:
            continue
        markers = markers_for(flow, resolved)
        selected.add(resolved)
        selections.append(FlowSelection(flow, markers))

    return ScanResult(
        flows=tuple(selections),
        warnings=tuple(warnings),
        errors=tuple(errors),
    )
