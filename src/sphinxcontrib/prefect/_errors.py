"""Error-policy handling for Prefect directives."""

from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Any

from sphinx.errors import SphinxError
from sphinx.util import logging

if TYPE_CHECKING:
    from collections.abc import Iterable

    from sphinx.util.docutils import SphinxDirective

logger = logging.getLogger(__name__)


def source_path(fn: Any) -> str | None:
    """Return the source file behind *fn*, if it has one.

    Falls back to the function's code object because ``inspect.getsourcefile``
    can return ``None`` for some dynamically created callables that still carry
    a usable ``co_filename``.
    """
    try:
        filename = inspect.getsourcefile(fn)
    except TypeError:
        filename = None
    if filename is None:
        code = getattr(fn, "__code__", None)
        filename = getattr(code, "co_filename", None)
    if not isinstance(filename, str):
        return None
    # Code objects created with ``exec`` carry pseudo-paths such as <string>.
    if filename.startswith("<") and filename.endswith(">"):
        return None
    return filename


def _describe_source(fn: Any) -> str:
    """Return a readable entrypoint and source path for *fn*."""
    # Imported lazily because ``_import`` uses :func:`source_note` itself.
    from sphinxcontrib.prefect._import import callable_entrypoint

    entrypoint = callable_entrypoint(fn)
    path = source_path(fn)
    if path is None:
        return f"flow {entrypoint}"
    return f"flow {entrypoint} at {path}"


def source_note(fn: Any) -> str:
    """Return a source-path suffix for a message that already names *fn*."""
    path = source_path(fn)
    return f" (source: {path})" if path is not None else ""


def with_source(message: str, fn: Any) -> str:
    """Append the source location of *fn* to a diagnostic message."""
    return f"{message} ({_describe_source(fn)})"


def with_sources(messages: Iterable[str], fn: Any) -> tuple[str, ...]:
    """Append the source location of *fn* to each diagnostic message."""
    return tuple(with_source(message, fn) for message in messages)


def report_error(directive: SphinxDirective, message: str) -> None:
    """Report a recoverable failure according to ``prefect_on_error``."""
    if directive.config.prefect_on_error == "error":
        source, line = directive.get_source_info()
        prefix = f"{source}:{line}: " if source else ""
        raise SphinxError(f"{prefix}{message}")
    report_warning(directive, message)


def report_warning(directive: SphinxDirective, message: str) -> None:
    """Emit a warning regardless of ``prefect_on_error``."""
    logger.warning(message, location=directive.get_source_info())


def report_diagnostics(
    directive: SphinxDirective,
    *,
    warnings: Iterable[str] = (),
    errors: Iterable[str] = (),
) -> None:
    """Route collected warnings and errors through the configured policy."""
    for message in warnings:
        report_warning(directive, message)
    for message in errors:
        report_error(directive, message)
