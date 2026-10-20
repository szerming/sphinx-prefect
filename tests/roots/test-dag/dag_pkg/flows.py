"""Pure fixture flows for runtime DAG tests."""

from __future__ import annotations

from pathlib import Path

from prefect import flow, get_run_logger, task
from pydantic import BaseModel, Field

EXECUTED = Path(__file__).with_name("executed.txt")


class Record(BaseModel):
    """A record processed by a task."""

    name: str = Field(description="Record name.")


@task(viz_return_value=["record"])
def extract(records: int) -> list[int]:
    """Extract a sample of records."""
    return list(range(records))


@task(viz_return_value=["record"])
def clean(rows: list[int]) -> list[int]:
    """Remove empty rows."""
    return rows


@task
def summarize(rows: list[int]) -> int:
    """Summarize rows inside the subflow."""
    return len(rows)


@flow
def transform(rows: list[int]) -> None:
    """Transform rows in a subflow."""
    summarize(rows)


@flow
def pipeline(records: int = 2) -> None:
    """Run the pipeline under the visualizer.

    Args:
        records: Number of records to extract.

    @mainflow
    """
    EXECUTED.write_text("pipeline executed\n", encoding="utf-8")
    rows = extract(records)
    rows = clean(rows)
    transform(rows)


@task
def label(record: Record) -> str:
    """Label a record.

    Args:
        record: Record to label.
    """
    return record.name


@flow
def with_model_task() -> None:
    """Run a task with a Pydantic parameter."""
    EXECUTED.write_text("with_model_task executed\n", encoding="utf-8")
    label(Record(name="sample"))


@flow
def with_repeated_task(records: int = 1) -> None:
    """Run the same task twice.

    Args:
        records: Number of records to extract.
    """
    EXECUTED.write_text("with_repeated_task executed\n", encoding="utf-8")
    extract(records)
    extract(records)


@flow
def empty() -> None:
    """Run a flow without tasks or subflows."""
    EXECUTED.write_text("empty executed\n", encoding="utf-8")


@flow
def needs_arguments(count: int) -> None:
    """Run a flow with a required sample argument.

    Args:
        count: Number of records to process.
    """
    EXECUTED.write_text("needs_arguments executed\n", encoding="utf-8")
    extract(count)


@flow
def unsupported_submit(records: int = 1) -> None:
    """Run a flow using a task future, which Prefect cannot visualize."""
    EXECUTED.write_text("unsupported_submit executed\n", encoding="utf-8")
    extract.submit(records)


@flow
def needs_context() -> None:
    """Run a flow that asks Prefect for a run logger."""
    EXECUTED.write_text("needs_context executed\n", encoding="utf-8")
    get_run_logger().info("This flow requires a flow-run context.")


@flow
def with_unknown(records: int = 1) -> None:
    """Run a task defined outside this module.

    Args:
        records: Number of records to process.
    """
    EXECUTED.write_text("with_unknown executed\n", encoding="utf-8")
    from dag_pkg.external import external_task

    external_task(records)


@task(name="ambiguous")
def ambiguous_task(records: int) -> None:
    """Run a task whose name also belongs to a flow."""


@flow(name="ambiguous")
def ambiguous_flow(rows: list[int]) -> None:
    """Run a flow whose name also belongs to a task."""


@flow
def with_ambiguous(records: int = 1) -> None:
    """Run a task and a flow that share a name.

    Args:
        records: Number of records to process.
    """
    EXECUTED.write_text("with_ambiguous executed\n", encoding="utf-8")
    ambiguous_task(records)


@task(name="twin")
def twin_one(records: int) -> None:
    """Run the first task named twin."""


@task(name="twin")
def twin_two(records: int) -> None:
    """Run the second task named twin."""


@flow
def with_same_named_tasks(records: int = 1) -> None:
    """Run two distinct tasks that share a name.

    Args:
        records: Number of records to process.
    """
    EXECUTED.write_text("with_same_named_tasks executed\n", encoding="utf-8")
    twin_one(records)
    twin_two(records)
