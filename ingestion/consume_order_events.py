"""Consume order events from Kafka and persist them idempotently to raw.streaming_events."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from kafka import KafkaConsumer
from sqlalchemy import create_engine, text

from ingestion.kafka_config import kafka_settings
from ingestion.load_olist import database_url
from ingestion.schema import metadata

logger = logging.getLogger("order_event_consumer")
INSERT_EVENT = text("""
INSERT INTO raw.streaming_events (
    event_id, event_type, event_timestamp, order_id, payload,
    kafka_topic, kafka_partition, kafka_offset, kafka_timestamp
) VALUES (
    :event_id, :event_type, :event_timestamp, :order_id, CAST(:payload AS jsonb),
    :kafka_topic, :kafka_partition, :kafka_offset, :kafka_timestamp
)
ON CONFLICT (event_id) DO NOTHING
""")


def main() -> None:
    load_dotenv()
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(message)s",
    )
    topic = os.getenv("KAFKA_TOPIC", "olist.order-events")
    consumer = KafkaConsumer(
        topic,
        **kafka_settings(),
        group_id=os.getenv("KAFKA_GROUP_ID", "streamline-order-events-to-postgres"),
        enable_auto_commit=False,
        auto_offset_reset=os.getenv("KAFKA_AUTO_OFFSET_RESET", "earliest"),
        max_poll_records=int(os.getenv("KAFKA_MAX_POLL_RECORDS", "500")),
        value_deserializer=lambda value: json.loads(value.decode("utf-8")),
    )
    engine = create_engine(database_url(), pool_pre_ping=True)
    try:
        with engine.begin() as connection:
            connection.execute(text("CREATE SCHEMA IF NOT EXISTS raw"))
        metadata.create_all(engine)

        while True:
            polled = consumer.poll(timeout_ms=1000)
            records = [record for partition_records in polled.values() for record in partition_records]
            if not records:
                continue
            inserted = 0
            with engine.begin() as connection:
                for record in records:
                    event = record.value
                    required = ("event_id", "event_type", "event_timestamp", "order_id", "data")
                    if any(field not in event for field in required):
                        raise ValueError(f"Invalid event at {record.topic}:{record.partition}:{record.offset}")
                    result = connection.execute(
                        INSERT_EVENT,
                        {
                            "event_id": event["event_id"],
                            "event_type": event["event_type"],
                            "event_timestamp": event["event_timestamp"],
                            "order_id": event["order_id"],
                            "payload": json.dumps(event),
                            "kafka_topic": record.topic,
                            "kafka_partition": record.partition,
                            "kafka_offset": record.offset,
                            "kafka_timestamp": (
                                datetime.fromtimestamp(record.timestamp / 1000, tz=timezone.utc)
                                if record.timestamp is not None
                                else None
                            ),
                        },
                    )
                    inserted += result.rowcount
            consumer.commit()
            logger.info("Persisted %d of %d consumed events", inserted, len(records))
    finally:
        consumer.close()
        engine.dispose()


if __name__ == "__main__":
    main()
