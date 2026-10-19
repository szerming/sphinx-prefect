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


@flow
def marked_with_at(seed: int = 1) -> None:
    """Run a flow selected with a standalone marker.

    The marker is a docstring line, not a decorator.

    @mainflow
    """


@flow
def marked_with_frontmatter() -> None:
    """---
    mainflow: true
    ---
    Run a flow selected with YAML frontmatter.

    The frontmatter is stripped from the description.
    """


@flow
def marked_with_field() -> None:
    """Run a flow selected with a reST field.

    :mainflow:
    """


@flow
def conflicting_markers() -> None:
    """Run a flow with conflicting markers.

    @mainflow

    :mainflow: false
    """


@flow(description="Explicit description with *emphasis*.")
def explicit_description() -> None:
    """The docstring marker must not leak into the explicit description.

    @mainflow
    """


@flow
def malformed_markers() -> None:
    """---
    mainflow: [true
    ---
    Run a flow with malformed frontmatter.
    """


@flow
def missing_frontmatter_closing() -> None:
    """---
    mainflow: true
    Notes: this is description prose.
    """


@flow
def indented_field_literal() -> None:
    """Run a flow that shows marker syntax in a literal block.

    Example::

        :mainflow: true
    """


@task
def not_a_flow() -> None:
    """A task, which is not a flow."""


def plain_function() -> None:
    """A plain function, which is not a flow."""
