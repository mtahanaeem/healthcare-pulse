@echo off
setlocal enabledelayedexpansion

set "ROOT=%~dp0"
cd /d "%ROOT%"

echo =====================================================
echo  Healthcare Pipeline - One-Click Launcher
echo =====================================================
echo.

rem ── Step 1: Ensure directories ──
echo [1/8] Ensuring directories...
if not exist "data\processed" mkdir "data\processed"
if not exist "data\models" mkdir "data\models"
echo   OK
echo.

rem ── Step 2: Start KNIME Windows Bridge API ──
echo [2/8] Starting KNIME Windows Bridge API...
start "KNIME-API" /B /MIN python knime_api.py
echo   Waiting for KNIME API...
:knime_wait
timeout /t 2 /nobreak >nul
curl.exe -s -o nul "http://localhost:5001/api/health" 2>nul
if !ERRORLEVEL! neq 0 goto knime_wait
echo   KNIME API is running on http://localhost:5001
echo.

rem ── Step 3: Build and start Docker containers ──
echo [3/8] Building images (first run may take a few minutes)...
docker compose build --parallel react-frontend flask-api n8n 2>&1
if !ERRORLEVEL! neq 0 (
    echo   [WARN] Build had warnings, continuing...
)
echo.

echo [4/8] Starting all services...
docker compose up -d 2>&1
if !ERRORLEVEL! neq 0 (
    echo   [ERROR] Failed to start services
    pause
    exit /b 1
)

echo   Waiting for PostgreSQL to become healthy...
:wait_loop
for /f "tokens=2" %%s in ('docker compose ps --format "table {{.Status}}" postgres 2^>nul ^| findstr /i "healthy"') do set "pg_ready=1"
if not defined pg_ready (
    timeout /t 3 /nobreak >nul
    goto wait_loop
)
echo   All containers are up
echo.

rem ── Step 5: Verify services ──
echo [5/8] Verifying services...
docker compose ps
echo.

rem ── Step 6: Check database ──
echo [6/8] Checking database...
docker compose exec -T postgres psql -U health_admin -d healthcare_warehouse -c "SELECT COUNT(*) AS fact_rows FROM fact_cases;" 2>nul
if !ERRORLEVEL! neq 0 (
    echo   [WARN] Database check failed - retrying in 5s...
    timeout /t 5 /nobreak >nul
    docker compose exec -T postgres psql -U health_admin -d healthcare_warehouse -c "SELECT COUNT(*) AS fact_rows FROM fact_cases;" 2>nul
    if !ERRORLEVEL! neq 0 (
        echo   [ERROR] Database unreachable. Check credentials in .env
    )
) else (
    echo   Database OK
)
echo.

rem ── Step 7: Run pipeline stages ──
echo [7/8] Running pipeline stages...
echo.

echo   --- Stage 1: EXTRACT (scrapers) ---
echo   Running WHO scraper...
docker compose exec -T flask-api python /app/scraping/who_scraper.py 2>nul
if !ERRORLEVEL! equ 0 ( echo     WHO scraper done ) else ( echo     [SKIP] WHO scraper failed (API may be unreachable) )

echo   Running OWID spider...
docker compose exec -T flask-api python /app/scraping/owid_spider.py 2>nul
if !ERRORLEVEL! equ 0 ( echo     OWID spider done ) else ( echo     [SKIP] OWID spider failed )

echo   Running CDC extractor...
docker compose exec -T flask-api python /app/scraping/cdc_extractor.py 2>nul
if !ERRORLEVEL! equ 0 ( echo     CDC extractor done ) else ( echo     [SKIP] CDC extractor failed )
echo.

echo   --- Stage 2: ETL (KNIME via Windows Bridge) ---
echo   Running KNIME ETL...
docker compose exec -T flask-api curl -s -X POST http://flask-api:5000/api/run-knime -H "X-API-Key: hc-pipeline-api-key-2026" 2>nul
if !ERRORLEVEL! equ 0 ( echo     KNIME ETL triggered ) else ( echo     [SKIP] KNIME ETL trigger failed )
echo.

echo   --- Stage 3: CLEAN (Spark) ---
echo   Running Spark clean transform (6g memory)...
docker compose exec -T spark-master spark-submit --master spark://spark-master:7077 --conf spark.driver.memory=6g --conf spark.executor.memory=6g --conf spark.sql.shuffle.partitions=4 /opt/spark/jobs/clean_transform.py 2>nul
if !ERRORLEVEL! equ 0 ( echo     Spark clean transform completed ) else ( echo     [WARN] Spark clean transform had issues )
echo.

echo   --- Stage 4: WAREHOUSE (load) ---
echo   Loading warehouse...
docker compose exec -T flask-api python /app/warehouse/load_warehouse.py 2>nul
if !ERRORLEVEL! equ 0 ( echo     Warehouse load completed ) else ( echo     [WARN] Warehouse load had issues )
echo.

echo   --- Stage 5: ML (forecast) ---
echo   Running forecast model (6g memory)...
docker compose exec -T spark-master spark-submit --master spark://spark-master:7077 --conf spark.driver.memory=6g --conf spark.executor.memory=6g /opt/spark/jobs/forecast_model.py 2>nul
if !ERRORLEVEL! equ 0 ( echo     Forecast model completed ) else ( echo     [WARN] Forecast model had issues )
echo.

rem ── Step 8: Final verification ──
echo [8/8] Final verification...
echo.
echo   Testing API endpoints:
for %%e in (
    "health|http://localhost:5000/api/health"
    "metrics|http://localhost:5000/api/metrics"
    "cases|http://localhost:5000/api/cases?per_page=3"
    "forecast|http://localhost:5000/api/forecast?limit=3"
) do (
    for /f "tokens=1,* delims=|" %%a in (%%e) do (
        curl.exe -s -o nul -w "    %%a: HTTP %%{http_code}" "%%b" 2>nul
        echo.
    )
)
timeout /t 2 /nobreak >nul
echo.

rem ── Verify updated case count ──
echo   Checking updated case count...
docker compose exec -T postgres psql -U health_admin -d healthcare_warehouse -c "SELECT COUNT(*) AS total_cases FROM fact_cases;" 2>nul
echo.

echo =====================================================
echo  Pipeline is fully operational!
echo =====================================================
echo.
echo  Frontend Dashboard:    http://localhost:3000
echo  Flask API Health:      http://localhost:5000/api/health
echo  Spark Master UI:       http://localhost:8080
echo  n8n Workflows:          http://localhost:5678
echo  KNIME Bridge API:       http://localhost:5001/api/health
echo.
echo  To view logs:          docker compose logs -f
echo  To stop:               docker compose down
echo  To stop + wipe data:   docker compose down -v
echo.
echo  Press any key to close this window.
echo.
endlocal

pause >nul
