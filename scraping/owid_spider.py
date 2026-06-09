"""
Our World In Data CSV Fetcher
===============================
Fetches health indicator CSVs directly from Our World In Data's grapher
export URLs. More reliable than scraping HTML pages.

Output: data/raw/owid_data.csv
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
logger = logging.getLogger("owid_fetcher")

BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_OUTPUT_DIR: str = os.path.join(BASE_DIR, "data", "raw")
CSV_OUTPUT_FILE: str = os.path.join(CSV_OUTPUT_DIR, "owid_data.csv")
COVID_CSV_URL: str = "https://raw.githubusercontent.com/owid/covid-19-data/master/public/data/owid-covid-data.csv"
COVID_OUTPUT_FILE: str = os.path.join(CSV_OUTPUT_DIR, "covid_data.csv")

# Working OWID grapher slugs (verified via https://ourworldindata.org/grapher/)
TARGET_DISEASES: List[Dict[str, str]] = [
    {"name": "cardiovascular_disease_death_rate", "slug": "deaths-from-cardiovascular-disease-ghe"},
    {"name": "diabetes_prevalence", "slug": "diabetes-prevalence"},
    {"name": "cancer_death_rate", "slug": "cancer-death-rates"},
    {"name": "hiv_death_rate", "slug": "hiv-death-rates"},
    {"name": "maternal_mortality", "slug": "maternal-mortality"},
    {"name": "child_mortality", "slug": "child-mortality"},
]

REQUEST_DELAY: float = 1.0
MAX_RETRIES: int = 3
TARGET_YEARS: List[int] = [2025, 2026]


def fetch_csv(slug: str) -> Optional[List[Dict[str, str]]]:
    url: str = f"https://ourworldindata.org/grapher/{slug}.csv?v=1&csvType=full&useColumnShortNames=false"
    logger.info(f"Fetching CSV from: {url}")
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            time.sleep(REQUEST_DELAY)
            resp: requests.Response = requests.get(
                url,
                headers={"User-Agent": "HealthcarePipeline/1.0 (student@ucp.edu.pk)"},
                timeout=30,
            )
            if resp.status_code == 200:
                lines: List[str] = resp.text.strip().split("\n")
                if len(lines) < 2:
                    logger.warning(f"No data rows in CSV for {slug}")
                    return None
                headers: List[str] = [h.strip().strip('"') for h in lines[0].split(",")]
                records: List[Dict[str, str]] = []
                for line in lines[1:]:
                    if not line.strip():
                        continue
                    parts: List[str] = _parse_csv_line(line)
                    row: Dict[str, str] = {}
                    for i, h in enumerate(headers):
                        row[h] = parts[i].strip() if i < len(parts) else ""
                    records.append(row)
                logger.info(f"Fetched {len(records)} rows for {slug}")
                return records
            elif resp.status_code == 404:
                logger.error(f"CSV not found (404) for slug: {slug}")
                return None
            else:
                logger.warning(f"HTTP {resp.status_code} for {slug} (attempt {attempt})")
                if attempt < MAX_RETRIES:
                    time.sleep(REQUEST_DELAY * 2)
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {slug} (attempt {attempt}): {e}")
            if attempt < MAX_RETRIES:
                time.sleep(REQUEST_DELAY * 2)
    return None


def fetch_covid_csv() -> Optional[List[Dict[str, Any]]]:
    logger.info(f"Fetching OWID COVID-19 CSV from: {COVID_CSV_URL}")
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            time.sleep(REQUEST_DELAY)
            resp: requests.Response = requests.get(
                COVID_CSV_URL,
                headers={"User-Agent": "HealthcarePipeline/1.0"},
                timeout=60,
            )
            if resp.status_code == 200:
                lines: List[str] = resp.text.strip().split("\n")
                if len(lines) < 2:
                    logger.warning("No data rows in COVID CSV")
                    return None
                headers: List[str] = [h.strip().strip('"') for h in lines[0].split(",")]
                records: List[Dict[str, Any]] = []
                seen: set = set()
                for line in lines[1:]:
                    if not line.strip():
                        continue
                    parts: List[str] = _parse_csv_line(line)
                    row: Dict[str, Any] = {}
                    for i, h in enumerate(headers):
                        row[h] = parts[i].strip().strip('"') if i < len(parts) else ""
                    location: str = row.get("location", "")
                    date_str: str = row.get("date", "")
                    new_cases: str = row.get("new_cases", "")
                    if not location or not date_str or not new_cases:
                        continue
                    year: int = int(date_str[:4])
                    if year < 2020 or year > 2026:
                        continue
                    dedup_key: str = f"{location}_{year}"
                    if dedup_key in seen:
                        continue
                    seen.add(dedup_key)
                    records.append({
                        "disease_code": "COVID_001",
                        "disease_name": "COVID-19",
                        "region": location,
                        "year": str(year),
                        "case_count": new_cases,
                        "source": "OWID",
                    })
                logger.info(f"Fetched {len(records)} COVID-19 records across {len(seen)} location-years")
                return records
            else:
                logger.warning(f"HTTP {resp.status_code} for COVID CSV (attempt {attempt})")
                if attempt < MAX_RETRIES:
                    time.sleep(REQUEST_DELAY * 2)
        except requests.exceptions.RequestException as e:
            logger.error(f"COVID CSV request failed (attempt {attempt}): {e}")
            if attempt < MAX_RETRIES:
                time.sleep(REQUEST_DELAY * 2)
    return None

def _parse_csv_line(line: str) -> List[str]:
    parts: List[str] = []
    current: List[str] = []
    in_quotes: bool = False
    for char in line:
        if char == '"':
            in_quotes = not in_quotes
        elif char == "," and not in_quotes:
            parts.append("".join(current))
            current = []
        else:
            current.append(char)
    parts.append("".join(current))
    return parts


def save_csv(filepath: str, records: List[Dict[str, Any]]) -> bool:
    if not records:
        return False
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    fieldnames: List[str] = list(records[0].keys())
    try:
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(records)
        logger.info(f"Saved {len(records)} records to {filepath}")
        return True
    except IOError as e:
        logger.error(f"Failed to write CSV {filepath}: {e}")
        return False

def run() -> str:
    logger.info("=== OWID CSV Fetcher Started ===")
    all_records: List[Dict[str, Any]] = []
    for disease in TARGET_DISEASES:
        rows: Optional[List[Dict[str, str]]] = fetch_csv(disease["slug"])
        if not rows:
            continue
        for row in rows:
            row["_disease_name"] = disease["name"]
            row["_scraped_at"] = datetime.utcnow().isoformat()
            all_records.append(row)
    if all_records and "Year" in all_records[0]:
        recent: List[Dict[str, Any]] = [r for r in all_records if r.get("Year", "").isdigit() and int(r["Year"]) in TARGET_YEARS]
        if recent:
            logger.info(f"Filtered to {len(recent)} records for years {TARGET_YEARS} (from {len(all_records)} total)")
            all_records = recent
        else:
            current_year: int = datetime.utcnow().year
            recent = [r for r in all_records if r.get("Year", "").isdigit() and int(r["Year"]) >= current_year - 5]
            if recent:
                logger.info(f"Falling back to last 5 years: {len(recent)} records")
                all_records = recent
    if not all_records:
        logger.warning("No records fetched from any OWID dataset")
    save_csv(CSV_OUTPUT_FILE, all_records)

    covid: Optional[List[Dict[str, Any]]] = fetch_covid_csv()
    if covid:
        save_csv(COVID_OUTPUT_FILE, covid)
        all_records.extend(covid)
        logger.info(f"COVID-19: {len(covid)} records added")
    else:
        logger.warning("No COVID-19 data fetched")

    logger.info(f"=== OWID CSV Fetcher Completed — {len(all_records)} total records ===")
    return CSV_OUTPUT_FILE


if __name__ == "__main__":
    result: str = run()
    if result:
        print(f"OWID fetch completed successfully. Output: {result}")
    else:
        print("OWID fetch completed with no output.")
        sys.exit(1)
