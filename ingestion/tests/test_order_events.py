from datetime import datetime

from ingestion.generate_order_events import new_order_event, status_change_event


def test_new_order_event_has_positive_order_total_and_valid_items():
    event = new_order_event()

    assert event["event_type"] == "new_order"
    assert event["order_id"]
    assert datetime.fromisoformat(event["event_timestamp"])
    assert event["data"]["status"] == "created"
    assert event["data"]["items"]
    assert all(item["price"] > 0 and item["freight_value"] > 0 for item in event["data"]["items"])
    assert event["data"]["order_total"] > 0


def test_status_event_keeps_order_identity_and_transition():
    event = status_change_event("order-123", "created", "approved")

    assert event["event_type"] == "order_status_change"
    assert event["order_id"] == "order-123"
    assert event["data"] == {"previous_status": "created", "status": "approved"}
