"""First fixture module for duplicate flow names."""

from prefect import flow


@flow
def duplicate() -> None:
    """Run the duplicate flow from the first module.

    @mainflow
    """
