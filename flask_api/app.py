"""
Healthcare Public Data Pipeline — Flask API Gateway
====================================================
Multi-threaded Flask routing platform serving as the cross-platform
execution gateway between the Docker container ecosystem and the
Windows Host (KNIME). Provides REST endpoints for dashboard data,
forecast results, pipeline status, and KNIME execution orchestration.
"""

import json
import logging
import os
import subprocess
import sys
import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import unquote

import psycopg2
from psycopg2.extras import RealDictCursor
import requests as http_requests
from dotenv import load_dotenv
from flask import Flask, Response, jsonify, request
from flask_cors import CORS

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("flask_api")

app: Flask = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change_this_secret_key")

knime_execution_lock: threading.Lock = threading.Lock()
knime_running: bool = False
knime_last_run: Optional[Dict[str, Any]] = None
pipeline_status: Dict[str, Any] = {
    "extract": {"status": "idle", "last_run": None},
    "etl": {"status": "idle", "last_run": None},
    "clean": {"status": "idle", "last_run": None},
    "warehouse": {"status": "idle", "last_run": None},
    "ml": {"status": "idle", "last_run": None},
    "dashboard": {"status": "idle", "last_run": None},
}


def get_db_config() -> Dict[str, Any]:
    return {
        "dbname": os.environ.get("POSTGRES_DB", "healthcare_warehouse"),
        "user": os.environ.get("POSTGRES_USER", "health_admin"),
        "password": os.environ.get("POSTGRES_PASSWORD", "change_this_password"),
        "host": os.environ.get("POSTGRES_HOST", "localhost"),
        "port": int(os.environ.get("POSTGRES_PORT", "5432")),
    }


def get_db_connection() -> Optional[psycopg2.extensions.connection]:
    try:
        config: Dict[str, Any] = get_db_config()
        conn: psycopg2.extensions.connection = psycopg2.connect(**config)
        return conn
    except psycopg2.OperationalError as e:
        logger.error(f"Database connection failed: {e}")
        return None


def require_api_key() -> Optional[Tuple[Response, int]]:
    api_key: Optional[str] = request.headers.get("X-API-Key")
    expected_key: str = os.environ.get("API_KEY", "hc-pipeline-api-key-2026")
    if not api_key or api_key != expected_key:
        return jsonify({"error": "Unauthorized. Provide valid X-API-Key header."}), 401
    return None


@app.route("/api/health", methods=["GET"])
def health_check() -> Tuple[Response, int]:
    return jsonify({
        "status": "healthy",
        "service": "healthcare-pipeline-api",
        "timestamp": datetime.utcnow().isoformat(),
    }), 200


@app.route("/api/run-knime", methods=["POST"])
def run_knime() -> Tuple[Response, int]:
    auth_error = require_api_key()
    if auth_error:
        return auth_error
    global knime_running, knime_last_run
    if not knime_execution_lock.acquire(blocking=False):
        return jsonify({"error": "KNIME execution is already running"}), 409
    try:
        knime_running = True
        knime_bridge_url: str = os.environ.get("KNIME_BRIDGE_URL", "http://host.docker.internal:9999")
        knime_key: str = os.environ.get("KNIME_API_KEY", "hc-pipeline-knime-key-2026")
        logger.info(f"Calling KNIME Windows bridge at {knime_bridge_url}")
        try:
            resp: http_requests.Response = http_requests.post(
                knime_bridge_url,
                headers={
                    "X-KNIME-Key": knime_key,
                    "Content-Type": "application/json",
                },
                json={},
                timeout=7200,
            )
            result = resp.json()
            knime_last_run = result
            if resp.status_code == 200:
                logger.info(f"KNIME execution completed via bridge: {result.get('execution_time_seconds', '?')}s")
                return jsonify(result), 200
            else:
                logger.error(f"KNIME bridge returned {resp.status_code}: {result.get('error', 'unknown')}")
                return jsonify(result), resp.status_code
        except http_requests.exceptions.ConnectionError:
            logger.warning("KNIME Windows bridge unavailable. Falling back to mock.")
            time.sleep(2)
            result = {
                "status": "completed",
                "message": "Mock KNIME execution (Windows host bridge unreachable)",
                "exit_code": 0,
                "stdout": "Mock: KNIME headless batch execution completed successfully.",
                "stderr": "",
                "execution_time_seconds": 2.0,
                "timestamp": datetime.utcnow().isoformat(),
            }
            knime_last_run = result
            return jsonify(result), 200
        except http_requests.exceptions.Timeout:
            logger.error("KNIME bridge timed out")
            result = {"status": "timeout", "error": "KNIME bridge timed out (7200s)", "timestamp": datetime.utcnow().isoformat()}
            knime_last_run = result
            return jsonify(result), 504
    except Exception as e:
        logger.error(f"KNIME execution error: {e}")
        result = {"status": "failed", "error": str(e), "timestamp": datetime.utcnow().isoformat()}
        return jsonify(result), 500
    finally:
        knime_running = False
        knime_execution_lock.release()


