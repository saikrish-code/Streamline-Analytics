"""Bulk-load Olist CSV files into PostgreSQL's raw schema (SQLAlchemy-free fallback)."""

import logging
import os
from pathlib import Path
from urllib.parse import quote_plus
import pandas as pd
import psycopg2
from dotenv import load_dotenv
from ingestion.schema import CSV_FILES, RAW_SCHEMA

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

def database_url() -> str:
    """Return the SQLAlchemy URL for the configured Postgres database."""
    load_dotenv()
    host = os.getenv("POSTGRES_HOST", "localhost")
    explicit = os.getenv("DATABASE_URL")
    # POSTGRES_* wins when set so containers can override the host-oriented .env URL.
    if explicit and not os.getenv("POSTGRES_HOST"):
        return explicit.replace("postgresql://", "postgresql+psycopg2://", 1) if explicit.startswith("postgresql://") else explicit
    user = quote_plus(os.getenv("POSTGRES_USER", "streamline"))
    password = quote_plus(os.getenv("POSTGRES_PASSWORD", "streamline_local"))
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "streamline")
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"


def load_with_fallback():
    """Load CSV files using pandas and direct psycopg2 inserts to bypass blocked SQLAlchemy."""
    data_dir = Path(os.getenv("OLIST_DATA_DIR", "data/raw"))
    chunksize = int(os.getenv("LOAD_CHUNK_SIZE", "5000"))

    logger.info(f"Connecting to Postgres at {os.getenv('POSTGRES_HOST', 'localhost')}")
    conn = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        user=os.getenv("POSTGRES_USER", "streamline"),
        password=os.getenv("POSTGRES_PASSWORD", "streamline_local"),
        dbname=os.getenv("POSTGRES_DB", "streamline")
    )
    conn.autocommit = True

    try:
        with conn.cursor() as cur:
            cur.execute(f'CREATE SCHEMA IF NOT EXISTS "{RAW_SCHEMA}"')

        only = {t.strip() for t in os.getenv("OLIST_TABLES", "").split(",") if t.strip()}
        for table_name, filename in CSV_FILES.items():
            if only and table_name not in only:
                continue
            csv_path = data_dir / filename
            if not csv_path.is_file():
                logger.warning(f"File not found, skipping: {csv_path}")
                continue

            logger.info(f"Loading {table_name} from {filename}...")

            # Read header to get column names
            df_header = pd.read_csv(csv_path, nrows=0, encoding="utf-8-sig")
            # The public Olist CSV misspells these two product columns.
            renames = {"product_name_lenght": "product_name_length", "product_description_lenght": "product_description_length"}
            cols = [f'"{renames.get(c, c)}"' for c in df_header.columns]

            with conn.cursor() as cur:
                cur.execute(f'DROP TABLE IF EXISTS "{RAW_SCHEMA}"."{table_name}" CASCADE')
                col_defs = ", ".join([f'{c} TEXT' for c in cols])
                cur.execute(f'CREATE TABLE "{RAW_SCHEMA}"."{table_name}" ({col_defs})')

            total_rows = 0
            for chunk in pd.read_csv(csv_path, chunksize=chunksize, encoding="utf-8-sig", dtype=str):
                chunk = chunk.astype(object).where(pd.notna(chunk), None)
                placeholders = ", ".join(["%s"] * len(cols))
                sql = f'INSERT INTO "{RAW_SCHEMA}"."{table_name}" ({", ".join(cols)}) VALUES ({placeholders})'

                with conn.cursor() as cur:
                    cur.executemany(sql, chunk.values.tolist())

                total_rows += len(chunk)

            logger.info(f"Successfully loaded {total_rows} rows into {RAW_SCHEMA}.{table_name}")

    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        raise
    finally:
        conn.close()

def main():
    load_dotenv()
    load_with_fallback()

if __name__ == "__main__":
    main()
