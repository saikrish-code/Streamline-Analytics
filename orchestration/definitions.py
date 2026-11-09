"""Dagster assets and automation for batch and streaming ingestion."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from dagster import (
    AssetExecutionContext,
    AssetSelection,
    DefaultScheduleStatus,
    Definitions,
    Failure,
    ScheduleDefinition,
    asset,
    define_asset_job,
)
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
DBT_PROJECT = REPO_ROOT / "dbt_project"
load_dotenv(REPO_ROOT / ".env")


def _run_command(
    context: AssetExecutionContext,
    command: list[str],
    *,
    env_overrides: dict[str, str] | None = None,
) -> None:
    env = os.environ.copy()
    if env_overrides:
        env.update(env_overrides)
    context.log.info("Running: %s", " ".join(command))
    try:
        result = subprocess.run(
            command,
            cwd=REPO_ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
    except OSError as exc:
        raise Failure(description=f"Could not start {' '.join(command)}: {exc}") from exc

    if result.stdout:
        for line in result.stdout.rstrip().splitlines():
            context.log.info(line)
    if result.returncode:
        raise Failure(
            description=f"Command failed with exit code {result.returncode}: {' '.join(command)}"
        )


def _dbt_command(*args: str) -> list[str]:
    return [
        "dbt",
        *args,
        "--project-dir",
        str(DBT_PROJECT),
        "--profiles-dir",
        str(DBT_PROJECT),
    ]


@asset(description="Load the Olist CSVs into the Postgres raw zone.", compute_kind="python")
def raw_ingestion(context: AssetExecutionContext) -> bool:
    _run_command(context, [sys.executable, "-m", "ingestion.load_olist"])
    return True


@asset(description="Run the Great Expectations raw-zone checkpoint.", compute_kind="great_expectations")
def raw_zone_validation(context: AssetExecutionContext, raw_ingestion: bool) -> bool:
    del raw_ingestion
    _run_command(context, [sys.executable, "-m", "quality.validate_raw"])
    return True


@asset(description="Materialize all dbt models after raw validation.", compute_kind="dbt")
def dbt_run(context: AssetExecutionContext, raw_zone_validation: bool) -> bool:
    del raw_zone_validation
    _run_command(context, _dbt_command("run"))
    return True


@asset(description="Run dbt schema and singular tests after the model run.", compute_kind="dbt")
def dbt_test(context: AssetExecutionContext, dbt_run: bool) -> bool:
    del dbt_run
    _run_command(context, _dbt_command("test"))
    return True


@asset(description="Drain a bounded batch of Kafka events into raw.streaming_events.", compute_kind="kafka")
def streaming_event_ingestion(context: AssetExecutionContext) -> bool:
    _run_command(
        context,
        [sys.executable, "-m", "ingestion.consume_order_events"],
        env_overrides={
            "KAFKA_MAX_MESSAGES": os.getenv("STREAMING_BATCH_MAX_MESSAGES", "5000"),
            "KAFKA_IDLE_TIMEOUT_SECONDS": os.getenv("STREAMING_BATCH_IDLE_SECONDS", "10"),
            "KAFKA_MAX_RUNTIME_SECONDS": os.getenv("STREAMING_BATCH_MAX_RUNTIME_SECONDS", "240"),
        },
    )
    return True


@asset(description="Validate raw tables and streaming-event freshness before streaming dbt models.", compute_kind="great_expectations")
def streaming_raw_validation(
    context: AssetExecutionContext,
    streaming_event_ingestion: bool,
) -> bool:
    del streaming_event_ingestion
    _run_command(context, [sys.executable, "-m", "quality.validate_raw"])
    return True


@asset(description="Refresh the dbt streaming-event staging model.", compute_kind="dbt")
def streaming_dbt_run(context: AssetExecutionContext, streaming_raw_validation: bool) -> bool:
    del streaming_raw_validation
    _run_command(context, _dbt_command("run", "--select", "stg_streaming_events"))
    return True


@asset(description="Run dbt tests attached to the streaming-event staging model.", compute_kind="dbt")
def streaming_dbt_test(context: AssetExecutionContext, streaming_dbt_run: bool) -> bool:
    del streaming_dbt_run
    _run_command(context, _dbt_command("test", "--select", "stg_streaming_events"))
    return True


daily_batch_job = define_asset_job(
    name="daily_batch_pipeline",
    selection=AssetSelection.assets(raw_ingestion, raw_zone_validation, dbt_run, dbt_test),
)
streaming_events_job = define_asset_job(
    name="streaming_events_pipeline",
    selection=AssetSelection.assets(
        streaming_event_ingestion,
        streaming_raw_validation,
        streaming_dbt_run,
        streaming_dbt_test,
    ),
)

daily_batch_schedule = ScheduleDefinition(
    name="daily_batch_schedule",
    job=daily_batch_job,
    cron_schedule="0 2 * * *",
    execution_timezone="UTC",
    default_status=DefaultScheduleStatus.RUNNING,
)
streaming_events_schedule = ScheduleDefinition(
    name="streaming_events_schedule",
    job=streaming_events_job,
    cron_schedule="*/5 * * * *",
    execution_timezone="UTC",
    default_status=DefaultScheduleStatus.RUNNING,
)

defs = Definitions(
    assets=[
        raw_ingestion,
        raw_zone_validation,
        dbt_run,
        dbt_test,
        streaming_event_ingestion,
        streaming_raw_validation,
        streaming_dbt_run,
        streaming_dbt_test,
    ],
    jobs=[daily_batch_job, streaming_events_job],
    schedules=[daily_batch_schedule, streaming_events_schedule],
)
