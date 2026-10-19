"""Fixture flows used by the directive tests."""

from prefect import flow, task


@flow(version="1.2.3")
def main(seed: int = 1) -> None:
    """Run the main fixture flow.

    This description uses *reStructuredText*.
    """


@flow
def undocumented() -> None:
    pass


@task
def not_a_flow() -> None:
    """A task, which is not a flow."""


def plain_function() -> None:
    """A plain function, which is not a flow."""
