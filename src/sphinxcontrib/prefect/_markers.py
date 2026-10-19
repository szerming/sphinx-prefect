"""Parse main-flow markers from Prefect flow docstrings."""

from __future__ import annotations

import inspect
import re
from dataclasses import dataclass

import yaml

_AT_MAINFLOW = re.compile(r"^\s*@mainflow\s*$")
_MAINFLOW_FIELD = re.compile(r"^\s*:mainflow:\s*(?P<value>.*?)\s*$")


@dataclass(frozen=True)
class MarkerResult:
    """The main-flow selection and cleaned description parsed from a docstring."""

    is_main_flow: bool
    description: str
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()


def parse_mainflow_markers(docstring: str | None) -> MarkerResult:
    """Parse main-flow markers from *docstring* and strip their syntax.

    ``warnings`` contains non-fatal conflicts. ``errors`` contains malformed
    marker syntax that the caller must route through ``prefect_on_error``.
    """
    text = inspect.cleandoc(docstring) if docstring else ""
    markers: list[tuple[str, bool]] = []
    errors: list[str] = []

    lines, frontmatter_value, frontmatter_errors = _strip_frontmatter(text)
    errors.extend(frontmatter_errors)
    if frontmatter_value is not None:
        markers.append(("YAML frontmatter", frontmatter_value))

    description_lines: list[str] = []
    for line in lines:
        if _AT_MAINFLOW.match(line):
            markers.append(("'@mainflow' line", True))
        elif (match := _MAINFLOW_FIELD.match(line)) is not None:
            value = match.group("value").strip().lower()
            if value in {"", "true"}:
                markers.append(("':mainflow:' field", True))
            elif value == "false":
                markers.append(("':mainflow:' field", False))
            else:
                errors.append("Malformed ':mainflow:' field: expected true or false.")
        else:
            description_lines.append(line)

    true_markers = [label for label, value in markers if value]
    false_markers = [label for label, value in markers if not value]
    warnings: list[str] = []
    if true_markers and false_markers:
        warnings.append(
            "Conflicting main-flow markers: "
            f"{', '.join(true_markers)} select the flow, but "
            f"{', '.join(false_markers)} do not; treating it as a main flow."
        )

    return MarkerResult(
        is_main_flow=bool(true_markers),
        description="\n".join(description_lines).strip(),
        warnings=tuple(warnings),
        errors=tuple(errors),
    )


def _strip_frontmatter(text: str) -> tuple[list[str], bool | None, list[str]]:
    """Strip leading YAML frontmatter and return its ``mainflow`` value."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return lines, None, []

    closing = next(
        (index for index in range(1, len(lines)) if lines[index].strip() == "---"),
        None,
    )
    if closing is None:
        return (
            lines[1:],
            None,
            ["Malformed main-flow frontmatter: missing closing '---'."],
        )

    body = "\n".join(lines[1:closing])
    remaining = lines[closing + 1 :]
    if not body.strip():
        return remaining, None, []

    try:
        data = yaml.safe_load(body)
    except yaml.YAMLError as exc:
        problem = getattr(exc, "problem", str(exc))
        return remaining, None, [f"Malformed main-flow frontmatter: {problem}"]

    if data is None:
        return remaining, None, []
    if not isinstance(data, dict):
        return (
            remaining,
            None,
            ["Malformed main-flow frontmatter: expected a YAML mapping."],
        )

    value = data.get("mainflow")
    if value is None:
        return remaining, None, []
    if isinstance(value, bool):
        return remaining, value, []
    if isinstance(value, str) and value.lower() in {"true", "false"}:
        return remaining, value.lower() == "true", []
    return (
        remaining,
        None,
        ["Malformed main-flow frontmatter: 'mainflow' must be true or false."],
    )
