"""Demo flows for the sphinx-contrib-prefect example project."""

from __future__ import annotations

from prefect import flow, task

from demo.models import ReportConfig


@task(viz_return_value=[{"row": 0, "value": 0}])
def extract(rows: int) -> list[dict[str, int]]:
    """Extract a deterministic sample of rows."""
    return [{"row": index, "value": index * 2} for index in range(rows)]


@task(viz_return_value=[{"row": 0, "value": 0}])
def transform(rows: list[dict[str, int]]) -> list[dict[str, int]]:
    """Scale every value for the report."""
    return [{**row, "value": row["value"] * 10} for row in rows]


@task
def publish(rows: list[dict[str, int]], title: str) -> None:
    """Publish the transformed rows to the report store."""


@task
def deliver_notification(email: str) -> None:
    """Deliver the notification through the configured channel."""


@flow
def notify_owner(email: str) -> None:
    """Tell the report owner that a new report is available.

    Args:
        email: Recipient address.
    """
    deliver_notification(email)


@flow(version="0.1.0")
def build_report(
    config: ReportConfig,
    rows: int = 12,
    dry_run: bool = False,
) -> None:
    """Build and publish a report.

    The flow extracts rows, transforms them, and publishes the result unless
    ``dry_run`` is true. It always notifies the report owner.

    Args:
        config: Report title, owner, and tags.
        rows: Number of sample rows to extract.
        dry_run: Skip publishing when true.

    @mainflow
    """
    extracted = extract(rows)
    transformed = transform(extracted)
    if not dry_run:
        publish(transformed, config.title)
    notify_owner(config.owner.email)


@task
def collect_metrics() -> None:
    """Collect the week's metrics from the report store."""


@flow
def weekly_digest() -> None:
    """---
    mainflow: true
    ---
    Build the weekly digest from the latest report.

    This flow is selected by YAML frontmatter at the start of its docstring.
    """
    collect_metrics()


@task
def ping_service() -> None:
    """Check that the reporting service answers."""


@flow
def health_check(timeout: float = 5.0) -> None:
    """Verify that the reporting pipeline can reach its dependencies.

    :mainflow:
    """
    ping_service()
