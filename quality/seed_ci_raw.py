"""Seed a small, realistic raw-zone dataset for CI integration checks."""

from __future__ import annotations

from datetime import datetime, timezone

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from ingestion.load_olist import database_url
from ingestion.schema import RAW_SCHEMA, STREAMING_EVENTS, TABLES, metadata


def main() -> None:
    load_dotenv()
    engine = create_engine(database_url())
    now = datetime.now(timezone.utc)
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")

    rows = {
        "customers": [{
            "customer_id": "ci-customer-order-1",
            "customer_unique_id": "ci-customer-unique-1",
            "customer_zip_code_prefix": "01001",
            "customer_city": "sao paulo",
            "customer_state": "SP",
        }],
        "orders": [{
            "order_id": "ci-order-1",
            "customer_id": "ci-customer-order-1",
            "order_status": "delivered",
            "order_purchase_timestamp": timestamp,
            "order_approved_at": timestamp,
            "order_delivered_carrier_date": timestamp,
            "order_delivered_customer_date": timestamp,
            "order_estimated_delivery_date": timestamp,
        }],
        "order_items": [{
            "order_id": "ci-order-1",
            "order_item_id": 1,
            "product_id": "ci-product-1",
            "seller_id": "ci-seller-1",
            "shipping_limit_date": timestamp,
            "price": 100.00,
            "freight_value": 10.00,
        }],
        "payments": [{
            "order_id": "ci-order-1",
            "payment_sequential": 1,
            "payment_type": "credit_card",
            "payment_installments": 1,
            "payment_value": 110.00,
        }],
        "reviews": [{
            "review_id": "ci-review-1",
            "order_id": "ci-order-1",
            "review_score": 5,
            "review_comment_title": "great",
            "review_comment_message": "arrived as expected",
            "review_creation_date": timestamp,
            "review_answer_timestamp": timestamp,
        }],
        "products": [{
            "product_id": "ci-product-1",
            "product_category_name": "health_beauty",
            "product_name_length": 20,
            "product_description_length": 100,
            "product_photos_qty": 2,
            "product_weight_g": 500,
            "product_length_cm": 20,
            "product_height_cm": 10,
            "product_width_cm": 15,
        }],
    }
    event = {
        "event_id": "ci-event-1",
        "event_type": "new_order",
        "event_timestamp": now.isoformat(),
        "order_id": "ci-order-1",
        "data": {"status": "created"},
    }

    try:
        with engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{RAW_SCHEMA}"'))
        metadata.create_all(engine)
        with engine.begin() as connection:
            connection.execute(STREAMING_EVENTS.delete())
            for table_name, table_rows in rows.items():
                table = TABLES[table_name]
                connection.execute(table.delete())
                connection.execute(table.insert(), table_rows)
            connection.execute(
                STREAMING_EVENTS.insert().values(
                    event_id=event["event_id"],
                    event_type=event["event_type"],
                    event_timestamp=now,
                    order_id=event["order_id"],
                    payload=event,
                    kafka_topic="olist.order-events",
                    kafka_partition=0,
                    kafka_offset=0,
                    kafka_timestamp=now,
                )
            )
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
