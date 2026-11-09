# Streamline Analytics

A modular Python data pipeline starter built around the Olist Brazilian E-Commerce Public Dataset.

## Project layout

```text
ingestion/       Dataset download and Postgres raw-zone loading
dbt_project/     dbt transformation project scaffold
orchestration/   Workflow entry points and orchestration scaffold
quality/         Data quality checks scaffold
api/             API scaffold
dashboard/       Dashboard scaffold
data/raw/        Local source CSVs (ignored by Git)
```

## Get the data

The source dataset is published on [Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce). Download and unzip it into `data/raw/`, keeping the CSV filenames intact. Kaggle may require an account and API credentials. The loader checks for the six required files before loading. The public dataset also includes sellers, geolocation, and product category translation CSVs; this first raw model focuses on orders, customers, order items, payments, reviews, and products.

The six source CSVs are expected to use the Olist headers documented in `ingestion/schema.py`. Source data is not committed to this repository.

## Run locally

1. Copy `.env.example` to `.env` and adjust credentials if needed.
2. Start Postgres with `docker compose up -d`.
3. Create a virtual environment and install the project: `python -m pip install -e .`.
4. Download and extract the Olist CSVs to `data/raw/`.
5. Run `python -m ingestion.load_olist`.

The loader creates the `raw` schema and replaces the six raw tables on each run, making reruns deterministic. It loads rows in configurable chunks via SQLAlchemy/pandas. Raw columns are typed to retain practical source fidelity: identifiers and dates are text, numeric measures use numeric types, and reviews/labels remain text. No warehouse keys or relationships are imposed at this layer.
