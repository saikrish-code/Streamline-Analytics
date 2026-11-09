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

## dbt transformations

The dbt project reads from `raw` and builds models into the `staging`, `intermediate`, and `marts` Postgres schemas. Install its adapter with `python -m pip install -e ".[dbt]"`. Copy `dbt_project/profiles.yml.example` to `dbt_project/profiles.yml`, then run from `dbt_project/`:

```sh
dbt debug --profiles-dir .
dbt build --profiles-dir .
```

The profile defaults match the local Compose credentials. For other credentials, define the `POSTGRES_*` environment variables in the shell running dbt; dbt does not automatically load the root `.env` file. The marts use an order-item grain for `fact_orders` so `dim_products`, `dim_customers`, and `dim_date` join cleanly without hiding multi-product orders. Item price and freight measures are additive; order totals are checked in the intermediate order model to avoid repeating an order-level amount on every item line. Schema tests cover key uniqueness, non-null keys, and dimension relationships. Singular tests check positive totals, positive order-line values, and legal streaming status transitions.

## Stream synthetic order events

Local Redpanda starts with Postgres through Compose. In one terminal, start the services and create the topic:

```sh
docker compose up -d
docker compose exec redpanda rpk topic create olist.order-events
```

Run the consumer in one terminal and the generator in another:

```sh
python -m ingestion.consume_order_events
python -m ingestion.generate_order_events
```

The generator emits `new_order` events and realistic transitions through `created`, `approved`, `shipped`, and terminal `delivered` or `canceled` statuses. Tune its pace with `PRODUCER_INTERVAL_SECONDS` and the chance of selecting an active order for a status update with `PRODUCER_STATUS_CHANGE_RATE`. The consumer writes the original event JSON, event fields, Kafka topic/partition/offset, and ingestion timestamp to `raw.streaming_events`. It commits Kafka offsets after the database transaction and uses event IDs to deduplicate replays.

## Hosted Kafka settings (Upstash)

Upstash Kafka was discontinued; Upstash announced it would stop accepting new Kafka users and new clusters. This connection path is therefore for an existing Upstash Kafka cluster only. See [Upstash's discontinuation announcement](https://upstash.com/blog/workflow-kafka).

For an existing cluster, create the topic in the Upstash console and copy the broker endpoint, username, and password from its connection details. Put these settings in `.env`:

```dotenv
KAFKA_BOOTSTRAP_SERVERS=<your-kafka-endpoint>:9092
KAFKA_TOPIC=olist.order-events
KAFKA_SECURITY_PROTOCOL=SASL_SSL
KAFKA_SASL_MECHANISM=SCRAM-SHA-256
KAFKA_USERNAME=<your-upstash-kafka-username>
KAFKA_PASSWORD=<your-upstash-kafka-password>
```

Both the producer and consumer use these settings. Keep credentials in `.env` and never commit that file. Upstash's Kafka protocol uses SASL authentication; the cluster console provides the actual endpoint and credentials. See [Upstash's Kafka connection example](https://upstash.com/blog/kafka-spark).
