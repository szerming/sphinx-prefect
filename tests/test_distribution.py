"""Tests for the distributable package metadata."""

from __future__ import annotations

import tomllib
from pathlib import Path

ROOT = Path(__file__).parent.parent


def project() -> dict[str, object]:
    """Return the parsed ``[project]`` table from ``pyproject.toml``."""
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return data["project"]


def test_project_declares_the_supported_version_ranges() -> None:
    metadata = project()

    assert metadata["requires-python"] == ">=3.12,<3.15"
    dependencies = metadata["dependencies"]
    assert isinstance(dependencies, list)
    assert "sphinx>=9,<10" in dependencies
    assert "prefect>=3,<4" in dependencies
    assert "pydantic>=2.10,<3" in dependencies


def test_project_declares_the_mit_license() -> None:
    metadata = project()

    assert metadata["license"] == "MIT"
    assert metadata["license-files"] == ["LICENSE"]


def test_project_declares_distribution_classifiers() -> None:
    classifiers = project()["classifiers"]
    assert isinstance(classifiers, list)

    assert "Framework :: Sphinx :: Extension" in classifiers
    assert "Programming Language :: Python :: 3.12" in classifiers
    assert "Programming Language :: Python :: 3.13" in classifiers
