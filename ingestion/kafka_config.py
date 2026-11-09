"""Shared Kafka connection settings for the local Redpanda and hosted brokers."""

from __future__ import annotations

import os

from dotenv import load_dotenv


def kafka_settings() -> dict:
    load_dotenv()
    settings = {
        "bootstrap_servers": [
            broker.strip()
            for broker in os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:19092").split(",")
            if broker.strip()
        ],
        "security_protocol": os.getenv("KAFKA_SECURITY_PROTOCOL", "PLAINTEXT").upper(),
    }
    if settings["security_protocol"] in {"SASL_SSL", "SASL_PLAINTEXT"}:
        username = os.getenv("KAFKA_USERNAME")
        password = os.getenv("KAFKA_PASSWORD")
        if not username or not password:
            raise ValueError("KAFKA_USERNAME and KAFKA_PASSWORD are required for SASL Kafka brokers")
        settings.update(
            sasl_mechanism=os.getenv("KAFKA_SASL_MECHANISM", "SCRAM-SHA-256"),
            sasl_plain_username=username,
            sasl_plain_password=password,
        )
    return settings
