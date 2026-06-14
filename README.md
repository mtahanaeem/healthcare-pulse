# 💓 Healthcare Pulse

**Disease Surveillance & Forecast Dashboard**

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://python.org)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=white)](https://react.dev)
[![Flask](https://img.shields.io/badge/Flask-3.0-000000?logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![Spark](https://img.shields.io/badge/Spark-3.4-E25A1C?logo=apachespark&logoColor=white)](https://spark.apache.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)](https://postgresql.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://docker.com)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-3-06B6D4?logo=tailwindcss&logoColor=white)](https://tailwindcss.com)
[![Recharts](https://img.shields.io/badge/Recharts-2-22B5BF?logo=recharts&logoColor=white)](https://recharts.org)

---

## 📋 Overview

A Dockerized, multi-service **disease surveillance dashboard** that ingests public health data (WHO, OWID, CDC), processes it via **Apache Spark**, and visualizes trends, forecasts, and regional breakdowns through an interactive **React** frontend — all orchestrated with **n8n** and containerized via **Docker Compose**.

Built for the **Tools & Techniques for Data Science** course at **University of Central Punjab (UCP)**, Assignment 4.

---

## ✨ Features

- **🔬 Multi-Source Data Ingestion** — WHO GHO API, OWID CSV, CDC Open Data scrapers
- **🧹 Automated ETL** — KNIME workflow on Windows host, bridged via HTTP to Docker
- **🧠 ML-Powered Forecasting** — PySpark GBTRegressor with lag features (R² = 0.77)
- **📊 Interactive Dashboard** — KPI cards, disease distribution, regional heatmaps, trend charts
- **🔮 Predictive Projections** — 2024–2025 case forecasts with confidence bounds
- **🌙 Dark Mode UI** — Full dark theme with Tailwind CSS (#0F172A scheme)
- **🔗 Pipeline Orchestration** — n8n automates the scrape → ETL → clean → warehouse → ML flow
- **🐳 Fully Containerized** — 6 Docker services managed via single `docker compose up`

---

## 🗂️ Project Structure

```
healthcare-pulse/
├── ⚙️ flask_api/
│   ├── app.py                    # Flask gateway (15 REST endpoints)
│   ├── requirements.txt
│   └── Dockerfile
│
├── 🎨 frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx     # KPI grid + disease/region heatmaps
│   │   │   ├── Trends.jsx        # Historical + forecast line charts
│   │   │   ├── RegionalMap.jsx   # Top-30 region breakdowns
│   │   │   ├── Explorer.jsx      # Multi-filter table with pagination
│   │   │   └── PipelineMonitor.jsx # n8n lifecycle + KNIME gateway
│   │   ├── components/
│   │   │   ├── Sidebar.jsx, KPICard.jsx, TrendChart.jsx
│   │   │   ├── HeatmapChart.jsx, PieChartCard.jsx, DataTable.jsx
│   │   └── utils/
│   │       └── countryMapping.js # ISO→Name mapping + disease filters
│   ├── Dockerfile                # Multi-stage nginx build
│   └── nginx.conf                # API reverse proxy
│
├── 🔥 spark/
│   ├── clean_transform.py        # PySpark dedup + imputation
│   └── forecast_model.py         # GBTRegressor with lag features
│
├── 🗄️ warehouse/
│   ├── schema.sql                # Star schema DDL
│   └── load_warehouse.py         # psycopg2 upsert worker
│
├── 🕷️ scraping/
│   ├── who_scraper.py            # WHO GHO API
│   ├── owid_spider.py            # OWID Scrapy spider
│   └── cdc_extractor.py          # CDC Open Data
│
├── 🔗 knime_bridge.py            # Windows host HTTP bridge
├── 🐳 docker-compose.yaml
└── 📖 README.md
```

---

## 🚀 Quick Start

### Prerequisites

- Docker Desktop 4.20+ (WSL2 backend on Windows)
- KNIME Analytics Platform 5.1+ (optional, for ETL on Windows host)

### Setup

```bash
git clone https://github.com/mtahanaeem/healthcare-pulse.git
cd healthcare-pulse

# Set up environment
cp .env.example .env
# Edit .env with your passwords

# Start all services
docker compose up --build -d

# Wait ~60s for initialization
```

### Access

| Service | URL |
|---------|-----|
| **Dashboard** | [http://localhost](http://localhost) |
| **Flask API** | [http://localhost:5000/api/health](http://localhost:5000/api/health) |
| **n8n** | [http://localhost:5678](http://localhost:5678) |

---

## 🐳 Docker Services

| Service | Image | Ports | Purpose |
|---------|-------|-------|---------|
| `postgres` | postgres:16 | 5432 | Star schema data warehouse |
| `flask-api` | Custom build | 5000 | REST API gateway (15 endpoints) |
| `react-frontend` | Custom build | 80 → 3000 | Dashboard UI (nginx-served) |
| `spark-master` | bitnami/spark:3.4 | 8080, 7077 | Distributed processing engine |
| `spark-worker` | bitnami/spark:3.4 | 8081 | Spark worker node |
| `n8n` | n8nio/n8n | 5678 | Pipeline workflow orchestration |

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 18, Vite 5, Tailwind CSS 3, Recharts 2, Lucide React |
| **Backend API** | Python 3.11, Flask 3.0, Gunicorn |
| **Database** | PostgreSQL 16 (star schema, 405 fact rows, 5 diseases, 180 regions) |
| **Distributed Processing** | Apache Spark 3.4 (Bitnami), PySpark MLlib |
| **ML Model** | GBTRegressor — 4 lag features, R² = 0.77 |
| **ETL** | KNIME Analytics Platform (Windows host, bridged via HTTP) |
| **Workflow Automation** | n8n — 6-stage pipeline orchestration |
| **Containerization** | Docker Compose, multi-stage builds, nginx reverse proxy |
| **Data Sources** | WHO GHO API, Our World in Data, CDC Open Data |

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Service health check |
| `GET` | `/api/metrics` | Aggregate KPIs (cases, deaths, recoveries by disease/region) |
| `GET` | `/api/cases` | Paginated case records with disease/region/year filters |
| `GET` | `/api/diseases` | Disease dimension listing |
| `GET` | `/api/forecast` | ML forecast with mock fallback (2024–2025) |
| `GET` | `/api/pipeline/status` | n8n pipeline stage states |
| `POST` | `/api/run-knime` | Trigger KNIME ETL execution (X-API-Key auth) |

---

## 🧠 How It Works

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

## 🔧 KNIME Host Integration

The Flask API communicates with KNIME running natively on Windows via `knime_bridge.py`:
- HTTP bridge listens on `host.docker.internal:9999`
- Threading lock prevents concurrent executions
- X-API-Key header authentication
- 7200s timeout with stdout/stderr truncation
- Launch via double-clicking `run_knime_bridge.bat` on the Windows host

---

## 📊 Database

The warehouse uses a **star schema** with **405 clean fact rows** across **5 diseases** and **180 regions**.

**Top 5 Diseases:** Hepatitis B, Tuberculosis, Hepatitis C, Influenza, Cardiovascular Disease

### Key Queries

```sql
-- Cases by disease
SELECT dd.disease_name, SUM(fc.case_count) AS total_cases
FROM fact_cases fc JOIN dim_disease dd ON fc.disease_id = dd.disease_id
WHERE dd.disease_name IN ('Hepatitis B', 'Tuberculosis', 'Hepatitis C', 'Influenza', 'Cardiovascular Disease')
GROUP BY dd.disease_name ORDER BY total_cases DESC;

-- Top 10 regions
SELECT dr.region_name, SUM(fc.case_count) AS total_cases
FROM fact_cases fc JOIN dim_region dr ON fc.region_id = dr.region_id
GROUP BY dr.region_name ORDER BY total_cases DESC LIMIT 10;

-- Year-over-year trend
SELECT dd.disease_name, dt.year, SUM(fc.case_count) AS total_cases
FROM fact_cases fc
JOIN dim_disease dd ON fc.disease_id = dd.disease_id
JOIN dim_time dt ON fc.time_id = dt.time_id
GROUP BY dd.disease_name, dt.year ORDER BY dd.disease_name, dt.year;
```

---

## 🔧 Troubleshooting

| Issue | Solution |
|-------|----------|
| Port already in use | Change host port in `docker-compose.yaml` |
| DB connection refused | Wait 30s, check `docker compose logs postgres` |
| Frontend can't reach API | Verify nginx proxy_pass in `nginx.conf` |
| Spark job fails | `docker compose logs spark-master spark-worker` |
| KNIME bridge timeout | Ensure `run_knime_bridge.bat` is running on Windows host |
| Container exits immediately | `docker compose logs <service>` to diagnose |

---

## 👥 Team

| Member | GitHub | Role |
|--------|--------|------|
| **Muhammad Taha Naeem** | [@mtahanaeem](https://github.com/mtahanaeem) | Developer |
| **Abdur Rehman** | [@abdur-codes](https://github.com/abdur-codes) | Developer |
| **Adil Hayat Khan** | [@adilhayatkhan](https://github.com/adilhayatkhan) | Developer |

---

## 🤝 Connect

[![GitHub](https://img.shields.io/badge/GitHub-mtahanaeem-181717?logo=github)](https://github.com/mtahanaeem)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-0A66C2?logo=linkedin)](https://linkedin.com/in/mtahanaeem)

**If you find this project useful, consider giving it a ⭐!**

---

**University of Central Punjab, Lahore** — Tools & Techniques for Data Science — Fall 2026
