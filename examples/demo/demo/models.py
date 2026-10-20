"""Pydantic models used by the demo flows."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Owner(BaseModel):
    """The person responsible for a report."""

    name: str = Field(description="Display name of the report owner.")
    email: str = Field(description="Address that receives report notifications.")


class ReportConfig(BaseModel):
    """Configuration for a generated report."""

    title: str = Field(description="Title shown on the report dashboard.")
    owner: Owner = Field(description="Person responsible for the report.")
    tags: list[str] = Field(
        default_factory=list,
        description="Labels attached to the report.",
    )
