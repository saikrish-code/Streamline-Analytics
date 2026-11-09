# Customer churn API

The model uses `marts.fact_orders`, `marts.dim_date`, `marts.dim_customers`, and `marts.fact_reviews`. Order lines are rolled up to order grain before computing 180-day recency, distinct-order frequency, monetary value, and average order value. Review features are 180-day aggregates of normalized 1–5 review ratings: mean sentiment in `[-1, 1]`, negative-review share, mean score, and review count. The rating-based sentiment proxy is language-neutral for Olist's mostly Portuguese comments.

The target is `churned_next_90d`: for customers active during a 180-day feature window, churn is 1 when they place no non-canceled order in the next 90 days. Training creates 30-day-spaced snapshots and holds out the latest snapshots for evaluation when enough dates are available. The classifier is a median-imputed, scaled, class-weighted logistic-regression pipeline.

## Train and version the model

After raw quality validation and `dbt build` have produced the marts, install the API dependencies and train from the repository root:

```sh
python -m pip install -e ".[api,dbt]"
python -m api.churn.train --version 1.0.0
```

Artifacts are immutable under `api/model_registry/churn/vMAJOR.MINOR.PATCH/` and include `model.joblib` plus `metadata.json`. `current.json` selects the active version. A duplicate version is rejected; increment the version for every retrain. The metadata records the feature schema, training dates, split strategy, evaluation metrics, and Python/scikit-learn versions. The serving API refuses to load an artifact produced by a different scikit-learn version.

The training process reads `DATABASE_URL` or `POSTGRES_*` settings. Use `CHURN_MODEL_VERSION` to set a version without the CLI argument, and `CHURN_MODEL_REGISTRY` to choose another artifact directory.

## Run and deploy

Start locally with `uvicorn api.app:app --host 0.0.0.0 --port 8000` from the repository root. Build the API image with the repository root as the Docker context and `api/Dockerfile` as the Dockerfile path. Railway or Render can deploy this image and route traffic to the port supplied in `PORT`.

Package the versioned registry with the image, or mount a persistent volume and set `CHURN_MODEL_REGISTRY` to its path. `/health` reports whether a compatible model is loaded; `/predict` returns HTTP 503 until one is available. Restart/redeploy the API to activate a newly trained version.

### `GET /health`

Returns service status, model readiness, and the loaded model version.

### `POST /predict`

Example request:

```json
{
  "recency_days": 42,
  "frequency_180d": 3,
  "monetary_180d": 540.5,
  "average_order_value_180d": 180.17,
  "mean_review_sentiment_180d": 0.5,
  "negative_review_share_180d": 0.0,
  "mean_review_score_180d": 4.0,
  "review_count_180d": 2
}
```

The response includes the model version, churn probability, binary prediction at the recorded 0.5 threshold, and the threshold value.
