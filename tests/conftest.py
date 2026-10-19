"""Shared pytest configuration for the test suite."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest_plugins = ("sphinx.testing.fixtures",)


@pytest.fixture(scope="session")
def rootdir() -> Path:
    """Return the directory containing the Sphinx test roots."""
    return Path(__file__).parent / "roots"
