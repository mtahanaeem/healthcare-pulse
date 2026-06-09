"""
CDC Open Data API Extractor
============================
Queries the CDC Open Data API (Socrata-based) with paginated while-loop
logic using $limit=1000 and $offset increments until all records are fetched.

Output: data/raw/cdc_data.csv
"""

import csv
import logging
import os
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("cdc_extractor")

BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_OUTPUT_DIR: str = os.path.join(BASE_DIR, "data", "raw")
CSV_OUTPUT_FILE: str = os.path.join(CSV_OUTPUT_DIR, "cdc_data.csv")

# PLACES ZCTA dataset contains 40+ health measures at ZIP code level
# Includes diabetes, obesity, cancer, heart disease, sleep, smoking, etc.
# Source: https://data.cdc.gov/500-Cities-Places/PLACES-ZCTA-Data-GIS-Friendly-Format-2025-release/kee5-23sr
CDC_DATASETS: List[Dict[str, str]] = [
    {
        "id": "kee5-23sr",
        "name": "places_health_measures",
        "description": "PLACES ZCTA Health Measures (diabetes, obesity, cancer, heart disease, etc.)",
    },
    {
        "id": "th8y-thx5",
        "name": "heart_disease_mortality",
        "description": "Heart Disease Mortality by County (2021-2023)",
    },
]

BASE_CDC_URL: str = os.environ.get("CDC_DATA_URL", "https://data.cdc.gov/resource")
PAGE_LIMIT: int = 1000
MAX_RETRIES: int = 3
REQUEST_DELAY: float = 0.5
TARGET_YEARS: List[int] = [2025, 2026]


def build_api_url(dataset_id: str) -> str:
    return f"{BASE_CDC_URL}/{dataset_id}.json"


def get_request_params(offset: int, limit: int = PAGE_LIMIT, app_token: str = "") -> Dict[str, Any]:
    params: Dict[str, Any] = {
        "$limit": limit,
        "$offset": offset,
        "$order": ":id",
    }
    if app_token:
        params["$$app_token"] = app_token
    return params


def fetch_page(url: str, params: Dict[str, Any], retries: int = MAX_RETRIES) -> Optional[List[Dict[str, Any]]]:
    for attempt in range(1, retries + 1):
        try:
            headers: Dict[str, str] = {
                "User-Agent": "HealthcarePipeline/1.0 (CDC Extractor; mailto:student@ucp.edu.pk)",
                "Accept": "application/json",
            }
            time.sleep(REQUEST_DELAY)
            response: requests.Response = requests.get(url, headers=headers, params=params, timeout=60)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                wait_time: float = 2.0 ** attempt
                logger.warning(f"Rate limited (429). Waiting {wait_time}s (attempt {attempt}/{retries})")
                time.sleep(wait_time)
            else:
                logger.error(f"HTTP {response.status_code} fetching page offset={params.get('$offset', 0)}")
                if response.status_code >= 500 and attempt < retries:
                    time.sleep(2.0 ** attempt)
                    continue
                return None
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error on attempt {attempt}: {e}")
            if attempt < retries:
                time.sleep(2.0 ** attempt)
        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout on attempt {attempt}: {e}")
            if attempt < retries:
                time.sleep(2.0 ** attempt)
        except requests.exceptions.RequestException as e:
            logger.error(f"Request exception on attempt {attempt}: {e}")
            return None
    return None