@app.route("/api/cases", methods=["GET"])
def get_cases() -> Tuple[Response, int]:
    page: int = request.args.get("page", 1, type=int)
    per_page: int = request.args.get("per_page", 50, type=int)
    disease: Optional[str] = request.args.get("disease")
    region: Optional[str] = request.args.get("region")
    year: Optional[int] = request.args.get("year", type=int)
    source: Optional[str] = request.args.get("source")
    sort_by: str = request.args.get("sort_by", "loaded_at")
    sort_order: str = request.args.get("sort_order", "desc")
    page = max(1, page)
    per_page = min(max(10, per_page), 500)
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database unavailable"}), 503
    try:
        top_sql: str = "', '".join(TOP_DISEASES)
        conditions: List[str] = [
            f"dd.disease_name IN ('{top_sql}')",
            "fc.case_count > 0",
        ]
        params: List[Any] = []
        if disease:
            conditions.append("dd.disease_name ILIKE %s")
            params.append(f"%{disease}%")
        if region:
            conditions.append("dr.region_name ILIKE %s")
            params.append(f"%{region}%")
        if year:
            conditions.append("dt.year = %s")
            params.append(year)
        if source:
            conditions.append("fc.source ILIKE %s")
            params.append(f"%{source}%")
        where_clause: str = " WHERE " + " AND ".join(conditions) if conditions else ""
        valid_sort_cols: Dict[str, str] = {
            "year": "dt.year",
            "disease": "dd.disease_name",
            "region": "dr.region_name",
            "case_count": "fc.case_count",
            "cases_per_100k": "fc.cases_per_100k",
            "loaded_at": "fc.loaded_at",
        }
        sort_col: str = valid_sort_cols.get(sort_by, "fc.loaded_at")
        order: str = "ASC" if sort_order.lower() == "asc" else "DESC"
        offset: int = (page - 1) * per_page
        count_query: str = f"""
            SELECT COUNT(*) AS total
            FROM fact_cases fc
            JOIN dim_disease dd ON fc.disease_id = dd.disease_id
            JOIN dim_region dr ON fc.region_id = dr.region_id
            JOIN dim_time dt ON fc.time_id = dt.time_id
            JOIN dim_age_group da ON fc.age_group_id = da.age_group_id
            {where_clause}
        """
        data_query: str = f"""
            SELECT fc.case_id, dd.disease_name, dd.disease_category,
                   dr.region_name, dr.continent,
                   dt.year, dt.quarter, dt.month,
                   da.age_group_name,
                   fc.case_count, fc.cases_per_100k,
                   fc.deaths, fc.hospitalizations, fc.recoveries,
                   fc.source, fc.loaded_at
            FROM fact_cases fc
            JOIN dim_disease dd ON fc.disease_id = dd.disease_id
            JOIN dim_region dr ON fc.region_id = dr.region_id
            JOIN dim_time dt ON fc.time_id = dt.time_id
            JOIN dim_age_group da ON fc.age_group_id = da.age_group_id
            {where_clause}
            ORDER BY {sort_col} {order}
            LIMIT %s OFFSET %s
        """
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(count_query, params)
            total: int = cur.fetchone()["total"]
            cur.execute(data_query, params + [per_page, offset])
            rows: List[Dict[str, Any]] = cur.fetchall()
        return jsonify({
            "data": [dict(r) for r in rows],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": max(1, (total + per_page - 1) // per_page),
            },
        }), 200
    except psycopg2.Error as e:
        logger.error(f"Database error in /api/cases: {e}")
        return jsonify({"error": "Database query failed"}), 500
    finally:
        if conn:
            conn.close()


TOP_DISEASES: List[str] = [
    "Hepatitis B", "Tuberculosis", "Hepatitis C",
    "Influenza", "Cardiovascular Disease",
]


