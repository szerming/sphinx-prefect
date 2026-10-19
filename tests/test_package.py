"""Tests for the extension package scaffold."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

import sphinxcontrib.prefect

SOURCE_ROOT = Path(__file__).parent.parent / "src"


class FakeApp:
    """Minimal stand-in for a Sphinx application."""

    def __init__(self) -> None:
        self.required_sphinx: list[str] = []
        self.extensions: list[str] = []
        self.config_values: list[tuple[str, Any, str]] = []
        self.directives: list[str] = []

    def require_sphinx(self, version: str) -> None:
        self.required_sphinx.append(version)

    def setup_extension(self, name: str) -> None:
        self.extensions.append(name)

    def add_config_value(
        self,
        name: str,
        default: Any,
        rebuild: str,
        types: Any = (),
    ) -> None:
        self.config_values.append((name, default, rebuild))

    def add_directive(self, name: str, directive: Any) -> None:
        self.directives.append(name)


def test_setup_returns_extension_metadata() -> None:
    app = FakeApp()

    metadata: dict[str, Any] = sphinxcontrib.prefect.setup(app)  # type: ignore[arg-type]

    assert metadata["version"] == "0.1.0"
    assert metadata["parallel_read_safe"] is False
    assert metadata["parallel_write_safe"] is True


def test_setup_requires_sphinx_9_and_dependencies() -> None:
    app = FakeApp()

    sphinxcontrib.prefect.setup(app)  # type: ignore[arg-type]

    assert app.required_sphinx == ["9.0"]
    assert app.extensions == [
        "sphinx.ext.autodoc",
        "sphinxcontrib.pydantic",
        "sphinxcontrib.mermaid",
    ]
    assert app.config_values == [("prefect_on_error", "warn", "env")]
    assert app.directives == ["prefect-flow"]


def test_sphinxcontrib_is_a_namespace_package() -> None:
    assert (SOURCE_ROOT / "sphinxcontrib" / "prefect" / "__init__.py").is_file()
    assert not (SOURCE_ROOT / "sphinxcontrib" / "__init__.py").exists()


@pytest.mark.sphinx("html", testroot="package")
def test_extension_builds_empty_page(app: Any) -> None:
    app.build()

    assert app.statuscode == 0
    assert (app.outdir / "index.html").is_file()
    assert app.extensions["sphinxcontrib.prefect"].version == "0.1.0"
