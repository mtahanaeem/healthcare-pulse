"""
WHO GHO Data Scraper
====================
Extracts global health indicators from the World Health Organization's
Global Health Observatory (GHO) API using BeautifulSoup4 and requests.

Output: data/raw/who_data.csv
"""

import csv
import json
import logging
import os
import random
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("who_scraper")

ROTATING_USER_AGENTS: List[str] = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:119.0) Gecko/20100101 Firefox/119.0",
]

BASE_URL: str = os.environ.get("WHO_GHO_BASE_URL", "https://ghoapi.azureedge.net/api")
INDICATOR_CODES: List[str] = [
    "TB_notif_num",
    "MALARIA_PF_INDIG",
    "NCD_DIABETES_PREVALENCE_CRUDE",
    "HEPATITIS_HBV_INFECTIONS_NEW_NUM",
    "HEPATITIS_HCV_INFECTIONS_NEW_NUM",
]
MAX_RETRIES: int = 5
BASE_DELAY: float = 1.0
BACKOFF_MULTIPLIER: float = 2.0
CSV_OUTPUT_DIR: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "raw")
CSV_OUTPUT_FILE: str = os.path.join(CSV_OUTPUT_DIR, "who_data.csv")
TARGET_YEARS: List[int] = [2025, 2026]


def get_random_headers() -> Dict[str, str]:
    user_agent: str = random.choice(ROTATING_USER_AGENTS)
    return {
        "User-Agent": user_agent,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
    }


def fetch_with_retry(url: str, params: Optional[Dict[str, Any]] = None) -> Optional[requests.Response]:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            headers: Dict[str, str] = get_random_headers()
            delay: float = BASE_DELAY * (BACKOFF_MULTIPLIER ** (attempt - 1)) + random.uniform(0, 0.5)
            time.sleep(delay)
            response: requests.Response = requests.get(url, headers=headers, params=params, timeout=30)
            if response.status_code == 200:
                logger.info(f"Successfully fetched {url} on attempt {attempt}")
                return response
            elif response.status_code == 429:
                wait_time: float = delay * 2
                logger.warning(f"Rate limited (429) on attempt {attempt}. Waiting {wait_time:.2f}s")
                time.sleep(wait_time)
            elif response.status_code >= 500:
                logger.warning(f"Server error {response.status_code} on attempt {attempt}. Retrying...")
            else:
                logger.error(f"Unexpected status {response.status_code} for {url}")
                return response
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error on attempt {attempt}: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(delay)
        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout on attempt {attempt}: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(delay)
        except requests.exceptions.RequestException as e:
            logger.error(f"Request exception on attempt {attempt}: {e}")
            return None
    logger.error(f"Exhausted {MAX_RETRIES} retries for {url}")
    return None


def fetch_indicators() -> List[Dict[str, Any]]:
    all_indicators: List[Dict[str, Any]] = []
    url: str = f"{BASE_URL}/Indicator"
    response: Optional[requests.Response] = fetch_with_retry(url)
    if response is None:
        logger.error("Failed to fetch indicator list from WHO GHO API")
        return all_indicators
    try:
        data: Dict[str, Any] = response.json()
        all_indicators = data.get("value", [])
        logger.info(f"Retrieved {len(all_indicators)} indicators from WHO GHO")
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse WHO indicator response JSON: {e}")
    return all_indicators


def fetch_dimensions(indicator_code: str) -> Optional[List[Dict[str, Any]]]:
    url: str = f"{BASE_URL}/Dimension/{indicator_code}/DimensionValues"
    response: Optional[requests.Response] = fetch_with_retry(url)
    if response is None:
        logger.error(f"Failed to fetch dimensions for {indicator_code}")
        return None
    try:
        data: Dict[str, Any] = response.json()
        return data.get("value", [])
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse dimension JSON for {indicator_code}: {e}")
        return None


def fetch_indicator_data(indicator_code: str, top: int = 500, max_pages: int = 0) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    url: str = f"{BASE_URL}/{indicator_code}"
    skip: int = 0
    page_count: int = 0
    while True:
        params: Dict[str, Any] = {"$top": top, "$skip": skip}
        response: Optional[requests.Response] = fetch_with_retry(url, params=params)
        if response is None:
            break
        try:
            data: Dict[str, Any] = response.json()
            batch: List[Dict[str, Any]] = data.get("value", [])
            if not batch:
                break
            records.extend(batch)
            page_count += 1
            logger.info(f"Fetched {len(batch)} records for {indicator_code} (skip={skip})")
            if len(batch) < top:
                break
            if max_pages > 0 and page_count >= max_pages:
                break
            skip += top
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse indicator data JSON for {indicator_code}: {e}")
            break
    return records


