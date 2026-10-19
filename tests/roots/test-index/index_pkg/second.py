"""Fixture flows for the second scanned module."""

from prefect import flow


@flow
def delta() -> None:
    """Run the delta flow.

    :mainflow:
    """


@flow
def explicit_main() -> None:
    """Run the explicitly selected flow."""
