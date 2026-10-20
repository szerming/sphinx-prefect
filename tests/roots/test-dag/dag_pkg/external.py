"""A task in a separate module, so the graph node is unknown to the flow module."""

from prefect import task


@task
def external_task(records: int) -> None:
    """Run a task defined outside the flow's module."""
