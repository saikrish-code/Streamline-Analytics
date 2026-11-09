"""Train and version the customer churn classifier from dbt marts."""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import sklearn
import scipy
from dotenv import load_dotenv
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sqlalchemy import create_engine, text

from api.churn.features import (
    FEATURE_COLUMNS,
    LABEL_HORIZON_DAYS,
    LOOKBACK_DAYS,
    TARGET_COLUMN,
    build_training_examples,
)
from ingestion.load_olist import database_url

ORDERS_SQL = text("""
select
    fact.order_id,
    fact.customer_unique_id,
    dates.date_day as order_date,
    sum(fact.item_total)::double precision as order_total,
    max(fact.order_status) as order_status
from marts.fact_orders as fact
join marts.dim_date as dates
    on fact.date_key = dates.date_key
join marts.dim_customers as customers
    on fact.customer_unique_id = customers.customer_unique_id
group by fact.order_id, fact.customer_unique_id, dates.date_day
""")
REVIEWS_SQL = text("""
select customer_unique_id, review_created_at as review_date, review_score
from marts.fact_reviews
where review_score is not null
""")
VERSION_PATTERN = re.compile(r"^v?\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")


def normalize_version(version: str) -> str:
    if not VERSION_PATTERN.fullmatch(version):
        raise ValueError("Model version must use semantic versioning, for example 1.0.0")
    return version if version.startswith("v") else f"v{version}"


def default_registry_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "model_registry" / "churn"


def _split_examples(examples: pd.DataFrame):
    snapshots = sorted(examples["snapshot_date"].drop_duplicates())
    if len(snapshots) >= 4:
        holdout_count = max(1, round(len(snapshots) * 0.2))
        holdout_start = snapshots[-holdout_count]
        train = examples[examples["snapshot_date"] < holdout_start]
        test = examples[examples["snapshot_date"] >= holdout_start]
        if train[TARGET_COLUMN].nunique() == 2 and not test.empty:
            return train, test, "latest_time_snapshots"

    if examples[TARGET_COLUMN].nunique() != 2 or examples[TARGET_COLUMN].value_counts().min() < 2:
        raise ValueError("Training data must contain at least two examples from each churn class")
    train, test = train_test_split(
        examples,
        test_size=0.2,
        random_state=42,
        stratify=examples[TARGET_COLUMN],
    )
    return train, test, "stratified_random_fallback"


def _evaluate(model: Pipeline, test: pd.DataFrame) -> dict[str, float | None]:
    actual = test[TARGET_COLUMN].astype(int)
    predicted = model.predict(test[FEATURE_COLUMNS]).astype(int)
    probabilities = model.predict_proba(test[FEATURE_COLUMNS])[:, list(model.classes_).index(1)]
    both_classes = actual.nunique() == 2
    return {
        "accuracy": float(accuracy_score(actual, predicted)),
        "precision": float(precision_score(actual, predicted, zero_division=0)),
        "recall": float(recall_score(actual, predicted, zero_division=0)),
        "f1": float(f1_score(actual, predicted, zero_division=0)),
        "roc_auc": float(roc_auc_score(actual, probabilities)) if both_classes else None,
        "average_precision": float(average_precision_score(actual, probabilities)),
    }


def _read_marts(engine) -> tuple[pd.DataFrame, pd.DataFrame]:
    with engine.connect() as connection:
        orders = pd.read_sql_query(ORDERS_SQL, connection)
        reviews = pd.read_sql_query(REVIEWS_SQL, connection)
    if orders.empty:
        raise ValueError("marts.fact_orders is empty; run dbt before training")
    if reviews.empty:
        reviews = pd.DataFrame(columns=["customer_unique_id", "review_date", "review_score"])
    return orders, reviews


def train_and_save(version: str | None = None, registry_dir: Path | None = None) -> dict[str, Any]:
    load_dotenv()
    model_version = normalize_version(version or os.getenv("CHURN_MODEL_VERSION", "1.0.0"))
    registry = Path(registry_dir or os.getenv("CHURN_MODEL_REGISTRY", default_registry_dir()))
    version_dir = registry / model_version
    if version_dir.exists():
        raise FileExistsError(
            f"{version_dir} already exists. Increment CHURN_MODEL_VERSION for a new immutable model artifact."
        )

    engine = create_engine(database_url(), pool_pre_ping=True)
    try:
        orders, reviews = _read_marts(engine)
    finally:
        engine.dispose()

    examples = build_training_examples(orders, reviews)
    if len(examples) < 20:
        raise ValueError(f"Only {len(examples)} training examples were generated; at least 20 are required")
    train, test, split_strategy = _split_examples(examples)
    if train[TARGET_COLUMN].nunique() != 2:
        raise ValueError("Training split contains only one churn class")

    model = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True)),
            ("scaler", StandardScaler()),
            (
                "classifier",
                LogisticRegression(
                    class_weight="balanced",
                    max_iter=2000,
                    random_state=42,
                ),
            ),
        ]
    )
    model.fit(train[FEATURE_COLUMNS], train[TARGET_COLUMN].astype(int))
    metrics = _evaluate(model, test)

    metadata: dict[str, Any] = {
        "model_name": "olist_customer_churn",
        "model_version": model_version,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "model_type": "scikit-learn Pipeline with LogisticRegression",
        "target": TARGET_COLUMN,
        "decision_threshold": 0.5,
        "churn_definition": "No non-canceled order in the 90 days after a customer snapshot.",
        "lookback_days": LOOKBACK_DAYS,
        "label_horizon_days": LABEL_HORIZON_DAYS,
        "snapshot_step_days": 30,
        "feature_columns": FEATURE_COLUMNS,
        "review_sentiment_definition": "Mean normalized review score (score - 3) / 2, clipped to [-1, 1].",
        "training_examples": int(len(train)),
        "test_examples": int(len(test)),
        "churn_rate": float(examples[TARGET_COLUMN].mean()),
        "split_strategy": split_strategy,
        "train_snapshot_max": pd.Timestamp(train["snapshot_date"].max()).date().isoformat(),
        "test_snapshot_min": pd.Timestamp(test["snapshot_date"].min()).date().isoformat(),
        "order_date_min": pd.Timestamp(orders["order_date"].min()).date().isoformat(),
        "order_date_max": pd.Timestamp(orders["order_date"].max()).date().isoformat(),
        "metrics": metrics,
        "versions": {
            "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "scikit_learn": sklearn.__version__,
            "joblib": joblib.__version__,
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scipy": scipy.__version__,
        },
    }

    registry.mkdir(parents=True, exist_ok=True)
    temporary_dir = Path(tempfile.mkdtemp(prefix=f".{model_version}-", dir=registry))
    try:
        joblib.dump(model, temporary_dir / "model.joblib", compress=3)
        (temporary_dir / "metadata.json").write_text(
            json.dumps(metadata, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        temporary_dir.replace(version_dir)
        pointer_tmp = registry / ".current.json.tmp"
        pointer_tmp.write_text(json.dumps({"model_version": model_version}, indent=2), encoding="utf-8")
        pointer_tmp.replace(registry / "current.json")
    except Exception:
        if temporary_dir.exists():
            shutil.rmtree(temporary_dir)
        raise

    return {"model_dir": str(version_dir), **metadata}