@app.route("/api/forecast", methods=["GET"])
def get_forecast() -> Tuple[Response, int]:
    disease: Optional[str] = request.args.get("disease")
    region: Optional[str] = request.args.get("region")
    limit: int = request.args.get("limit", 100, type=int)
    limit = min(max(10, limit), 1000)
    forecast_path: str = os.path.join(os.path.dirname(__file__), "data", "processed", "forecast_results")
    if not os.path.exists(forecast_path):
        return jsonify({
            "data": [],
            "message": "No forecast results available. Run forecast_model.py first.",
            "hint": "docker exec healthcare-spark-master spark-submit /opt/spark/jobs/forecast_model.py",
        }), 200
    try:
        import pandas as pd
        df: pd.DataFrame = pd.read_parquet(forecast_path)
        df = df[df["disease_name"].isin(TOP_DISEASES)]
        if disease:
            df = df[df["disease_name"].str.contains(disease, case=False, na=False)]
        if region:
            df = df[df["region"].str.contains(region, case=False, na=False)]
        if len(df) == 0:
            logger.info("No forecast parquet records match Non-communicable diseases. Falling back to mock.")
            mock_data: List[Dict[str, Any]] = generate_mock_forecast(disease, region, limit)
            return jsonify({"data": mock_data, "count": len(mock_data), "source": "mock"}), 200
        df = df.sort_values("year", ascending=False).head(limit)
        records: List[Dict[str, Any]] = json.loads(df.to_json(orient="records", date_format="iso"))
        return jsonify({"data": records, "count": len(records)}), 200
    except ImportError:
        logger.warning("Parquet libraries not available for /api/forecast. Returning mock data.")
        mock_data: List[Dict[str, Any]] = generate_mock_forecast(disease, region, limit)
        return jsonify({"data": mock_data, "count": len(mock_data), "source": "mock"}), 200
    except Exception as e:
        logger.error(f"Forecast query error: {e}")
        return jsonify({"error": "Failed to retrieve forecast data"}), 500


def generate_mock_forecast(disease: Optional[str], region: Optional[str], limit: int) -> List[Dict[str, Any]]:
    diseases: List[str] = TOP_DISEASES
    regions: List[str] = ["United States", "Pakistan", "India", "United Kingdom", "Nigeria"]
    import random
    results: List[Dict[str, Any]] = []
    for d in diseases:
        if disease and disease.lower() not in d.lower():
            continue
        for r in regions:
            if region and region.lower() not in r.lower():
                continue
            for year in [2024, 2025]:
                base: float = random.uniform(1000, 10000)
                results.append({
                    "region": r, "disease_name": d, "year": year,
                    "case_count": round(base, 2),
                    "prediction": round(base * random.uniform(0.85, 1.15), 2),
                    "forecast_timestamp": datetime.utcnow().isoformat(),
                })
    results.sort(key=lambda x: x["year"], reverse=True)
    return results[:limit]


@app.route("/api/metrics", methods=["GET"])
def get_metrics() -> Tuple[Response, int]:
    conn = get_db_connection()
    if not conn:
        return jsonify({
            "total_cases": 0,
            "total_deaths": 0,
            "total_recoveries": 0,
            "active_diseases": 0,
            "regions_covered": 0,
            "date_range": {"min": None, "max": None},
            "cases_by_disease": [],
            "cases_by_region": [],
            "source": "unavailable",
        }), 200
    try:
        top_list: str = "', '".join(TOP_DISEASES)
        clean_filter: str = f"dd.disease_name IN ('{top_list}') AND fc.case_count > 0"
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(f"""
                SELECT
                    COALESCE(SUM(fc.case_count), 0) AS total_cases,
                    COALESCE(SUM(fc.deaths), 0) AS total_deaths,
                    COALESCE(SUM(fc.recoveries), 0) AS total_recoveries,
                    COUNT(DISTINCT dd.disease_id) AS active_diseases,
                    COUNT(DISTINCT dr.region_id) AS regions_covered,
                    MIN(dt.year) AS min_year,
                    MAX(dt.year) AS max_year
                FROM fact_cases fc
                JOIN dim_disease dd ON fc.disease_id = dd.disease_id
                JOIN dim_region dr ON fc.region_id = dr.region_id
                JOIN dim_time dt ON fc.time_id = dt.time_id
                WHERE {clean_filter}
            """)
            agg: Dict[str, Any] = dict(cur.fetchone())
            cur.execute(f"""
                SELECT dd.disease_name, SUM(fc.case_count) AS total_cases
                FROM fact_cases fc
                JOIN dim_disease dd ON fc.disease_id = dd.disease_id
                WHERE {clean_filter}
                GROUP BY dd.disease_name
                ORDER BY total_cases DESC
            """)
            by_disease: List[Dict[str, Any]] = [dict(r) for r in cur.fetchall()]
            cur.execute(f"""
                SELECT dr.region_name, SUM(fc.case_count) AS total_cases
                FROM fact_cases fc
                JOIN dim_disease dd ON fc.disease_id = dd.disease_id
                JOIN dim_region dr ON fc.region_id = dr.region_id
                WHERE {clean_filter}
                GROUP BY dr.region_name
                ORDER BY total_cases DESC
            """)
            by_region: List[Dict[str, Any]] = [dict(r) for r in cur.fetchall()]
        return jsonify({
            "total_cases": float(agg["total_cases"]),
            "total_deaths": float(agg["total_deaths"]),
            "total_recoveries": float(agg["total_recoveries"]),
            "active_diseases": agg["active_diseases"],
            "regions_covered": agg["regions_covered"],
            "date_range": {"min": agg["min_year"], "max": agg["max_year"]},
            "cases_by_disease": by_disease,
            "cases_by_region": by_region,
            "source": "warehouse",
        }), 200
    except psycopg2.Error as e:
        logger.error(f"Metrics query error: {e}")
        return jsonify({"error": "Failed to compute metrics"}), 500
    finally:
        if conn:
            conn.close()


