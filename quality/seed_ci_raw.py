"""Seed a small, realistic raw-zone dataset (SQLAlchemy-free fallback)."""

from datetime import datetime, timezone
import json
import psycopg2
import os
from dotenv import load_dotenv

def main():
    load_dotenv()
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

    conn = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        user=os.getenv("POSTGRES_USER", "streamline"),
        password=os.getenv("POSTGRES_PASSWORD", "streamline_local"),
        dbname=os.getenv("POSTGRES_DB", "streamline")
    )
    conn.autocommit = True

    try:
        with conn.cursor() as cur:
            cur.execute('CREATE SCHEMA IF NOT EXISTS raw')

            for table_name, table_rows in rows.items():
                # Drop and create table with text columns for simplicity in seed
                cur.execute(f'DROP TABLE IF EXISTS raw.{table_name} CASCADE')
                cols = table_rows[0].keys()
                cur.execute(f'CREATE TABLE raw.{table_name} (' + ", ".join([f'"{c}" TEXT' for c in cols]) + ')')

                for r in table_rows:
                    placeholders = ", ".join(["%s"] * len(cols))
                    cur.execute(f'INSERT INTO raw.{table_name} (' + ", ".join([f'"{c}"' for c in cols]) + f') VALUES ({placeholders})', list(r.values()))

            # Streaming events table
            cur.execute('DROP TABLE IF EXISTS raw.streaming_events CASCADE')
            cur.execute('''
                CREATE TABLE raw.streaming_events (
                    event_id text PRIMARY KEY,
                    event_type text NOT NULL,
                    event_timestamp timestamptz NOT NULL,
                    order_id text NOT NULL,
                    payload jsonb NOT NULL,
                    kafka_topic text NOT NULL,
                    kafka_partition integer NOT NULL,
                    kafka_offset bigint NOT NULL,
                    kafka_timestamp timestamptz,
                    ingested_at timestamptz NOT NULL DEFAULT now()
                )
            ''')

            payload = {
                "event_id": "ci-event-1",
                "event_type": "new_order",
                "event_timestamp": now.isoformat(),
                "order_id": "ci-order-1",
                "data": {"status": "created"},
            }

            cur.execute('''
                INSERT INTO raw.streaming_events
                (event_id, event_type, event_timestamp, order_id, payload, kafka_topic, kafka_partition, kafka_offset, kafka_timestamp)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', ("ci-event-1", "new_order", now, "ci-order-1", json.dumps(payload), "olist.order-events", 0, 0, now))

        print("Seed data loaded successfully!")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
