from datetime import date

import pandas as pd
import pytest

from api.churn.features import build_training_examples
from api.churn.training import normalize_version


def test_build_training_examples_uses_rfm_reviews_and_forward_churn_label():
    orders = pd.DataFrame(
        [
            {"order_id": "a1", "customer_unique_id": "a", "order_date": "2024-01-10", "order_total": 25, "order_status": "delivered"},
            {"order_id": "b1", "customer_unique_id": "b", "order_date": "2024-01-10", "order_total": 40, "order_status": "delivered"},
            {"order_id": "b2", "customer_unique_id": "b", "order_date": "2024-02-05", "order_total": 60, "order_status": "delivered"},
            {"order_id": "a2", "customer_unique_id": "a", "order_date": "2024-04-30", "order_total": 12, "order_status": "delivered"},
        ]
    )
    reviews = pd.DataFrame(
        [{"customer_unique_id": "a", "review_date": "2024-01-20", "review_score": 1}]
    )

    examples = build_training_examples(
        orders, reviews, lookback_days=30, label_horizon_days=20, snapshot_step_days=30
    )
    first_snapshot = examples.loc[examples["snapshot_date"] == pd.Timestamp(date(2024, 1, 31))]
    customer_a = first_snapshot.set_index("customer_unique_id").loc["a"]
    customer_b = first_snapshot.set_index("customer_unique_id").loc["b"]

    assert customer_a["frequency_180d"] == 1
    assert customer_a["monetary_180d"] == 25
    assert customer_a["mean_review_sentiment_180d"] == -1
    assert customer_a["churned_next_90d"] == 1
    assert customer_b["churned_next_90d"] == 0


@pytest.mark.parametrize("version, expected", [("1.2.3", "v1.2.3"), ("v2.0.1", "v2.0.1")])
def test_normalize_model_version(version, expected):
    assert normalize_version(version) == expected


def test_model_version_requires_semver():
    with pytest.raises(ValueError, match="semantic versioning"):
        normalize_version("latest")
