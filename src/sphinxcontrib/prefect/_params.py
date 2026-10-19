"""Render flow parameter tables from Prefect's OpenAPI-style schema."""

from __future__ import annotations

import inspect
import typing
from typing import TYPE_CHECKING, Any

from docutils import nodes
from sphinx import addnodes

from sphinxcontrib.prefect._models import (
    ANNOTATED,
    UNION_ORIGINS,
    ModelCollection,
    is_pydantic_model,
    model_target,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

    from sphinx.util.docutils import SphinxDirective

    from prefect import Flow

_MISSING_DEFAULT = "—"
_HEADERS = ("Parameter", "Type", "Required", "Default", "Description")


def render_parameter_table(
    directive: SphinxDirective,
    section: nodes.Element,
    flow: Flow,
    models: ModelCollection,
) -> None:
    """Append a parameter table to *section* when *flow* has parameters."""
    schema = flow.parameters.model_dump()
    properties = schema.get("properties") or {}
    if not properties:
        return

    required = set(schema.get("required") or ())
    signature = inspect.signature(flow.fn)
    linked_targets = {model_target(model) for model in models.models}
    ordered = sorted(
        properties.items(),
        key=lambda item: (item[1].get("position", 0), item[0]),
    )

    table = nodes.table(classes=["prefect-parameters"])
    table += nodes.title(text="Parameters")
    tgroup = nodes.tgroup(cols=len(_HEADERS))
    for width in (2, 2, 1, 1, 4):
        tgroup += nodes.colspec(colwidth=width)

    head = nodes.thead()
    head += _row(_HEADERS, header=True)
    tgroup += head

    body = nodes.tbody()
    for name, property_schema in ordered:
        annotation = models.hints.get(name, inspect.Parameter.empty)
        signature_default = signature.parameters[name].default
        has_default = _has_default(
            property_schema,
            annotation,
            signature_default,
        )
        body += _row(
            (
                _literal_cell(name),
                _type_cell(annotation, property_schema, linked_targets),
                _plain_cell(
                    "Optional" if name not in required or has_default else "Required"
                ),
                _literal_cell(
                    _default_text(property_schema, annotation, signature_default)
                ),
                _description_cell(directive, property_schema.get("description", "")),
            ),
            header=False,
        )
    tgroup += body
    table += tgroup
    section += table


def _row(cells: Iterable[Any], *, header: bool) -> nodes.row:
    """Build a table row from cell node lists or text headers."""
    row = nodes.row()
    for cell in cells:
        entry = nodes.entry()
        if header:
            entry += nodes.paragraph(text=str(cell))
        else:
            entry.extend(cell)
        row += entry
    return row


def _plain_cell(text: str) -> list[nodes.Node]:
    return [nodes.paragraph(text=text)]


def _literal_cell(text: str) -> list[nodes.Node]:
    paragraph = nodes.paragraph()
    paragraph += nodes.literal(text=text)
    return [paragraph]


def _has_default(
    property_schema: dict[str, Any],
    annotation: Any,
    signature_default: Any,
) -> bool:
    """Return whether a parameter has a value or factory default."""
    return (
        "default" in property_schema
        or _has_field_factory(annotation)
        or _is_factory_default(signature_default)
    )


def _default_text(
    property_schema: dict[str, Any],
    annotation: Any,
    signature_default: Any,
) -> str:
    """Format a parameter's default value or factory for display."""
    if "default" in property_schema:
        return repr(property_schema["default"])
    if _has_field_factory(annotation) or _is_factory_default(signature_default):
        return "factory"
    return _MISSING_DEFAULT


def _has_field_factory(annotation: Any) -> bool:
    """Return whether ``Annotated`` metadata carries a default factory."""
    if typing.get_origin(annotation) is not ANNOTATED:
        return False
    return any(
        getattr(metadata, "default_factory", None) is not None
        for metadata in typing.get_args(annotation)[1:]
    )


def _is_factory_default(default: Any) -> bool:
    """Return whether a signature default is a Pydantic field with a factory."""
    return getattr(default, "default_factory", None) is not None


def _description_cell(
    directive: SphinxDirective,
    description: Any,
) -> list[nodes.Node]:
    """Render a parameter description as reStructuredText."""
    if not description:
        return []
    return list(
        directive.parse_text_to_nodes(
            str(description),
            allow_section_headings=False,
        )
    )


def _type_cell(
    annotation: Any,
    property_schema: dict[str, Any],
    linked_targets: set[str],
) -> list[nodes.Node]:
    """Render a parameter's type, linking documented Pydantic models."""
    if annotation is not inspect.Parameter.empty:
        parts = _annotation_nodes(annotation, linked_targets)
        if parts:
            paragraph = nodes.paragraph()
            paragraph.extend(parts)
            return [paragraph]

    fallback = _schema_type(property_schema)
    return [nodes.paragraph(text=fallback or "Any")]


def _annotation_nodes(
    annotation: Any,
    linked_targets: set[str],
) -> list[nodes.Node]:
    """Return literal and cross-reference nodes describing *annotation*."""
    if annotation is inspect.Parameter.empty:
        return []
    if annotation is None or annotation is type(None):
        return [nodes.literal(text="None")]

    if typing.get_origin(annotation) is ANNOTATED:
        arguments = typing.get_args(annotation)
        return _annotation_nodes(arguments[0], linked_targets) if arguments else []

    origin = typing.get_origin(annotation)
    if origin in UNION_ORIGINS:
        result: list[nodes.Node] = []
        for index, argument in enumerate(typing.get_args(annotation)):
            if index:
                result.append(nodes.literal(text=" | "))
            result.extend(_annotation_nodes(argument, linked_targets))
        return result

    if is_pydantic_model(annotation):
        target = model_target(annotation)
        name = nodes.literal(text=annotation.__name__)
        if target not in linked_targets:
            return [name]
        return [
            addnodes.pending_xref(
                "",
                name,
                refdomain="py",
                reftype="class",
                reftarget=target,
                refexplicit=True,
            )
        ]

    if origin is not None:
        name = _origin_name(origin)
        arguments = typing.get_args(annotation)
        if not arguments:
            return [nodes.literal(text=name)]
        result = [nodes.literal(text=f"{name}[")]
        for index, argument in enumerate(arguments):
            if index:
                result.append(nodes.literal(text=", "))
            result.extend(_annotation_nodes(argument, linked_targets))
        result.append(nodes.literal(text="]"))
        return result

    if isinstance(annotation, type):
        return [nodes.literal(text=annotation.__name__)]
    return [nodes.literal(text=str(annotation))]


def _origin_name(origin: Any) -> str:
    """Return a readable name for a generic's origin."""
    name = getattr(origin, "__name__", None) or getattr(origin, "_name", None)
    if name:
        return name
    return str(origin).removeprefix("typing.")


def _schema_type(property_schema: dict[str, Any]) -> str:
    """Derive a display type from a Prefect parameter schema."""
    if "type" in property_schema:
        return str(property_schema["type"])
    if "anyOf" in property_schema:
        variants = [_schema_type(option) for option in property_schema["anyOf"]]
        return " | ".join(variant for variant in variants if variant)
    if "$ref" in property_schema:
        return str(property_schema["$ref"]).rsplit("/", 1)[-1]
    if "allOf" in property_schema:
        variants = [_schema_type(option) for option in property_schema["allOf"]]
        return " | ".join(variant for variant in variants if variant)
    return ""
