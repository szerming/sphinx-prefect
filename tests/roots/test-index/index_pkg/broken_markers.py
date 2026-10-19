"""Fixture flows with malformed selection metadata."""

from prefect import flow


@flow
def broken() -> None:
    """---
    mainflow: [true
    ---
    Run a flow with malformed frontmatter.
    """
