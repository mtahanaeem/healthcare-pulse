# 💓 PulsePredict

> **Disease Surveillance & Forecast Dashboard** — React + Flask + Apache Spark + PostgreSQL + Docker Compose  
> **Course**: Tools & Techniques for Data Science — BS Data Science (6th Semester)  
> **University**: University of Central Punjab (UCP), Department of Data Science  
> **Semester**: Fall 2026

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://python.org)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=white)](https://react.dev)
[![Flask](https://img.shields.io/badge/Flask-3.0-000000?logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![Spark](https://img.shields.io/badge/Spark-3.4-E25A1C?logo=apachespark&logoColor=white)](https://spark.apache.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)](https://postgresql.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://docker.com)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-3-06B6D4?logo=tailwindcss&logoColor=white)](https://tailwindcss.com)
[![Recharts](https://img.shields.io/badge/Recharts-2-22B5BF?logo=recharts&logoColor=white)](https://recharts.org)

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Docker Compose Network                    │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │PostgreSQL │  │  Spark   │  │Flask API │  │   n8n    │   │
│  │  :5432    │  │:7077/8081│  │  :5000   │  │  :5678   │   │
│  │(Warehouse)│  │Master/Wrk│  │(Gateway) │  │(Workflow)│   │
│  └─────┬─────┘  └────┬─────┘  └────┬─────┘  └──────────┘   │
│        │             │             │                         │
└────────┼─────────────┼─────────────┼─────────────────────────┘
         │             │             │
         ▼             ▼             ▼
┌─────────────────────────────────────────────────────────────┐
│                     WINDOWS HOST ENGINE                      │
│                                                              │
│  ┌──────────────┐    ┌────────────────────────────┐         │
│  │ Native KNIME  │    │     Data Sources           │         │
│  │  knime.exe    │◄───│  - WHO GHO API             │         │
│  │  ETL Clean    │    │  - OWID Dataset            │         │
│  └──────────────┘    │  - CDC Open Data            │         │
│                      └────────────────────────────┘         │
└─────────────────────────────────────────────────────────────┘

                           ┌──────────────────┐
                           │   React Frontend   │
                           │   Vite + Tailwind  │
                           │   Nginx :80        │
                           │   Recharts+Lucide  │
                           └────────┬─────────┘
                                    │
                                    ▼
                           ┌──────────────────┐
                           │   Flask REST API   │
                           │     :5000          │
                           │  CORS + Threading  │
                           └──────────────────┘
```

### Pipeline Data Flow

```
WHO GHO ──┐
OWID ─────┤──► Scrapers ──► Raw CSVs ──► KNIME ETL ──► staging_health_data
CDC ──────┘                                                     │
                                                                 ▼
                                                       PySpark Clean & Transform
                                                                 │
                                                    ┌────────────┴────────────┐
                                                    ▼                        ▼
                                           dim_disease, dim_region    GBTRegressor
                                           dim_time, dim_age_group    Forecast Model
                                           fact_cases (Star Schema)         │
                                                                           ▼
                                                    ┌─────────────────── forecast_results
                                                    ▼
                                           Flask API Endpoints
                                           /api/metrics /api/cases
                                           /api/forecast /api/pipeline
                                                    │
                                                    ▼
                                           React Dashboard
                                           (5 disease views)
```

---

## 🛠️ Tech Stack

| Technology | Purpose |
|-----------|---------|
| **React 18 + Vite** | Frontend UI framework |
| **Flask 3.0 + Gunicorn** | REST API gateway |
| **PostgreSQL 16** | Star schema data warehouse |
| **Apache Spark 3.4** | Distributed data cleaning & ML |
| **PySpark MLlib GBTRegressor** | Disease case forecasting (R²=0.77) |
| **KNIME Analytics Platform** | ETL (Windows host, bridged via HTTP) |
| **n8n** | Pipeline workflow orchestration |
| **Docker Compose** | Multi-service container orchestration |
| **Tailwind CSS 3** | Dark-mode UI styling |
| **Recharts 2** | Interactive charts & heatmaps |
| **Lucide React** | UI iconography |
| **Nginx 1.25** | Static file serving + API proxy |

---

## 🚀 Quick Start

### Prerequisites

- Docker Desktop 4.20+ (WSL2 backend on Windows)
- Docker Compose v2.20+
- KNIME Analytics Platform 5.1+ (optional, for ETL on Windows host)

### Setup

```bash
# Clone repository
git clone https://github.com/mtahanaeem/healthcare-pulse.git
cd healthcare-pulse

# Set up environment (edit .env with your passwords)
cp .env.example .env

# Start everything
docker compose up --build -d

# Verify
docker compose ps
```

### Access

| Service | URL |
|---------|-----|
| **Dashboard** | http://localhost |
| **Flask API** | http://localhost:5000/api/health |
| **n8n** | http://localhost:5678 |

---

## 📊 Database

The warehouse uses a **star schema** with ~405 clean fact rows across **5 diseases** and **180 regions**.

**Dimensions:** `dim_disease`, `dim_region`, `dim_time`, `dim_age_group`  
**Fact table:** `fact_cases` (case_count, deaths, recoveries, hospitalizations, cases_per_100k)

**Top 5 Diseases:** Hepatitis B, Tuberculosis, Hepatitis C, Influenza, Cardiovascular Disease

### Key SQL Queries

```sql
-- Cases by disease
SELECT dd.disease_name, SUM(fc.case_count) AS total_cases
FROM fact_cases fc
JOIN dim_disease dd ON fc.disease_id = dd.disease_id
WHERE dd.disease_name IN ('Hepatitis B', 'Tuberculosis', 'Hepatitis C', 'Influenza', 'Cardiovascular Disease')
GROUP BY dd.disease_name ORDER BY total_cases DESC;

-- Cases by region (top 10)
SELECT dr.region_name, SUM(fc.case_count) AS total_cases
FROM fact_cases fc
JOIN dim_region dr ON fc.region_id = dr.region_id
GROUP BY dr.region_name ORDER BY total_cases DESC LIMIT 10;

-- Year-over-year trend
SELECT dd.disease_name, dt.year, SUM(fc.case_count) AS total_cases
FROM fact_cases fc
JOIN dim_disease dd ON fc.disease_id = dd.disease_id
JOIN dim_time dt ON fc.time_id = dt.time_id
GROUP BY dd.disease_name, dt.year ORDER BY dd.disease_name, dt.year;
```

---

## 🐳 Docker Services

| Service | Image | Ports | Purpose |
|---------|-------|-------|---------|
| `postgres` | postgres:16 | 5432 | Data warehouse |
| `flask-api` | Custom build | 5000 | REST API gateway |
| `react-frontend` | Custom build | 80 → 3000 | Dashboard UI |
| `spark-master` | bitnami/spark:3.4 | 8080, 7077 | Distributed processing |
| `spark-worker` | bitnami/spark:3.4 | 8081 | Spark worker node |
| `n8n` | n8nio/n8n | 5678 | Workflow orchestration |

---

## 📁 Project Structure

```
healthcare-pulse/
├── flask_api/
│   ├── app.py                 # Flask gateway (15 endpoints)
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx      # KPI grid + heatmaps
│   │   │   ├── Trends.jsx         # Historical + forecast charts
│   │   │   ├── RegionalMap.jsx    # Top-30 region breakdowns
│   │   │   ├── Explorer.jsx       # Multi-filter table
│   │   │   └── PipelineMonitor.jsx# n8n + KNIME gateway
│   │   ├── components/
│   │   │   ├── Sidebar.jsx, KPICard.jsx, TrendChart.jsx
│   │   │   ├── HeatmapChart.jsx, PieChartCard.jsx, DataTable.jsx
│   │   └── utils/
│   │       └── countryMapping.js  # ISO→Name + disease filters
│   ├── Dockerfile              # Multi-stage nginx build
│   └── nginx.conf              # API proxy config
├── spark/
│   ├── clean_transform.py      # PySpark dedup + imputation
│   └── forecast_model.py      # GBTRegressor with lag features
├── warehouse/
│   ├── schema.sql              # Star schema DDL
│   ├── load_warehouse.py       # psycopg2 upsert worker
│   └── ingest_parquet_to_staging.py
├── scraping/
│   ├── who_scraper.py          # WHO GHO API
│   ├── owid_spider.py          # OWID Scrapy spider
│   └── cdc_extractor.py        # CDC Open Data
├── knime_workflow/
│   └── health_cleaning.knwf    # KNIME ETL workflow
├── knime_bridge.py             # Windows host HTTP bridge
├── n8n_data/
│   └── Healthcare_Pipeline_Orchestrator.json
├── docker-compose.yaml
├── .gitignore
└── README.md
```

---

## 🔌 API Reference

### Health Check
```bash
curl http://localhost:5000/api/health
```
```json
{ "status": "healthy", "service": "healthcare-pipeline-api" }
```

### Metrics
```bash
curl http://localhost:5000/api/metrics
```
Returns total_cases, total_deaths, total_recoveries, cases_by_disease, cases_by_region, date_range, etc.

### Cases (Paginated)
```bash
curl "http://localhost:5000/api/cases?page=1&per_page=10&disease=Hepatitis&region=Pakistan&year=2024"
```

### Forecast
```bash
curl "http://localhost:5000/api/forecast?disease=Hepatitis%20B&limit=10"
```

### Pipeline Status
```bash
curl http://localhost:5000/api/pipeline/status
```

### Run KNIME ETL (Authenticated)
```bash
curl -X POST http://localhost:5000/api/run-knime \
  -H "X-API-Key: hc-pipeline-api-key-2026"
```

---

## 🔧 KNIME Host Integration

The Flask API communicates with KNIME running natively on Windows via `knime_bridge.py`:

- HTTP bridge listens on `host.docker.internal:9999`
- Threading lock prevents concurrent executions
- X-API-Key header authentication
- 7200s timeout, stdout/stderr truncated to 2000 chars
- Launch via double-clicking `run_knime_bridge.bat` on the Windows host

---

## 🧪 Spark ML Pipeline

- **Model:** Gradient Boosted Tree Regressor (GBTRegressor)
- **Features:** StandardScaler on 4 lag-based features
- **Performance:** R² = 0.77 on 382 training rows
- **Output:** 2024–2025 forecasts with confidence bounds
- **Fallback:** Mock generator when parquet has 0 matching rows

---

## 📱 Frontend Pages

| Route | Page | Description |
|-------|------|-------------|
| `/` | Dashboard | KPI grid, top-5 regions, disease distribution, case heatmap |
| `/trends` | Trends.jsx | Historical line charts + ML forecast toggle |
| `/regional` | RegionalMap.jsx | Top-30 region breakdowns |
| `/explorer` | Explorer.jsx | Multi-dimensional filter + paginated table |
| `/pipeline` | PipelineMonitor.jsx | Pipeline lifecycle + KNIME execution |

### Theme

- Background: `#0F172A` (slate-900), Cards: `#1E293B` (slate-800)
- Accent: `#0D7C66` (teal), Text: `#94A3B8` (slate-400)
- Headings: `#F1F5F9` (slate-100), Borders: `#334155` (slate-700)

---

## 🐳 Docker Compose Concepts

| Concept | Description |
|---------|-------------|
| **Service** | Each container defined in `docker-compose.yaml` |
| **Build** | Custom images built from Dockerfiles (flask-api, react-frontend) |
| **Ports** | Host-to-container port mappings |
| **Volumes** | Persistent storage (PostgreSQL, Spark data) |
| **depends_on** | Startup ordering between services |
| **Healthcheck** | PostgreSQL readiness probe |
| **Network** | `healthcare-net` bridge for inter-service DNS |

---

## 🔧 Troubleshooting

| Issue | Solution |
|-------|----------|
| Port conflict | Change host port in `docker-compose.yaml` |
| DB connection refused | Wait 30s for init, check `docker compose logs postgres` |
| Frontend can't reach API | Check nginx proxy_pass in `nginx.conf` |
| Spark job fails | `docker compose logs spark-master spark-worker` |
| KNIME bridge timeout | Verify `run_knime_bridge.bat` is running on Windows host |
| Container exits | `docker compose logs <service>` to diagnose |

---

## 👥 Team

| Member | GitHub | Role |
|--------|--------|------|
| **Muhammad Taha Naeem** | [@mtahanaeem](https://github.com/mtahanaeem) | Developer |
| **Abdur Rehman** | [@abdur-codes](https://github.com/abdur-codes) | Developer |
| **Adil Hayat Khan** | [@adilhayatkhan](https://github.com/adilhayatkhan) | Developer |

---

**University of Central Punjab, Lahore** — Tools & Techniques for Data Science — Fall 2026
