"""Error-policy handling for Prefect directives."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sphinx.errors import SphinxError
from sphinx.util import logging

if TYPE_CHECKING:
    from collections.abc import Iterable

    from sphinx.util.docutils import SphinxDirective

logger = logging.getLogger(__name__)


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
