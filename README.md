# Streamline Analytics

An end-to-end Olist Brazilian E-Commerce analytics pipeline. It loads source CSVs to PostgreSQL, ingests live order events, validates raw data, transforms it with dbt, orchestrates batch and streaming work with Dagster, trains a versioned churn classifier, and serves an analytics dashboard.

## Architecture

```mermaid
flowchart LR
  Olist[Olist CSV dataset] --> Loader[Python / SQLAlchemy loader]
  Loader --> Raw[(Postgres raw schema)]
  Producer[Synthetic order-event producer] --> Kafka[Redpanda / Kafka]
  Kafka --> Consumer[Event consumer]
  Consumer --> Events[(raw.streaming_events)]
  Raw --> GE[Great Expectations raw gate]
  Events --> GE
  GE --> Stg[dbt staging]
  Stg --> Int[dbt intermediate]
  Int --> Marts[(dbt marts schema)]
  Dagster[Dagster schedules and assets] -. orchestrates .-> Loader
  Dagster -. orchestrates .-> GE
  Dagster -. orchestrates .-> Stg
  Marts --> Trainer[Weekly scikit-learn training]
  Trainer --> Registry[Versioned churn model]
  Registry --> ChurnAPI[FastAPI /predict]
  Marts --> ReadModels[(Dashboard materialized views)]
  ChurnAPI --> Next[Next.js dashboard]
  ReadModels --> Next
  Vercel[Vercel Cron] --> Refresh[/api/refresh/]
  Refresh --> ReadModels
  GH[GitHub Actions] --> CI[PR: GE, dbt and pytest]
  GH --> Trainer
```

### Components

| Path | Responsibility |
| --- | --- |
| `ingestion/` | Olist CSV loading, synthetic Kafka producer, and idempotent Postgres event consumer |
| `quality/` | Great Expectations raw-schema, null-rate, and event-freshness checkpoint |
| `dbt_project/` | Staging and intermediate cleaning plus dimensional marts (`fact_orders`, `fact_reviews`, and dimensions) |
| `orchestration/` | Dagster daily batch pipeline and five-minute streaming pipeline |
| `api/` | Churn feature engineering, scikit-learn training/model registry, and FastAPI prediction service |
| `dashboard/` | Next.js App Router UI, analytics API routes, indexed dashboard materialized views, and Vercel Cron |
| `.github/workflows/` | Pull-request data/quality CI, Python unit tests, weekly retrain and Render deployment |

## Local setup

### Requirements and configuration

- Python 3.10 or newer (the examples below use 3.11)
- Docker Desktop or Docker Engine with Compose
- Node.js 20 or newer for the dashboard
- A Kaggle account to obtain the public [Olist Brazilian E-Commerce dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)

From the repository root, copy `.env.example` to `.env` and adjust values as needed. The defaults match the local Postgres and Redpanda Compose services. Create a Python environment and install the base project plus the dbt, quality, orchestration, and churn dependencies:

```sh
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[api,dbt,quality,orchestration]"
```

Start Postgres and Redpanda:

```sh
docker compose up -d
docker compose ps
docker compose exec redpanda rpk topic create olist.order-events
```

Download and extract the six Olist CSV files (customers, orders, order items, payments, reviews, products) into `data/raw/`. The loader checks the source headers and creates `raw` tables from the declared schema.

```sh
python -m ingestion.load_olist
```

### Stream events and validate raw data

Open two terminal sessions with the project virtual environment activated. Start the Postgres consumer in one and the live event generator in the other:

```sh
python -m ingestion.consume_order_events
```

```sh
python -m ingestion.generate_order_events
```

Let events arrive, then run the raw Great Expectations checkpoint in another terminal. It checks all six source tables plus `raw.streaming_events`, including that the latest event meets `STREAMING_FRESHNESS_MINUTES` (30 minutes by default).

```sh
python -m quality.validate_raw
```

The event generator emits `new_order` and realistic status transitions. Stop either long-running process with Ctrl+C.

### Build and test dbt marts