def extract_relevant_fields(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    cleaned: List[Dict[str, Any]] = []
    for rec in records:
        try:
            cleaned.append({
                "indicator_code": rec.get("IndicatorCode", ""),
                "indicator_name": rec.get("IndicatorName", ""),
                "spatial_dim_type": rec.get("SpatialDimType", ""),
                "spatial_dim": rec.get("SpatialDim", ""),
                "time_dim_type": rec.get("TimeDimType", ""),
                "time_dim": rec.get("TimeDim", ""),
                "time_dim_value": rec.get("TimeDimValue", ""),
                "dim1_type": rec.get("Dim1Type", ""),
                "dim1": rec.get("Dim1", ""),
                "dim2_type": rec.get("Dim2Type", ""),
                "dim2": rec.get("Dim2", ""),
                "dim3_type": rec.get("Dim3Type", ""),
                "dim3": rec.get("Dim3", ""),
                "data_source": rec.get("DataSourceDimValueCode", ""),
                "value": rec.get("Value", ""),
                "numeric_value": rec.get("NumericValue", ""),
                "low": rec.get("Low", ""),
                "high": rec.get("High", ""),
                "comments": rec.get("Comments", ""),
                "date_added": rec.get("DateAdded", ""),
                "scraped_at": datetime.utcnow().isoformat(),
            })
        except (KeyError, TypeError, AttributeError) as e:
            logger.warning(f"Skipping malformed record: {e}")
            continue
    return cleaned


def save_to_csv(records: List[Dict[str, Any]]) -> str:
    if not records:
        logger.warning("No records to save to CSV")
        return ""
    os.makedirs(CSV_OUTPUT_DIR, exist_ok=True)
    fieldnames: List[str] = [
        "indicator_code", "indicator_name", "spatial_dim_type", "spatial_dim",
        "time_dim_type", "time_dim", "time_dim_value", "dim1_type", "dim1",
        "dim2_type", "dim2", "dim3_type", "dim3", "data_source", "value",
        "numeric_value", "low", "high", "comments", "date_added", "scraped_at",
    ]
    try:
        with open(CSV_OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
            writer: csv.DictWriter = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(records)
        logger.info(f"Saved {len(records)} records to {CSV_OUTPUT_FILE}")
    except IOError as e:
        logger.error(f"Failed to write CSV to {CSV_OUTPUT_FILE}: {e}")
        return ""
    return CSV_OUTPUT_FILE


def run(limit_per_indicator: int = 250, max_pages: int = 10) -> str:
    logger.info("=== WHO GHO Scraper Started ===")
    all_records: List[Dict[str, Any]] = []
    target_codes: List[str] = INDICATOR_CODES
    logger.info(f"Targeting {len(target_codes)} specific indicator codes (filtering for years {TARGET_YEARS})")
    for code in target_codes:
        logger.info(f"Fetching data for indicator: {code}")
        records: List[Dict[str, Any]] = fetch_indicator_data(code, top=limit_per_indicator, max_pages=max_pages)
        if records:
            cleaned: List[Dict[str, Any]] = extract_relevant_fields(records)
            recent: List[Dict[str, Any]] = []
            for r in cleaned:
                td = r.get("time_dim")
                if td is not None:
                    try:
                        year = int(float(td))
                        if year in TARGET_YEARS:
                            r["time_dim"] = str(year)
                            recent.append(r)
                    except (ValueError, TypeError):
                        pass
            all_records.extend(recent)
            logger.info(f"Indicator {code}: {len(recent)} recent records (filtered from {len(cleaned)})")
        time.sleep(random.uniform(0.5, 1.5))
    if not all_records:
        logger.warning(f"No records found for years {TARGET_YEARS}. Falling back to last 5 years.")
        for code in target_codes:
            logger.info(f"Fetching data for indicator: {code}")
            records = fetch_indicator_data(code, top=limit_per_indicator, max_pages=max_pages)
            if records:
                cleaned = extract_relevant_fields(records)
                current_year: int = datetime.utcnow().year
                recent = []
                for r in cleaned:
                    td = r.get("time_dim")
                    if td is not None:
                        try:
                            year = int(float(td))
                            if year >= current_year - 5:
                                r["time_dim"] = str(year)
                                recent.append(r)
                        except (ValueError, TypeError):
                            pass
                all_records.extend(recent)
            time.sleep(random.uniform(0.5, 1.5))
    output_path: str = save_to_csv(all_records)
    logger.info(f"=== WHO GHO Scraper Completed — {len(all_records)} total records ===")
    return output_path


if __name__ == "__main__":
    result: str = run()
    if result:
        print(f"Scraping completed successfully. Output: {result}")
    else:
        print("Scraping completed with no output.")
        sys.exit(1)
