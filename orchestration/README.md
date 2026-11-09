# Dagster orchestration

`definitions.py` exposes Dagster assets and two enabled schedules:

- `daily_batch_pipeline`, daily at 02:00 UTC: `raw_ingestion` → `raw_zone_validation` → `dbt_run` → `dbt_test`.
- `streaming_events_pipeline`, every five minutes: bounded Kafka consume → raw-zone Great Expectations validation → run and test `stg_streaming_events`.

The streaming asset exits after reaching its idle timeout, message limit, or runtime cap. Defaults are a 10-second idle timeout, 5,000 messages, and a four-minute maximum run; set `STREAMING_BATCH_IDLE_SECONDS`, `STREAMING_BATCH_MAX_MESSAGES`, or `STREAMING_BATCH_MAX_RUNTIME_SECONDS` to change them. The long-running Kafka consumer defaults remain unchanged outside Dagster.

## Run locally

From the repository root, install the orchestration extras and start Dagster:

```sh
python -m pip install -e ".[orchestration,dbt,quality]"
dagster dev -h 0.0.0.0 -p 3000 -m orchestration.definitions
```

Set Postgres, Kafka, Olist data directory, and `STREAMING_FRESHNESS_MINUTES` environment variables before launching. `definitions.py` reads the root `.env` when one is present. The Dagster daemon runs with the UI process and evaluates both schedules.

## Railway / Render container

Build with the repository root as the Docker build context and deploy the root `Dockerfile`. Attach a persistent volume at `/data`; Dagster run history and instance state live under `/data/dagster`. Place the extracted Olist CSV files under `/data/olist` (or set `OLIST_DATA_DIR` to another mounted path). Configure `POSTGRES_*` or `DATABASE_URL`, Kafka connection settings, and the freshness/batch settings as service environment variables. The container listens on the platform `PORT` (3000 by default). Railway and Render both require a mounted volume for state that must survive restarts; Render persistent disks are available on paid services ([Railway volumes](https://docs.railway.com/volumes), [Render disks](https://render.com/docs/disks)).

This is a compact single-container Dagster deployment for a small workload. Keep the persistent volume attached to this service; do not run multiple replicas against the same local SQLite instance.
