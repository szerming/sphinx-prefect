"""Discover and render Pydantic models used as flow parameters."""

from __future__ import annotations

import importlib
import inspect
import types
import typing
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from sphinxcontrib.prefect._import import flow_entrypoint

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from docutils import nodes
    from sphinx.util.docutils import SphinxDirective

    from prefect import Flow

ANNOTATED = typing.Annotated
UNION_ORIGINS = frozenset({typing.Union, types.UnionType})


@dataclass(frozen=True)
class ModelCollection:
    """Importable models and resolved annotations for a flow's parameters."""

    models: tuple[type[BaseModel], ...] = ()
    hints: dict[str, Any] = field(default_factory=dict)
    errors: tuple[str, ...] = ()


def collect_flow_models(flow: Flow) -> ModelCollection:
    """Collect Pydantic v2 models from *flow*'s parameter annotations."""
    return collect_callable_models(
        flow.fn,
        owner=f"flow {flow_entrypoint(flow)!r}",
    )


def collect_callable_models(
    fn: Callable[..., Any],
    *,
    owner: str,
) -> ModelCollection:
    """Collect Pydantic v2 models from a flow's or task's callable annotations."""
    try:
        hints = typing.get_type_hints(fn, include_extras=True)
    except Exception as exc:
        return ModelCollection(
            errors=(f"Could not read type hints for {owner}: {exc}",)
        )

    collector = _ModelCollector()
    for name, parameter in inspect.signature(fn).parameters.items():
        annotation = hints.get(name, parameter.annotation)
        if annotation is inspect.Parameter.empty:
            continue
        collector.collect(annotation)

    return ModelCollection(
        models=tuple(collector.models),
        hints=hints,
        errors=tuple(collector.errors),
    )


@dataclass
class _ModelCollector:
    """Accumulate importable model classes while walking annotations."""

    models: list[type[BaseModel]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    seen: set[tuple[str, str]] = field(default_factory=set)

    def collect(self, annotation: Any) -> None:
        """Walk *annotation* and append importable Pydantic v2 classes."""
        if annotation is inspect.Parameter.empty or annotation is None:
            return
        if annotation is type(None):
            return

        if typing.get_origin(annotation) is ANNOTATED:
            arguments = typing.get_args(annotation)
            if arguments:
                self.collect(arguments[0])
            return

        origin = typing.get_origin(annotation)
        if origin in UNION_ORIGINS:
            for argument in typing.get_args(annotation):
                self.collect(argument)
            return

        if _is_pydantic_v1_model(annotation):
            self.errors.append(
                _not_documentable_message(annotation, "uses Pydantic v1")
            )
            return

        if is_pydantic_model(annotation):
            key = (annotation.__module__, annotation.__qualname__)
            if key in self.seen:
                return
            self.seen.add(key)

            if is_importable_model(annotation):
                self.models.append(annotation)
            else:
                self.errors.append(
                    _not_documentable_message(annotation, "is not an importable class")
                )

            for field in annotation.model_fields.values():
                self.collect(field.annotation)
            return

        if origin is not None:
            for argument in typing.get_args(annotation):
                self.collect(argument)


def render_model_sections(
    directive: SphinxDirective,
    section: nodes.Element,
    models: Iterable[type[BaseModel]],
) -> None:
    """Append one ``pydantic-model`` block per model to *section*.

    The first occurrence in a build indexes the model in the Python domain;
    later occurrences use ``:noindex:`` to avoid duplicate-object warnings.
    """
    models = tuple(models)
    if not models:
        return

    # Register at most one indexed object per model in the Python domain.
    # Later occurrences in the build use ``:noindex:``.
    domain = directive.env.domains.python_domain
    for model in models:
        target = model_target(model)
        lines = [
            f".. pydantic-model:: {target}",
            "   :show-field-summary:",
            "   :show-validator-summary:",
            "   :show-members:",
        ]
        if target in domain.objects:
            lines.append("   :noindex:")
        section.extend(
            directive.parse_text_to_nodes(
                "\n".join(lines),
                allow_section_headings=False,
            )
        )


def is_pydantic_model(obj: Any) -> bool:
    """Return whether *obj* is a Pydantic v2 ``BaseModel`` subclass."""
    try:
        return isinstance(obj, type) and issubclass(obj, BaseModel)
    except TypeError:
        return False


def is_importable_model(model: type[BaseModel]) -> bool:
    """Return whether *model* is a module-level, importable class."""
    if "." in model.__qualname__:
        return False
    try:
        module = importlib.import_module(model.__module__)
    except Exception:
        return False
    return getattr(module, model.__name__, None) is model


def model_target(model: type[BaseModel]) -> str:
    """Return the Python-domain target for *model*."""
    return f"{model.__module__}.{model.__name__}"


def _is_pydantic_v1_model(obj: Any) -> bool:
    """Return whether *obj* is a Pydantic v1 model class."""
    if not isinstance(obj, type):
        return False
    try:
        from pydantic.v1 import BaseModel as BaseModelV1
    except ImportError:
        return False
    try:
        return issubclass(obj, BaseModelV1)
    except TypeError:
        return False


def _not_documentable_message(model: type[Any], reason: str) -> str:
    name = f"{model.__module__}.{model.__qualname__}"
    return f"Pydantic model {name!r} {reason}; omitting its documentation."
