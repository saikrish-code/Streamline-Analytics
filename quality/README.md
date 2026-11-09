# Raw-zone quality gate

`python -m quality.validate_raw` runs the `raw_zone_checkpoint` with Great Expectations against all seven raw tables. It checks exact column sets and counts, per-column minimum non-null rates, and requires `raw.streaming_events` to contain data whose newest `event_timestamp` is within `STREAMING_FRESHNESS_MINUTES` (default 30). A database/schema/expectation error exits non-zero so downstream dbt work can stop. The non-null thresholds are declared in `validate_raw.py`; nullable review text and order lifecycle timestamps are intentionally not constrained.

Install the optional dependency with `python -m pip install -e ".[quality]"`. Set `DATABASE_URL` or the `POSTGRES_*` environment variables before running the command. Set `STREAMING_FRESHNESS_MINUTES` to tune the event recency window.

The GitHub Actions workflow provisions Postgres, seeds a small CI-only raw fixture, runs this checkpoint, then runs `dbt build` only if the quality step succeeds. The fixture exercises the gate and dbt dependency ordering; run the same validator against the target database in a deployment pipeline to validate its actual Olist rows.