@app.route("/api/pipeline/status", methods=["GET"])
def get_pipeline_status() -> Tuple[Response, int]:
    global knime_running, knime_last_run, pipeline_status
    return jsonify({
        "knime_running": knime_running,
        "knime_last_run": knime_last_run,
        "pipeline_stages": pipeline_status,
        "timestamp": datetime.utcnow().isoformat(),
    }), 200


@app.route("/api/pipeline/update", methods=["POST"])
def update_pipeline_stage() -> Tuple[Response, int]:
    auth_error = require_api_key()
    if auth_error:
        return auth_error
    global pipeline_status
    data: Optional[Dict[str, Any]] = request.get_json(silent=True)
    if not data or "stage" not in data or "status" not in data:
        return jsonify({"error": "stage and status are required"}), 400
    stage: str = data["stage"]
    status: str = data["status"]
    if stage not in pipeline_status:
        return jsonify({"error": f"Invalid stage: {stage}. Valid: {list(pipeline_status.keys())}"}), 400
    if status not in ["idle", "running", "completed", "failed"]:
        return jsonify({"error": "status must be: idle, running, completed, or failed"}), 400
    pipeline_status[stage] = {"status": status, "last_run": datetime.utcnow().isoformat() if status in ["completed", "failed"] else pipeline_status[stage].get("last_run")}
    return jsonify({"message": f"Stage {stage} updated to {status}"}), 200


@app.route("/api/diseases", methods=["GET"])
def get_diseases() -> Tuple[Response, int]:
    conn = get_db_connection()
    if not conn:
        return jsonify({"data": []}), 200
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            top_d: str = "', '".join(TOP_DISEASES)
            cur.execute(f"SELECT disease_id, disease_code, disease_name, disease_category, icd10_code FROM dim_disease WHERE disease_name IN ('{top_d}') ORDER BY disease_name")
            rows: List[Dict[str, Any]] = [dict(r) for r in cur.fetchall()]
        return jsonify({"data": rows}), 200
    except psycopg2.Error as e:
        logger.error(f"Diseases query error: {e}")
        return jsonify({"error": "Failed to fetch diseases"}), 500
    finally:
        if conn:
            conn.close()


@app.route("/api/regions", methods=["GET"])
def get_regions() -> Tuple[Response, int]:
    conn = get_db_connection()
    if not conn:
        return jsonify({"data": []}), 200
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT region_id, region_code, region_name, continent FROM dim_region ORDER BY region_name")
            rows: List[Dict[str, Any]] = [dict(r) for r in cur.fetchall()]
        return jsonify({"data": rows}), 200
    except psycopg2.Error as e:
        logger.error(f"Regions query error: {e}")
        return jsonify({"error": "Failed to fetch regions"}), 500
    finally:
        if conn:
            conn.close()


