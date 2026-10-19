"""Fixture Pydantic models used by the parameter tests."""

from __future__ import annotations

from pydantic import BaseModel, Field, RootModel


class Address(BaseModel):
    """A postal address."""

    street: str = Field(description="Street line.")
    city: str = Field(default="Springfield", description="City name.")


class Profile(BaseModel):
    """A user profile."""

    name: str = Field(description="Display name.")
    address: Address = Field(description="Where the user lives.")
    tags: list[str] = Field(default_factory=list, description="Free-form tags.")


class Node(BaseModel):
    """A self-referential node."""

    label: str = Field(description="Node label.")
    child: Node | None = Field(default=None, description="Nested child.")


class ProfileList(RootModel[list[Profile]]):
    """A root model wrapping a list of profiles."""


class Outer:
    """A container for a nested model."""

    class Nested(BaseModel):
        """A model nested inside another class."""

        value: int = Field(description="Nested value.")
