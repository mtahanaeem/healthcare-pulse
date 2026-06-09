"""
Data Warehouse Loader
=====================
Standalone psycopg2 automated transaction worker that performs continuous
ON CONFLICT DO UPDATE upserts from staging_health_data into the star
schema dimensions and fact tables.

This script is designed to be run periodically (via cron, n8n, or manually)
to synchronize the warehouse with newly landed staging data.
"""

import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import psycopg2
from psycopg2 import sql
from psycopg2.extras import DictCursor, RealDictCursor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("warehouse_loader")

DB_CONFIG_KEYS: List[str] = [
    "POSTGRES_DB",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_HOST",
    "POSTGRES_PORT",
]


def get_db_config() -> Dict[str, Any]:
    config: Dict[str, Any] = {}
    for key in DB_CONFIG_KEYS:
        env_key: str = key
        env_value: Optional[str] = os.environ.get(env_key)
        if env_value is None:
            logger.warning(f"Environment variable {env_key} is not set. Using default.")
    config["dbname"] = os.environ.get("POSTGRES_DB", "healthcare_warehouse")
    config["user"] = os.environ.get("POSTGRES_USER", "health_admin")
    config["password"] = os.environ.get("POSTGRES_PASSWORD", "change_this_password")
    config["host"] = os.environ.get("POSTGRES_HOST", "localhost")
    config["port"] = int(os.environ.get("POSTGRES_PORT", "5432"))
    return config


def get_connection(config: Dict[str, Any]) -> psycopg2.extensions.connection:
    try:
        conn: psycopg2.extensions.connection = psycopg2.connect(**config)
        conn.autocommit = False
        logger.info(f"Connected to PostgreSQL at {config['host']}:{config['port']}/{config['dbname']}")
        return conn
    except psycopg2.OperationalError as e:
        logger.error(f"Failed to connect to PostgreSQL: {e}")
        raise


def fetch_staging_data(conn: psycopg2.extensions.connection) -> List[Dict[str, Any]]:
    query: str = """
        SELECT sd.id, sd.disease_code, sd.disease_name, sd.region_name,
               sd.year, sd.disease_category, sd.case_count, sd.cases_per_100k,
               sd.source, sd.created_at
        FROM staging_health_data sd
        WHERE NOT EXISTS (
            SELECT 1 FROM fact_cases fc
            JOIN dim_disease dd ON fc.disease_id = dd.disease_id
            JOIN dim_region dr ON fc.region_id = dr.region_id
            JOIN dim_time dt ON fc.time_id = dt.time_id
            WHERE dd.disease_code = sd.disease_code
              AND dr.region_name = sd.region_name
              AND dt.year = sd.year
        )
        ORDER BY sd.id
        LIMIT 1000
    """
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query)
            rows: List[Dict[str, Any]] = cur.fetchall()
            logger.info(f"Fetched {len(rows)} unprocessed staging rows")
            return rows
    except psycopg2.Error as e:
        logger.error(f"Failed to fetch staging data: {e}")
        conn.rollback()
        return []


def upsert_disease(conn: psycopg2.extensions.connection, disease_code: str, disease_name: str, disease_category: Optional[str]) -> int:
    query: str = """
        INSERT INTO dim_disease (disease_code, disease_name, disease_category, updated_at)
        VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
        ON CONFLICT (disease_code) DO UPDATE SET
            disease_name = EXCLUDED.disease_name,
            disease_category = COALESCE(EXCLUDED.disease_category, dim_disease.disease_category),
            updated_at = CURRENT_TIMESTAMP
        RETURNING disease_id
    """
    try:
        with conn.cursor() as cur:
            cur.execute(query, (disease_code, disease_name, disease_category))
            disease_id: int = cur.fetchone()[0]
            return disease_id
    except psycopg2.Error as e:
        logger.error(f"Failed to upsert disease {disease_code}: {e}")
        conn.rollback()
        raise


def upsert_region(conn: psycopg2.extensions.connection, region_name: str) -> int:
    import hashlib
    region_code: str = hashlib.md5(region_name.encode()).hexdigest()[:8].upper()
    query: str = """
        INSERT INTO dim_region (region_code, region_name)
        VALUES (%s, %s)
        ON CONFLICT (region_code) DO UPDATE SET
            region_name = EXCLUDED.region_name
        RETURNING region_id
    """
    try:
        with conn.cursor() as cur:
            cur.execute(query, (region_code, region_name))
            region_id: int = cur.fetchone()[0]
            return region_id
    except psycopg2.Error as e:
        logger.error(f"Failed to upsert region {region_name}: {e}")
        conn.rollback()
        raise


