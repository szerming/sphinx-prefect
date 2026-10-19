"""Error-policy handling for Prefect directives."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sphinx.errors import SphinxError
from sphinx.util import logging

if TYPE_CHECKING:
    from sphinx.util.docutils import SphinxDirective

logger = logging.getLogger(__name__)


def report_error(directive: SphinxDirective, message: str) -> None:
    """Report a recoverable failure according to ``prefect_on_error``."""
    location = directive.get_source_info()
    if directive.config.prefect_on_error == "error":
        source, line = location
        prefix = f"{source}:{line}: " if source else ""
        raise SphinxError(f"{prefix}{message}")
    logger.warning(message, location=location)
