"""Resolve flow descriptions from docstrings and external files."""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, NamedTuple

from sphinxcontrib.prefect._errors import report_error
from sphinxcontrib.prefect._render import render_rst

if TYPE_CHECKING:
    from docutils import nodes
    from sphinx.util.docutils import SphinxDirective

    from prefect import Flow
    from sphinxcontrib.prefect._markers import MarkerResult

_MARKDOWN_SUFFIXES = {".md", ".markdown"}
_MYST_MISSING = (
    "Markdown description files require MyST; install "
    "'sphinx-contrib-prefect[markdown]'."
)


class _MystBindings(NamedTuple):
    """The MyST pieces imported lazily for Markdown rendering."""

    config_cls: type[Any]
    renderer_cls: type[Any]
    create_parser: Any


@dataclass(frozen=True)
class ExternalDescription:
    """Description text read from a file, and its markup format."""

    text: str
    format: Literal["rst", "markdown"] = "rst"


def resolve_flow_description(flow: Flow, markers: MarkerResult) -> str | None:
    """Return *flow*'s description with docstring marker syntax removed."""
    docstring = inspect.getdoc(flow.fn)
    if docstring is not None and flow.description == docstring:
        return markers.description or None
    return flow.description


def read_description_file(
    directive: SphinxDirective,
    path: str,
) -> ExternalDescription | None:
    """Read an external description relative to the Sphinx source directory."""
    source = Path(directive.env.srcdir) / path
    if not source.is_file():
        report_error(
            directive,
            f"Could not find description file {str(source)!r}.",
        )
        return None

    try:
        text = source.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        report_error(
            directive,
            f"Could not read description file {str(source)!r}: {exc}",
        )
        return None

    directive.env.note_dependency(str(source))
    description_format = (
        "markdown" if source.suffix.lower() in _MARKDOWN_SUFFIXES else "rst"
    )
    return ExternalDescription(text, format=description_format)


def render_external_description(
    directive: SphinxDirective,
    section: nodes.Element,
    description: ExternalDescription,
) -> None:
    """Parse an external description and append it to *section*."""
    if description.format == "rst":
        render_rst_description(directive, section, description.text)
        return

    myst = _load_myst()
    if myst is None:
        report_error(directive, _MYST_MISSING)
        return
    _render_markdown(directive, section, description.text, myst)


def render_rst_description(
    directive: SphinxDirective,
    section: nodes.Element,
    text: str,
) -> None:
    """Render a reStructuredText description in *section*."""
    render_rst(directive, section, inspect.cleandoc(text))


def _load_myst() -> _MystBindings | None:
    """Import MyST lazily so the core package does not depend on it."""
    try:
        from myst_parser.config.main import MdParserConfig
        from myst_parser.mdit_to_docutils.sphinx_ import SphinxRenderer
        from myst_parser.parsers.mdit import create_md_parser
    except ImportError:
        return None
    return _MystBindings(MdParserConfig, SphinxRenderer, create_md_parser)


def _section_renderer(base: type[Any]) -> type[Any]:
    """Return a MyST renderer that treats an existing section as its root."""

    class SectionRenderer(base):  # type: ignore[misc, valid-type]
        def setup_render(self, options: dict[str, Any], env: dict[str, Any]) -> None:
            super().setup_render(options, env)
            root = options["current_node"]
            self.current_node = root
            # MyST normally roots headings at the document. Root every level at
            # the flow section so description headings nest beneath it, even
            # when a fragment starts at H2 or deeper.
            self._level_to_section = dict.fromkeys(range(-1, 10), root)

    return SectionRenderer


def _render_markdown(
    directive: SphinxDirective,
    section: nodes.Element,
    text: str,
    myst: _MystBindings,
) -> None:
    """Render MyST Markdown *text* as children of *section*."""
    config = getattr(directive.env, "myst_config", None)
    if not isinstance(config, myst.config_cls):
        config = myst.config_cls()

    parser = myst.create_parser(config, _section_renderer(myst.renderer_cls))
    parser.options["document"] = directive.state.document
    parser.options["current_node"] = section

    renderer = parser.renderer
    renderer.setup_render(parser.options, {})
    # MyST has no public API for rendering a fragment below an existing section.
    # Its nested renderer handles the token stream and strips frontmatter.
    renderer.nested_render_text(text.rstrip(), 1, temp_root_node=section)
