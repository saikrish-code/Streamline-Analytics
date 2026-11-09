"""Customer-level RFM and rating-sentiment feature generation."""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd

LOOKBACK_DAYS = 180
LABEL_HORIZON_DAYS = 90
SNAPSHOT_STEP_DAYS = 30

FEATURE_COLUMNS = [
    "recency_days",
    "frequency_180d",
    "monetary_180d",
    "average_order_value_180d",
    "mean_review_sentiment_180d",
    "negative_review_share_180d",
    "mean_review_score_180d",
    "review_count_180d",
]
TARGET_COLUMN = "churned_next_90d"


def _normalize_orders(orders: pd.DataFrame) -> pd.DataFrame:
    required = {"order_id", "customer_unique_id", "order_date", "order_total"}
    missing = required - set(orders.columns)
    if missing:
        raise ValueError(f"Order data is missing required columns: {sorted(missing)}")
    normalized = orders.copy()
    normalized["order_date"] = pd.to_datetime(normalized["order_date"], errors="coerce").dt.normalize()
    normalized["order_total"] = pd.to_numeric(normalized["order_total"], errors="coerce")
    normalized = normalized.dropna(subset=["order_id", "customer_unique_id", "order_date", "order_total"])
    if "order_status" in normalized.columns:
        normalized = normalized[~normalized["order_status"].isin(["canceled", "unavailable"])]
    return normalized


def _normalize_reviews(reviews: pd.DataFrame) -> pd.DataFrame:
    expected = {"customer_unique_id", "review_date", "review_score"}
    missing = expected - set(reviews.columns)
    if missing:
        raise ValueError(f"Review data is missing required columns: {sorted(missing)}")
    normalized = reviews.copy()
    normalized["review_date"] = pd.to_datetime(normalized["review_date"], errors="coerce").dt.normalize()
    normalized["review_score"] = pd.to_numeric(normalized["review_score"], errors="coerce")
    return normalized.dropna(subset=["customer_unique_id", "review_date", "review_score"])


def build_training_examples(
    orders: pd.DataFrame,
    reviews: pd.DataFrame,
    *,
    lookback_days: int = LOOKBACK_DAYS,
    label_horizon_days: int = LABEL_HORIZON_DAYS,
    snapshot_step_days: int = SNAPSHOT_STEP_DAYS,
) -> pd.DataFrame:
    """Build rolling customer snapshots and a forward inactivity label.

    Customers enter each snapshot when they have at least one non-canceled order in the
    preceding lookback window. Churn is 1 when no non-canceled order occurs in the following
    label horizon. The final snapshots are capped so their full label period is observable.
    """
    if min(lookback_days, label_horizon_days, snapshot_step_days) < 1:
        raise ValueError("Lookback, label horizon, and snapshot step must be positive days")

    order_rows = _normalize_orders(orders)
    review_rows = _normalize_reviews(reviews)
    if order_rows.empty:
        raise ValueError("No usable order records were found in marts.fact_orders")

    first_order = order_rows["order_date"].min().date()
    last_order = order_rows["order_date"].max().date()
    snapshot = first_order + timedelta(days=lookback_days)
    final_snapshot = last_order - timedelta(days=label_horizon_days)
    if snapshot > final_snapshot:
        raise ValueError(
            "Not enough order history for a complete lookback and churn-label window "
            f"({lookback_days} days before and {label_horizon_days} days after a snapshot)."
        )

    snapshots: list[date] = []
    while snapshot <= final_snapshot:
        snapshots.append(snapshot)
        snapshot += timedelta(days=snapshot_step_days)

    examples: list[pd.DataFrame] = []
    for as_of in snapshots:
        as_of_ts = pd.Timestamp(as_of)
        lookback_start = as_of_ts - pd.Timedelta(days=lookback_days)
        label_end = as_of_ts + pd.Timedelta(days=label_horizon_days)

        history = order_rows[
            (order_rows["order_date"] > lookback_start)
            & (order_rows["order_date"] <= as_of_ts)
        ]
        if history.empty:
            continue
        features = history.groupby("customer_unique_id", as_index=False).agg(
            last_order_date=("order_date", "max"),
            frequency_180d=("order_id", "nunique"),
            monetary_180d=("order_total", "sum"),
        )
        features["recency_days"] = (as_of_ts - features["last_order_date"]).dt.days
        features["average_order_value_180d"] = (
            features["monetary_180d"] / features["frequency_180d"]
        )

        future = order_rows[
            (order_rows["order_date"] > as_of_ts)
            & (order_rows["order_date"] <= label_end)
        ]
        future_orders = future.groupby("customer_unique_id")["order_id"].nunique()
        features[TARGET_COLUMN] = (
            features["customer_unique_id"].map(future_orders).fillna(0).eq(0).astype("int8")
        )

        review_window = review_rows[
            (review_rows["review_date"] > lookback_start)
            & (review_rows["review_date"] <= as_of_ts)
            & review_rows["customer_unique_id"].isin(features["customer_unique_id"])
        ]
        if review_window.empty:
            features["mean_review_sentiment_180d"] = np.nan
            features["negative_review_share_180d"] = np.nan
            features["mean_review_score_180d"] = np.nan
            features["review_count_180d"] = 0
        else:
            # Rating-derived sentiment is language-neutral for the mostly Portuguese reviews.
            review_window = review_window.assign(
                rating_sentiment=((review_window["review_score"] - 3.0) / 2.0).clip(-1.0, 1.0),
                is_negative=review_window["review_score"].le(2).astype("int8"),
            )
            review_features = review_window.groupby("customer_unique_id").agg(
                mean_review_sentiment_180d=("rating_sentiment", "mean"),
                negative_review_share_180d=("is_negative", "mean"),
                mean_review_score_180d=("review_score", "mean"),
                review_count_180d=("review_score", "count"),
            )
            features = features.merge(review_features, on="customer_unique_id", how="left")
            features["review_count_180d"] = features["review_count_180d"].fillna(0)

        features["snapshot_date"] = as_of_ts
        examples.append(features[["customer_unique_id", "snapshot_date", *FEATURE_COLUMNS, TARGET_COLUMN]])

    if not examples:
        raise ValueError("No customer snapshots could be generated from the marts data")
    return pd.concat(examples, ignore_index=True)
