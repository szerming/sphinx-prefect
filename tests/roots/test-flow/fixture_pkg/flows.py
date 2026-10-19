"""Fixture flows used by the directive tests."""

from typing import Annotated

from prefect import flow, task
from pydantic import BaseModel, Field, create_model

from fixture_pkg.models import Node, Outer, Profile, ProfileList

# Deliberately not bound under its class name, so it looks importable only by
# walking ``__module__`` and ``__name__``.
dynamic_model = create_model(
    "DynamicParameter",
    value=(int, ...),
    __module__=__name__,
)


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


@flow
def markdown_looking_docstring() -> None:
    """Run a flow whose docstring looks like Markdown.

    # This is a docstring, not a Markdown heading
    """


@flow
def with_parameters(
    count: int,
    profile: Profile,
    label: str | None = None,
) -> None:
    """Run a flow with scalar and model parameters.

    Args:
        count: Number of records to generate.
        profile: Profile of the user running the analysis.
        label: Optional run label.
    """


@flow
def with_factory_parameter(
    tags: Annotated[list[str], Field(default_factory=list)],
) -> None:
    """Run a flow with a factory-backed parameter.

    Args:
        tags: Tags to attach.
    """


@flow
def with_field_default_factory(
    tags: list[str] = Field(default_factory=list),  # noqa: B008
) -> None:
    """Run a flow with a signature default factory.

    Args:
        tags: Tags to attach.
    """


@flow
def with_nested_class(config: Outer.Nested) -> None:
    """Run a flow with a model nested inside another class.

    Args:
        config: A nested model.
    """


def _make_local_model_flow():
    """Build a flow whose parameter model is local to this function."""

    class LocalConfig(BaseModel):
        value: int = Field(description="Local value.")

    @flow
    def local_model_flow(config: LocalConfig) -> None:
        """Run a flow with a local model.

        Args:
            config: A local model.
        """

    return local_model_flow


local_model_flow = _make_local_model_flow()


@flow
def with_nested_models(profile: Profile, node: Node) -> None:
    """Run a flow with nested and recursive models.

    Args:
        profile: Profile with a nested address.
        node: A self-referential tree node.
    """


@flow
def with_root_model(profiles: ProfileList) -> None:
    """Run a flow with a root-model parameter.

    Args:
        profiles: Profiles wrapped in a root model.
    """


@flow
def with_dynamic_model(config: dynamic_model) -> None:  # type: ignore[valid-type]
    """Run a flow with a dynamically generated model.

    Args:
        config: A model that cannot be imported by name.
    """


@task
def not_a_flow() -> None:
    """A task, which is not a flow."""


def plain_function() -> None:
    """A plain function, which is not a flow."""
