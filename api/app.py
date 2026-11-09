"""FastAPI service for versioned customer churn predictions."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import pandas as pd
from fastapi import FastAPI, HTTPException, Request

from api.churn.features import FEATURE_COLUMNS
from api.churn.registry import ModelBundle, load_current_model
from api.schemas import ChurnFeatures, ChurnPrediction

logger = logging.getLogger("streamline_churn_api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        app.state.model_bundle = load_current_model()
        logger.info("Loaded churn model %s", app.state.model_bundle.metadata["model_version"])
    except Exception as exc:
        app.state.model_bundle = None
        logger.warning("Churn model is unavailable: %s", exc)
    yield


app = FastAPI(
    title="Streamline Analytics Churn API",
    version="1.0.0",
    description="Scores customer churn from 180-day RFM and review-rating sentiment features.",
    lifespan=lifespan,
)


@app.get("/health")
def health(request: Request) -> dict:
    bundle: ModelBundle | None = getattr(request.app.state, "model_bundle", None)
    return {
        "status": "ok" if bundle else "model_unavailable",
        "model_loaded": bundle is not None,
        "model_version": bundle.metadata["model_version"] if bundle else None,
    }


@app.post("/predict", response_model=ChurnPrediction)
def predict(features: ChurnFeatures, request: Request) -> ChurnPrediction:
    bundle: ModelBundle | None = getattr(request.app.state, "model_bundle", None)
    if bundle is None:
        raise HTTPException(status_code=503, detail="No compatible churn model is loaded")

    feature_row = pd.DataFrame([features.model_dump()], columns=FEATURE_COLUMNS)
    probability = float(bundle.model.predict_proba(feature_row)[0, list(bundle.model.classes_).index(1)])
    threshold = float(bundle.metadata.get("decision_threshold", 0.5))
    return ChurnPrediction(
        model_version=bundle.metadata["model_version"],
        churn_probability=probability,
        predicted_churn=probability >= threshold,
        decision_threshold=threshold,
    )