def upsert_time(conn: psycopg2.extensions.connection, year: int) -> int:
    query: str = """
        INSERT INTO dim_time (year, quarter, month, month_name, week, day_of_year, is_leap_year)
        VALUES (%s, 1, 1, 'January', 1, 1, (%s %% 4 = 0 AND (%s %% 100 != 0 OR %s %% 400 = 0)))
        ON CONFLICT (year, quarter, month, week) DO UPDATE SET
            is_leap_year = EXCLUDED.is_leap_year
        RETURNING time_id
    """
    try:
        with conn.cursor() as cur:
            cur.execute(query, (year, year, year, year))
            time_id: int = cur.fetchone()[0]
            return time_id
    except psycopg2.Error as e:
        logger.error(f"Failed to upsert time {year}: {e}")
        conn.rollback()
        raise


def get_default_age_group(conn: psycopg2.extensions.connection) -> int:
    query: str = "SELECT age_group_id FROM dim_age_group WHERE age_group_code = 'AGE_25_49' LIMIT 1"
    try:
        with conn.cursor() as cur:
            cur.execute(query)
            row = cur.fetchone()
            if row:
                return row[0]
    except psycopg2.Error as e:
        logger.error(f"Failed to fetch default age group: {e}")
    return 3


def upsert_fact(
    conn: psycopg2.extensions.connection,
    disease_id: int,
    region_id: int,
    time_id: int,
    age_group_id: int,
    case_count: float,
    cases_per_100k: Optional[float],
    source: str,
) -> None:
    query: str = """
        INSERT INTO fact_cases (disease_id, region_id, time_id, age_group_id, case_count, cases_per_100k, source)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (disease_id, region_id, time_id, age_group_id) DO UPDATE SET
            case_count = EXCLUDED.case_count,
            cases_per_100k = COALESCE(EXCLUDED.cases_per_100k, fact_cases.cases_per_100k),
            source = EXCLUDED.source,
            loaded_at = CURRENT_TIMESTAMP
    """
    try:
        with conn.cursor() as cur:
            cur.execute(query, (disease_id, region_id, time_id, age_group_id, case_count, cases_per_100k, source))
    except psycopg2.Error as e:
        logger.error(f"Failed to upsert fact: {e}")
        conn.rollback()
        raise


def process_staging_row(conn: psycopg2.extensions.connection, row: Dict[str, Any]) -> bool:
    try:
        disease_code: str = row.get("disease_code") or f"UNKNOWN_{row['id']}"
        disease_name: str = row.get("disease_name") or "Unknown Disease"
        disease_category: Optional[str] = row.get("disease_category")
        region_name: str = row.get("region_name") or "Unknown"
        year: int = int(row.get("year", datetime.utcnow().year))
        case_count: float = float(row.get("case_count") or 0)
        cases_per_100k: Optional[float] = float(row.get("cases_per_100k")) if row.get("cases_per_100k") else None
        source: str = row.get("source") or "UNKNOWN"

        disease_id: int = upsert_disease(conn, disease_code, disease_name, disease_category)
        region_id: int = upsert_region(conn, region_name)
        time_id: int = upsert_time(conn, year)
        age_group_id: int = get_default_age_group(conn)
        upsert_fact(conn, disease_id, region_id, time_id, age_group_id, case_count, cases_per_100k, source)
        return True
    except Exception as e:
        logger.error(f"Failed to process staging row {row.get('id')}: {e}")
        return False


def run() -> Dict[str, Any]:
    logger.info("=== Warehouse Loader Started ===")
    db_config: Dict[str, Any] = get_db_config()
    conn: Optional[psycopg2.extensions.connection] = None
    processed: int = 0
    errors: int = 0

    try:
        conn = get_connection(db_config)
        staging_rows: List[Dict[str, Any]] = fetch_staging_data(conn)
        if not staging_rows:
            logger.info("No unprocessed staging rows found. Nothing to load.")
            return {"status": "completed", "rows_processed": 0, "rows_errors": 0}

        for row in staging_rows:
            success: bool = process_staging_row(conn, row)
            if success:
                processed += 1
            else:
                errors += 1

        conn.commit()
        logger.info(f"Warehouse load completed: {processed} rows processed, {errors} errors")
        return {
            "status": "completed",
            "rows_processed": processed,
            "rows_errors": errors,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except psycopg2.Error as e:
        logger.error(f"PostgreSQL error during warehouse load: {e}")
        if conn:
            conn.rollback()
        return {"status": "failed", "error": str(e), "rows_processed": processed, "rows_errors": errors}

    except Exception as e:
        logger.error(f"Unexpected error during warehouse load: {e}")
        if conn:
            conn.rollback()
        return {"status": "failed", "error": str(e), "rows_processed": processed, "rows_errors": errors}

    finally:
        if conn:
            conn.close()
            logger.info("Database connection closed")


if __name__ == "__main__":
    result: Dict[str, Any] = run()
    print(json.dumps(result, indent=2))
    if result.get("status") == "failed":
        sys.exit(1)