def extract_dataset(dataset_info: Dict[str, str], max_pages: int = 0) -> List[Dict[str, Any]]:
    dataset_id: str = dataset_info["id"]
    dataset_name: str = dataset_info["name"]
    url: str = build_api_url(dataset_id)
    all_records: List[Dict[str, Any]] = []
    offset: int = 0
    page_count: int = 0
    app_token: str = os.environ.get("CDC_APP_TOKEN", "")
    logger.info(f"Starting extraction for dataset: {dataset_name} (ID: {dataset_id})")
    while True:
        params: Dict[str, Any] = get_request_params(offset, app_token=app_token)
        page_data: Optional[List[Dict[str, Any]]] = fetch_page(url, params)
        if page_data is None:
            logger.error(f"Failed to fetch page at offset {offset} for {dataset_name}. Stopping.")
            break
        if not page_data:
            logger.info(f"No more records for {dataset_name}. Total: {len(all_records)}")
            break
        enriched: List[Dict[str, Any]] = []
        for record in page_data:
            record["_dataset_id"] = dataset_id
            record["_dataset_name"] = dataset_name
            record["_extracted_at"] = datetime.utcnow().isoformat()
            enriched.append(record)
        all_records.extend(enriched)
        page_count += 1
        offset += PAGE_LIMIT
        logger.info(f"Fetched {len(page_data)} records from {dataset_name} (total: {len(all_records)})")
        if len(page_data) < PAGE_LIMIT:
            logger.info(f"Reached end of dataset {dataset_name} at offset {offset}")
            break
        if max_pages > 0 and page_count >= max_pages:
            logger.info(f"Reached max_pages limit ({max_pages}) for {dataset_name}")
            break
    return all_records


def flatten_record(record: Dict[str, Any], prefix: str = "") -> Dict[str, str]:
    flat: Dict[str, str] = {}
    for key, value in record.items():
        flat_key: str = f"{prefix}{key}" if prefix else key
        if isinstance(value, dict):
            nested: Dict[str, str] = flatten_record(value, prefix=f"{flat_key}_")
            flat.update(nested)
        elif isinstance(value, list):
            flat[flat_key] = "; ".join(str(v) for v in value) if value else ""
        elif value is None:
            flat[flat_key] = ""
        else:
            flat[flat_key] = str(value)
    return flat


def save_records(all_records: List[Dict[str, Any]]) -> str:
    if not all_records:
        logger.warning("No CDC records to save")
        return ""
    os.makedirs(CSV_OUTPUT_DIR, exist_ok=True)
    flat_records: List[Dict[str, str]] = [flatten_record(r) for r in all_records]
    fieldnames: List[str] = list(flat_records[0].keys()) if flat_records else []
    try:
        with open(CSV_OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
            writer: csv.DictWriter = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(flat_records)
        logger.info(f"Saved {len(flat_records)} CDC records to {CSV_OUTPUT_FILE}")
    except IOError as e:
        logger.error(f"Failed to write CDC CSV: {e}")
        return ""
    return CSV_OUTPUT_FILE


def run(max_pages: int = 5) -> str:
    logger.info("=== CDC Data Extractor Started ===")
    all_records: List[Dict[str, Any]] = []
    for dataset in CDC_DATASETS:
        try:
            records: List[Dict[str, Any]] = extract_dataset(dataset, max_pages=max_pages)
            all_records.extend(records)
            logger.info(f"Dataset {dataset['name']}: {len(records)} records extracted")
        except Exception as e:
            logger.error(f"Failed to extract dataset {dataset['name']}: {e}")
            continue
    if all_records:
        year_filtered: List[Dict[str, Any]] = [
            r for r in all_records
            if r.get("year", "").isdigit() and int(r["year"]) in TARGET_YEARS
        ]
        if year_filtered:
            logger.info(f"Filtered to {len(year_filtered)} records for years {TARGET_YEARS} (from {len(all_records)})")
            all_records = year_filtered
        else:
            current_year: int = datetime.utcnow().year
            fallback = [r for r in all_records if r.get("year", "").isdigit() and int(r["year"]) >= current_year - 5]
            if fallback:
                logger.info(f"Falling back to last 5 years: {len(fallback)} records")
                all_records = fallback
    if not all_records:
        logger.warning("No records extracted from any CDC dataset")
    output_path: str = save_records(all_records)
    logger.info(f"=== CDC Data Extractor Completed — {len(all_records)} total records ===")
    return output_path


if __name__ == "__main__":
    result: str = run()
    if result:
        print(f"CDC extraction completed. Output: {result}")
    else:
        print("CDC extraction completed with no output.")
        sys.exit(1)
