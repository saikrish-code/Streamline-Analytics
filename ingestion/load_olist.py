"""Bulk-load Olist CSV files into PostgreSQL's raw schema."""

from __future__ import annotations

import logging
import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

from ingestion.schema import CSV_FILES, RAW_SCHEMA, TABLES, metadata

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


def database_url() -> str | URL:
    """Return DATABASE_URL or construct one from individual Postgres settings."""
    explicit_url = os.getenv("DATABASE_URL")
    if explicit_url:
        return explicit_url
    return URL.create(
        "postgresql+psycopg2",
        username=os.getenv("POSTGRES_USER", "streamline"),
        password=os.getenv("POSTGRES_PASSWORD", "streamline_local"),
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        database=os.getenv("POSTGRES_DB", "streamline"),
    )


def load_table(engine, table_name: str, csv_path: Path, chunksize: int) -> int:
    """Replace one raw table with rows streamed from a CSV in bounded chunks."""
    table = TABLES[table_name]
    expected = [column.name for column in table.columns]
    header = pd.read_csv(csv_path, nrows=0, encoding="utf-8-sig").columns.tolist()
    if header != expected:
        raise ValueError(
            f"Unexpected columns in {csv_path.name}. Expected {expected}; found {header}. "
            "Check that this is the original Olist CSV version."
        )

    total = 0
    first_chunk = True
    for frame in pd.read_csv(csv_path, chunksize=chunksize, encoding="utf-8-sig", dtype=str):
        frame = frame.where(pd.notna(frame), None)
        frame.to_sql(
            table_name,
            con=engine,
            schema=RAW_SCHEMA,
            if_exists="replace" if first_chunk else "append",
            index=False,
            chunksize=chunksize,
            method="multi",
            dtype={column.name: column.type for column in table.columns},
        )
        first_chunk = False
        total += len(frame)

    if first_chunk:
        table.create(engine, checkfirst=True)
    return total


def main() -> None:
    load_dotenv()
    data_dir = Path(os.getenv("OLIST_DATA_DIR", "data/raw"))
    missing = [
        str(data_dir / filename)
        for filename in CSV_FILES.values()
        if not (data_dir / filename).is_file()
    ]
    if missing:
        raise FileNotFoundError(
            "Missing required Olist CSV files:\n  " + "\n  ".join(missing)
            + "\nDownload and extract the dataset into OLIST_DATA_DIR."
        )

    chunksize = int(os.getenv("LOAD_CHUNK_SIZE", "5000"))
    if chunksize < 1:
        raise ValueError("LOAD_CHUNK_SIZE must be a positive integer")

    engine = create_engine(database_url(), pool_pre_ping=True)
    try:
        with engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{RAW_SCHEMA}"'))
        metadata.create_all(engine)
        for table_name, filename in CSV_FILES.items():
            count = load_table(engine, table_name, data_dir / filename, chunksize)
            logger.info("Loaded %s rows into %s.%s", count, RAW_SCHEMA, table_name)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
