"""Generate a stream of synthetic Olist-shaped order events to Kafka."""

from __future__ import annotations

import json
import logging
import os
import random
import signal
import time
import uuid
from datetime import datetime, timezone

from dotenv import load_dotenv
from kafka import KafkaProducer

from ingestion.kafka_config import kafka_settings

logger = logging.getLogger("order_event_generator")
STATUSES = {
    "created": ("approved", "canceled"),
    "approved": ("shipped", "canceled"),
    "shipped": ("delivered",),
}
PAYMENT_TYPES = ("credit_card", "boleto", "debit_card", "voucher")
CATEGORIES = ("health_beauty", "bed_bath_table", "sports_leisure", "computers_accessories", "watches_gifts")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def new_order_event() -> dict:
    order_id = str(uuid.uuid4())
    item_count = random.choices((1, 2, 3), weights=(0.78, 0.18, 0.04), k=1)[0]
    items = [
        {
            "product_id": str(uuid.uuid4()),
            "seller_id": str(uuid.uuid4()),
            "category": random.choice(CATEGORIES),
            "quantity": 1,
            "price": round(random.uniform(15, 650), 2),
            "freight_value": round(random.uniform(5, 80), 2),
        }
        for _ in range(item_count)
    ]
    return {
        "event_id": str(uuid.uuid4()),
        "event_type": "new_order",
        "event_timestamp": now_iso(),
        "order_id": order_id,
        "data": {
            "customer_id": str(uuid.uuid4()),
            "status": "created",
            "items": items,
            "payment_type": random.choice(PAYMENT_TYPES),
            "payment_installments": random.choices(
                (1, 2, 3, 6, 10), weights=(0.42, 0.14, 0.12, 0.20, 0.12), k=1
            )[0],
            "order_total": round(sum(item["price"] + item["freight_value"] for item in items), 2),
        },
    }


def status_change_event(order_id: str, old_status: str, new_status: str) -> dict:
    return {
        "event_id": str(uuid.uuid4()),
        "event_type": "order_status_change",
        "event_timestamp": now_iso(),
        "order_id": order_id,
        "data": {"previous_status": old_status, "status": new_status},
    }


def main() -> None:
    load_dotenv()
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(message)s",
    )
    topic = os.getenv("KAFKA_TOPIC", "olist.order-events")
    interval = float(os.getenv("PRODUCER_INTERVAL_SECONDS", "1.0"))
    status_rate = float(os.getenv("PRODUCER_STATUS_CHANGE_RATE", "0.4"))
    if interval < 0 or not 0 <= status_rate <= 1:
        raise ValueError("Interval must be non-negative and status change rate must be between 0 and 1")

    producer = KafkaProducer(
        **kafka_settings(),
        value_serializer=lambda value: json.dumps(value, separators=(",", ":")).encode("utf-8"),
        key_serializer=lambda key: key.encode("utf-8"),
        acks="all",
        retries=5,
    )
    running = True

    def stop(_signum, _frame):
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    active_orders: dict[str, str] = {}
    try:
        while running:
            should_change = active_orders and random.random() < status_rate
            if should_change:
                order_id = random.choice(tuple(active_orders))
                old_status = active_orders[order_id]
                new_status = random.choice(STATUSES[old_status])
                event = status_change_event(order_id, old_status, new_status)
                if new_status in {"delivered", "canceled"}:
                    del active_orders[order_id]
                else:
                    active_orders[order_id] = new_status
            else:
                event = new_order_event()
                active_orders[event["order_id"]] = "created"

            producer.send(topic, key=event["order_id"], value=event).get(timeout=30)
            logger.info("Produced %s for order %s", event["event_type"], event["order_id"])
            time.sleep(interval)
    finally:
        producer.flush()
        producer.close()


if __name__ == "__main__":
    main()
