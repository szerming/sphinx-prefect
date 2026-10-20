"""Flow whose subflow carries malformed marker syntax."""

from __future__ import annotations

from prefect import flow


@flow
def bad_subflow(rows: list[int]) -> None:
    """---
    mainflow: maybe
    ---
    Run a subflow with a malformed marker.
    """


@flow
def with_bad_subflow() -> None:
    """Run a subflow whose docstring has malformed markers."""
    bad_subflow([1])
