"""Fixture objects that are not Prefect flows."""

from prefect import task


@task
def not_a_flow() -> None:
    """A task, which is not a flow."""
