"""Fixture flows for the first scanned module."""

from prefect import flow


@flow
def alpha() -> None:
    """Run the alpha flow.

    @mainflow
    """


@flow
def beta() -> None:
    """Run the beta flow without a marker."""


# An alias that can be selected through prefect_main_flows.
beta_alias = beta


@flow
def gamma() -> None:
    """---
    mainflow: true
    ---
    Run the gamma flow selected with frontmatter.
    """


@flow
def not_a_main_flow() -> None:
    """Run a flow that is not selected."""
