"""
Parquet-to-Staging Ingestor
============================
Reads Spark clean transform Parquet output and inserts into
staging_health_data table so the warehouse loader can process it.
"""

import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("parquet_ingest")

BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARQUET_DIR: str = os.path.join(BASE_DIR, "data", "processed", "staging_spark_clean")


def get_db_config() -> Dict[str, Any]:
    return {
        "dbname": os.environ.get("POSTGRES_DB", "healthcare_warehouse"),
        "user": os.environ.get("POSTGRES_USER", "health_admin"),
        "password": os.environ.get("POSTGRES_PASSWORD", "change_this_password"),
        "host": os.environ.get("POSTGRES_HOST", "postgres"),
        "port": int(os.environ.get("POSTGRES_PORT", "5432")),
    }


def read_parquet(path: str) -> Optional[pd.DataFrame]:
    if not os.path.exists(path):
        logger.error(f"Parquet directory not found: {path}")
        return None
    try:
        df: pd.DataFrame = pd.read_parquet(path)
        logger.info(f"Read {len(df)} rows from {path}")
        logger.info(f"Columns: {list(df.columns)}")
        return df
    except Exception as e:
        logger.error(f"Failed to read Parquet: {e}")
        return None


def transform_for_staging(df: pd.DataFrame) -> pd.DataFrame:
    needed: Dict[str, str] = {
        "disease_code": "disease_code",
        "disease_name": "disease_name",
        "region": "region_name",
        "year": "year",
        "disease_category": "disease_category",
        "case_count": "case_count",
        "cases_per_100k": "cases_per_100k",
        "source": "source",
    }
    result: pd.DataFrame = pd.DataFrame()
    for src_col, tgt_col in needed.items():
        if src_col in df.columns:
            result[tgt_col] = df[src_col]
        else:
            result[tgt_col] = None
    result["year"] = pd.to_numeric(result["year"], errors="coerce").fillna(0).astype(int)
    for col in ["case_count", "cases_per_100k"]:
        result[col] = pd.to_numeric(result[col], errors="coerce")
    result = result.fillna({c: None for c in result.columns})
    return result


def clear_staging(conn: psycopg2.extensions.connection) -> None:
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM staging_health_data")
        conn.commit()
        logger.info("Cleared existing staging_health_data table")
    except psycopg2.Error as e:
        logger.warning(f"Could not clear staging table: {e}")
        conn.rollback()


def bulk_insert(conn: psycopg2.extensions.connection, df: pd.DataFrame) -> int:
    rows: List[tuple] = [
        (
            row.get("disease_code"),
            row.get("disease_name"),
            row.get("region_name"),
            int(row["year"]) if pd.notna(row.get("year")) else None,
            row.get("disease_category"),
            float(row["case_count"]) if pd.notna(row.get("case_count")) else None,
            float(row["cases_per_100k"]) if pd.notna(row.get("cases_per_100k")) else None,
            row.get("source"),
        )
        for _, row in df.iterrows()
    ]
    query: str = """
        INSERT INTO staging_health_data
            (disease_code, disease_name, region_name, year, disease_category, case_count, cases_per_100k, source)
        VALUES %s
    """
    try:
        with conn.cursor() as cur:
            execute_values(cur, query, rows, page_size=1000)
        conn.commit()
        logger.info(f"Inserted {len(rows)} rows into staging_health_data")
        return len(rows)
    except psycopg2.Error as e:
        logger.error(f"Bulk insert failed: {e}")
        conn.rollback()
        return 0


def run() -> int:
    logger.info("=== Parquet-to-Staging Ingestor ===")
    df: Optional[pd.DataFrame] = read_parquet(PARQUET_DIR)
    if df is None or len(df) == 0:
        logger.error("No data to ingest")
        return 1

    staging_df: pd.DataFrame = transform_for_staging(df)
    logger.info(f"Transformed {len(staging_df)} rows for staging")

    config: Dict[str, Any] = get_db_config()
    conn: Optional[psycopg2.extensions.connection] = None
    try:
        conn = psycopg2.connect(**config)
        conn.autocommit = False
        clear_staging(conn)
        inserted: int = bulk_insert(conn, staging_df)
        if inserted == 0:
            logger.error("No rows inserted")
            return 1
        logger.info(f"Successfully ingested {inserted} rows")
        return 0
    except psycopg2.OperationalError as e:
        logger.error(f"Database connection failed: {e}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    sys.exit(run())
