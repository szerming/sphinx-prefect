"""Lazy resolution of Prefect flows from importable entrypoints."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from prefect import Flow


class ObjectResolutionError(Exception):
    """Raised when an entrypoint cannot be resolved to a Prefect flow."""


def split_entrypoint(entrypoint: str) -> tuple[str, str]:
    """Split ``module.qualname`` or ``module:qualname`` into its parts."""
    entrypoint = entrypoint.strip()
    separator = ":" if ":" in entrypoint else "."
    module_name, found, attribute_path = entrypoint.rpartition(separator)
    if not found or not module_name.strip() or not attribute_path.strip():
        raise ObjectResolutionError(
            f"Invalid flow entrypoint {entrypoint!r}; "
            "expected 'module.qualname' or 'module:qualname'."
        )
    return module_name.strip(), attribute_path.strip()


def resolve_flow(entrypoint: str) -> Flow:
    """Import *entrypoint* lazily and return the Prefect flow it identifies."""
    module_name, attribute_path = split_entrypoint(entrypoint)
    try:
        module = importlib.import_module(module_name)
    except Exception as exc:
        raise ObjectResolutionError(
            f"Could not import module {module_name!r} for flow {entrypoint!r}: {exc}"
        ) from exc

    obj: Any = module
    for part in attribute_path.split("."):
        try:
            obj = getattr(obj, part)
        except AttributeError as exc:
            raise ObjectResolutionError(
                f"Could not find {attribute_path!r} in module {module_name!r}."
            ) from exc

    # Importing Prefect is deferred until an entrypoint is actually resolved.
    from prefect import Flow

    if not isinstance(obj, Flow):
        raise ObjectResolutionError(
            f"Object {entrypoint!r} is a {type(obj).__name__}, not a Prefect flow."
        )
    return obj
