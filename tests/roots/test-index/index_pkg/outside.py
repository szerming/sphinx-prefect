"""Fixture flow outside ``prefect_modules``."""

from prefect import flow


@flow
def outside_flow() -> None:
    """Run a flow outside the scanned modules."""