Copy `dbt_project/profiles.yml.example` to `dbt_project/profiles.yml`. The profile reads local connection settings from `POSTGRES_*` environment variables; these are also in `.env`, which dbt itself does not load automatically. In a shell where those values are available:

```sh
dbt debug --project-dir dbt_project --profiles-dir dbt_project
dbt build --project-dir dbt_project --profiles-dir dbt_project
```

`dbt build` runs the staging, intermediate, and marts models and their schema and singular tests. The `fact_orders` grain is one row per order item, so aggregate its additive item measures when calculating order-level totals.

### Train and serve churn predictions

The training command needs enough order history in the marts to create customer snapshots and forward 90-day churn labels. It saves a semantic-versioned artifact under `api/model_registry/churn/`:

```sh
python -m api.churn.train --version 1.0.0
uvicorn api.app:app --host 0.0.0.0 --port 8000
```

Check `http://localhost:8000/health`; send the documented RFM/review feature object to `POST /predict`. See [api/README.md](api/README.md) for the feature definition and version details. An Olist CSV snapshot is historical, so model training needs full forward-label history and may reject a dataset that has too little date coverage.

### Run the dashboard

Copy `dashboard/.env.example` to `dashboard/.env.local`. Set `DATABASE_URL` to the same Postgres database and `CHURN_API_URL` to `http://localhost:8000`. After `dbt build`, apply the dashboard read-model SQL once:

```sh
cd dashboard
npm install
# Create dashboard/.env.local from .env.example and set its values.
# Set DATABASE_URL in this shell (PowerShell: $env:DATABASE_URL = "postgresql://...").
export DATABASE_URL="postgresql://user:password@host:5432/streamline"
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f sql/dashboard_views.sql
npm run dev
```

Open `http://localhost:3000`. The dashboard reads the `marts` schema server-side and displays model scores when the churn API is healthy. The `/api/refresh` route refreshes the dashboard materialized views. [dashboard/README.md](dashboard/README.md) documents Vercel deployment and cron configuration.

### Run Dagster locally

With the Python environment activated and Postgres/Kafka settings configured:

```sh
dagster dev -h 0.0.0.0 -p 3000 -m orchestration.definitions
```

The enabled schedules run the raw-validation/dbt batch pipeline daily and a bounded streaming pipeline every five minutes. Details and persistent-service deployment notes are in [orchestration/README.md](orchestration/README.md).

## Automated checks and model deployment

- `.github/workflows/ci.yml` runs on pull requests that touch `dbt_project/` or `quality/`. It starts Postgres, seeds a small CI-only fixture, runs Great Expectations, and only then runs `dbt build` (including dbt tests).
- `.github/workflows/python-tests.yml` runs API and ingestion unit tests on relevant pull requests.
- `.github/workflows/weekly-churn-model.yml` runs Mondays at 05:00 UTC (and supports manual dispatch). Configure repository secrets `CHURN_TRAINING_DATABASE_URL` (a Postgres URL whose database has up-to-date marts), `RAILWAY_TOKEN`, `RAILWAY_PROJECT_ID`, `RAILWAY_ENVIRONMENT_ID`, and `RAILWAY_API_SERVICE_ID`. It trains a new semantic version and deploys the repository—including that model artifact—to the targeted Railway API service.

For weekly API deploys, configure the Railway service to use `RAILWAY_DOCKERFILE_PATH=api/Dockerfile`. Create a Railway project token scoped to the production environment and add the token plus project, environment, and API service IDs as GitHub Actions secrets. Railway's CLI supports non-interactive CI deploys with project tokens and explicit service/environment targets ([Railway CLI deploy docs](https://docs.railway.com/cli/deploying)).

## Hosted Kafka

Local development uses Redpanda through Compose. The earlier Upstash Kafka hosted option has been discontinued for new users; connection details for a previously provisioned compatible Kafka broker can be supplied through `KAFKA_BOOTSTRAP_SERVERS`, `KAFKA_SECURITY_PROTOCOL`, `KAFKA_SASL_MECHANISM`, `KAFKA_USERNAME`, and `KAFKA_PASSWORD`. Keep broker credentials in `.env` or service secrets, never in source control.
