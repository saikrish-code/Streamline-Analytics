"""Validate raw Postgres tables with Great Expectations; exit non-zero on any failure."""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone

import great_expectations as gx
import great_expectations.expectations as gxe
from dotenv import load_dotenv
from sqlalchemy.engine import URL

from ingestion.load_olist import database_url
from ingestion.schema import STREAMING_EVENTS, TABLES

NULL_RATE_THRESHOLDS = {
    "customers": {
        "customer_id": 1.0,
        "customer_unique_id": 1.0,
        "customer_zip_code_prefix": 0.99,
        "customer_city": 0.99,
        "customer_state": 1.0,
    },
    "orders": {
        "order_id": 1.0,
        "customer_id": 1.0,
        "order_status": 1.0,
        "order_purchase_timestamp": 1.0,
        "order_estimated_delivery_date": 0.99,
    },
    "order_items": {
        "order_id": 1.0,
        "order_item_id": 1.0,
        "product_id": 1.0,
        "seller_id": 1.0,
        "price": 1.0,
        "freight_value": 1.0,
    },
    "payments": {
        "order_id": 1.0,
        "payment_sequential": 1.0,
        "payment_type": 1.0,
        "payment_installments": 1.0,
        "payment_value": 1.0,
    },
    "reviews": {
        "review_id": 0.99,
        "order_id": 1.0,
        "review_score": 1.0,
        "review_creation_date": 0.99,
    },
    "products": {
        "product_id": 1.0,
        "product_category_name": 0.95,
    },
    "streaming_events": {
        "event_id": 1.0,
        "event_type": 1.0,
        "event_timestamp": 1.0,
        "order_id": 1.0,
        "payload": 1.0,
        "kafka_topic": 1.0,
        "kafka_partition": 1.0,
        "kafka_offset": 1.0,
        "ingested_at": 1.0,
    },
}


def expected_columns() -> dict[str, list[str]]:
    expected = {
        name: [column.name for column in table.columns]
        for name, table in TABLES.items()
    }
    expected["streaming_events"] = [column.name for column in STREAMING_EVENTS.columns]
    return expected


def run_raw_checkpoint() -> bool:
    load_dotenv()
    context = gx.get_context()
    url = database_url()
    connection_string = url.render_as_string(hide_password=False) if isinstance(url, URL) else url
    data_source = context.data_sources.add_postgres(
        name="streamline_raw_postgres",
        connection_string=connection_string,
    )

    validation_definitions = []
    tables = expected_columns()
    now = datetime.now(timezone.utc)
    freshness_minutes = int(os.getenv("STREAMING_FRESHNESS_MINUTES", "30"))
    if freshness_minutes < 1:
        raise ValueError("STREAMING_FRESHNESS_MINUTES must be a positive integer")

    for table_name, columns in tables.items():
        asset = data_source.add_table_asset(
            name=f"raw_{table_name}",
            table_name=table_name,
            schema_name="raw",
        )
        batch_definition = asset.add_batch_definition_whole_table("whole_table")
        suite = context.suites.add(gx.ExpectationSuite(name=f"raw_{table_name}_suite"))
        suite.add_expectation(
            gxe.ExpectTableColumnsToMatchSet(column_set=columns, exact_match=True)
        )
        suite.add_expectation(gxe.ExpectTableColumnCountToEqual(value=len(columns)))

        for column, minimum_non_null_rate in NULL_RATE_THRESHOLDS[table_name].items():
            suite.add_expectation(
                gxe.ExpectColumnValuesToNotBeNull(
                    column=column,
                    mostly=minimum_non_null_rate,
                )
            )

        if table_name == "streaming_events":
            suite.add_expectation(gxe.ExpectTableRowCountToBeBetween(min_value=1))
            suite.add_expectation(
                gxe.ExpectColumnMaxToBeBetween(
                    column="event_timestamp",
                    min_value=(now - timedelta(minutes=freshness_minutes)).isoformat(),
                    max_value=(now + timedelta(minutes=2)).isoformat(),
                )
            )

        validation_definitions.append(
            context.validation_definitions.add(
                gx.ValidationDefinition(
                    name=f"raw_{table_name}_validation",
                    data=batch_definition,
                    suite=suite,
                )
            )
        )

    checkpoint = context.checkpoints.add(
        gx.Checkpoint(
            name="raw_zone_checkpoint",
            validation_definitions=validation_definitions,
        )
    )
    result = checkpoint.run()
    print(result.describe())
    return bool(result.success)


def main() -> None:
    try:
        success = run_raw_checkpoint()
    except Exception as exc:
        print(f"Raw-zone Great Expectations validation could not complete: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    if not success:
        print("Raw-zone expectations failed; downstream dbt build must not run.", file=sys.stderr)
        raise SystemExit(1)
    print("Raw-zone Great Expectations validation passed.")


if __name__ == "__main__":
    main()
