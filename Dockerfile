FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    DAGSTER_HOME=/data/dagster \
    DBT_PROFILES_DIR=/app/dbt_project \
    OLIST_DATA_DIR=/data/olist

WORKDIR /app
COPY . /app

RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -e ".[dbt,quality,orchestration]" \
    && cp dbt_project/profiles.yml.example dbt_project/profiles.yml \
    && mkdir -p /data/dagster /data/olist

EXPOSE 3000
CMD ["sh", "-c", "mkdir -p \"$DAGSTER_HOME\" && cp /app/orchestration/dagster.yaml \"$DAGSTER_HOME/dagster.yaml\" && dagster dev -h 0.0.0.0 -p \"${PORT:-3000}\" -m orchestration.definitions"]
