"""Fixture flow using a Pydantic v1 model."""

import warnings

from prefect import flow
from pydantic.v1 import BaseModel


class LegacyConfig(BaseModel):
    """Configuration declared with Pydantic v1."""

    value: int = 1


# Prefect builds its parameter schema at decoration time, and Pydantic warns
# when v1 and v2 schemas are mixed. The extension's own diagnostic is what the
# test asserts, so silence Pydantic's expected warning here.
with warnings.catch_warnings():
    warnings.filterwarnings("ignore", message="Mixing V1 models.*")

    @flow
    def legacy_flow(config: LegacyConfig = None) -> None:  # type: ignore[assignment]
        """Run a flow with a Pydantic v1 model.

        Args:
            config: Legacy configuration.
        """