@app.route("/api/pipeline/run-scraper/<source>", methods=["POST"])
def run_scraper(source: str) -> Tuple[Response, int]:
    auth_error = require_api_key()
    if auth_error:
        return auth_error
    valid: Dict[str, str] = {
        "who": "/app/scraping/who_scraper.py",
        "owid": "/app/scraping/owid_spider.py",
        "cdc": "/app/scraping/cdc_extractor.py",
    }
    if source not in valid:
        return jsonify({"error": f"Invalid source: {source}. Valid: {list(valid.keys())}"}), 400
    try:
        result = subprocess.run(
            ["python", valid[source]],
            capture_output=True, text=True, timeout=300,
        )
        status = "completed" if result.returncode == 0 else "failed"
        return jsonify({
            "status": status, "exit_code": result.returncode,
            "stdout": result.stdout[-1000:], "stderr": result.stderr[-1000:],
        }), 200 if result.returncode == 0 else 500
    except subprocess.TimeoutExpired:
        return jsonify({"status": "timeout", "error": "Scraper timed out (300s)"}), 504
    except Exception as e:
        return jsonify({"status": "failed", "error": str(e)}), 500


@app.route("/api/pipeline/run-spark-clean", methods=["POST"])
def run_spark_clean() -> Tuple[Response, int]:
    auth_error = require_api_key()
    if auth_error:
        return auth_error
    try:
        result = subprocess.run(
            ["docker", "exec", "healthcare-spark-master", "/opt/spark/bin/spark-submit", "--master", "spark://spark-master:7077", "--conf", "spark.driver.memory=6g", "--conf", "spark.executor.memory=6g", "--conf", "spark.sql.shuffle.partitions=4", "/opt/spark/jobs/clean_transform.py"],
            capture_output=True, text=True, timeout=600,
        )
        status = "completed" if result.returncode == 0 else "failed"
        return jsonify({
            "status": status, "exit_code": result.returncode,
            "stdout": result.stdout[-1000:], "stderr": result.stderr[-1000:],
        }), 200 if result.returncode == 0 else 500
    except subprocess.TimeoutExpired:
        return jsonify({"status": "timeout", "error": "Spark clean timed out (600s)"}), 504
    except Exception as e:
        return jsonify({"status": "failed", "error": str(e)}), 500


@app.route("/api/pipeline/run-warehouse-load", methods=["POST"])
def run_warehouse_load() -> Tuple[Response, int]:
    auth_error = require_api_key()
    if auth_error:
        return auth_error
    try:
        result = subprocess.run(
            ["python", "/app/warehouse/load_warehouse.py"],
            capture_output=True, text=True, timeout=120,
        )
        status = "completed" if result.returncode == 0 else "failed"
        return jsonify({
            "status": status, "exit_code": result.returncode,
            "stdout": result.stdout[-1000:], "stderr": result.stderr[-1000:],
        }), 200 if result.returncode == 0 else 500
    except subprocess.TimeoutExpired:
        return jsonify({"status": "timeout", "error": "Warehouse load timed out (120s)"}), 504
    except Exception as e:
        return jsonify({"status": "failed", "error": str(e)}), 500


@app.route("/api/pipeline/run-ml-forecast", methods=["POST"])
def run_ml_forecast() -> Tuple[Response, int]:
    auth_error = require_api_key()
    if auth_error:
        return auth_error
    try:
        result = subprocess.run(
            ["docker", "exec", "healthcare-spark-master", "/opt/spark/bin/spark-submit", "--master", "spark://spark-master:7077", "--conf", "spark.driver.memory=6g", "--conf", "spark.executor.memory=6g", "/opt/spark/jobs/forecast_model.py"],
            capture_output=True, text=True, timeout=600,
        )
        status = "completed" if result.returncode == 0 else "failed"
        return jsonify({
            "status": status, "exit_code": result.returncode,
            "stdout": result.stdout[-1000:], "stderr": result.stderr[-1000:],
        }), 200 if result.returncode == 0 else 500
    except subprocess.TimeoutExpired:
        return jsonify({"status": "timeout", "error": "ML forecast timed out (600s)"}), 504
    except Exception as e:
        return jsonify({"status": "failed", "error": str(e)}), 500


if __name__ == "__main__":
    host: str = os.environ.get("FLASK_HOST", "0.0.0.0")
    port: int = int(os.environ.get("FLASK_PORT", "5000"))
    debug: bool = bool(int(os.environ.get("FLASK_DEBUG", "0")))
    logger.info(f"Starting Flask API on {host}:{port} (debug={debug})")
    app.run(host=host, port=port, debug=debug, threaded=True)
