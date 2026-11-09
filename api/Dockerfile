FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    CHURN_MODEL_REGISTRY=/app/api/model_registry/churn

WORKDIR /app
COPY pyproject.toml README.md ./
COPY api ./api
COPY ingestion ./ingestion

RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -e ".[api]"

EXPOSE 8000
CMD ["sh", "-c", "uvicorn api.app:app --host 0.0.0.0 --port \"${PORT:-8000}\""]
