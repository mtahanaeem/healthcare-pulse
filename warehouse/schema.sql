-- =============================================================================
-- Healthcare Data Warehouse — Star Schema DDL
-- =============================================================================
-- Dimensions: dim_disease, dim_region, dim_time, dim_age_group
-- Fact:       fact_cases
-- =============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- DIMENSION: dim_disease
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_disease (
    disease_id      SERIAL PRIMARY KEY,
    disease_code    VARCHAR(50) NOT NULL UNIQUE,
    disease_name    VARCHAR(255) NOT NULL,
    disease_category VARCHAR(100),
    icd10_code      VARCHAR(20),
    is_communicable BOOLEAN DEFAULT FALSE,
    severity_level  VARCHAR(20) CHECK (severity_level IN ('low', 'medium', 'high', 'critical')),
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_dim_disease_code ON dim_disease(disease_code);
CREATE INDEX IF NOT EXISTS idx_dim_disease_category ON dim_disease(disease_category);

-- ---------------------------------------------------------------------------
-- DIMENSION: dim_region
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_region (
    region_id       SERIAL PRIMARY KEY,
    region_code     VARCHAR(10) NOT NULL UNIQUE,
    region_name     VARCHAR(100) NOT NULL,
    continent       VARCHAR(50),
    sub_region      VARCHAR(100),
    population_2023 BIGINT,
    who_region      VARCHAR(50),
    income_group    VARCHAR(30),
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_dim_region_code ON dim_region(region_code);
CREATE INDEX IF NOT EXISTS idx_dim_region_continent ON dim_region(continent);

-- ---------------------------------------------------------------------------
-- DIMENSION: dim_time
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_time (
    time_id         SERIAL PRIMARY KEY,
    year            INTEGER NOT NULL,
    quarter         INTEGER CHECK (quarter BETWEEN 1 AND 4),
    month           INTEGER CHECK (month BETWEEN 1 AND 12),
    month_name      VARCHAR(20),
    week            INTEGER CHECK (week BETWEEN 1 AND 53),
    day_of_year     INTEGER CHECK (day_of_year BETWEEN 1 AND 366),
    is_leap_year    BOOLEAN DEFAULT FALSE,
    UNIQUE(year, quarter, month, week)
);

CREATE INDEX IF NOT EXISTS idx_dim_time_year ON dim_time(year);

-- ---------------------------------------------------------------------------
-- DIMENSION: dim_age_group
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_age_group (
    age_group_id    SERIAL PRIMARY KEY,
    age_group_code  VARCHAR(20) NOT NULL UNIQUE,
    age_group_name  VARCHAR(50) NOT NULL,
    age_min         INTEGER CHECK (age_min >= 0),
    age_max         INTEGER CHECK (age_max >= age_min),
    demographic     VARCHAR(50),
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_dim_age_group_code ON dim_age_group(age_group_code);

-- ---------------------------------------------------------------------------
-- FACT TABLE: fact_cases
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fact_cases (
    case_id         BIGSERIAL PRIMARY KEY,
    disease_id      INTEGER NOT NULL REFERENCES dim_disease(disease_id),
    region_id       INTEGER NOT NULL REFERENCES dim_region(region_id),
    time_id         INTEGER NOT NULL REFERENCES dim_time(time_id),
    age_group_id    INTEGER NOT NULL REFERENCES dim_age_group(age_group_id),
    case_count      NUMERIC(20,4) NOT NULL DEFAULT 0,
    cases_per_100k  NUMERIC(20,4),
    deaths          NUMERIC(20,4) DEFAULT 0,
    hospitalizations NUMERIC(20,4) DEFAULT 0,
    recoveries      NUMERIC(20,4) DEFAULT 0,
    source          VARCHAR(50),
    confidence_low  NUMERIC(20,4),
    confidence_high NUMERIC(20,4),
    batch_id        VARCHAR(50),
    loaded_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(disease_id, region_id, time_id, age_group_id)
);

CREATE INDEX IF NOT EXISTS idx_fact_disease_id ON fact_cases(disease_id);
CREATE INDEX IF NOT EXISTS idx_fact_region_id ON fact_cases(region_id);
CREATE INDEX IF NOT EXISTS idx_fact_time_id ON fact_cases(time_id);
CREATE INDEX IF NOT EXISTS idx_fact_age_group_id ON fact_cases(age_group_id);
CREATE INDEX IF NOT EXISTS idx_fact_source ON fact_cases(source);
CREATE INDEX IF NOT EXISTS idx_fact_loaded_at ON fact_cases(loaded_at);

-- ---------------------------------------------------------------------------
-- STAGING TABLE (used by Pentaho ETL)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS staging_health_data (
    id              SERIAL PRIMARY KEY,
    disease_code    VARCHAR(50),
    disease_name    VARCHAR(255),
    region_name     VARCHAR(100),
    year            INTEGER,
    disease_category VARCHAR(100),
    case_count      NUMERIC(20,4),
    cases_per_100k  NUMERIC(20,4),
    source          VARCHAR(50),
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_staging_disease ON staging_health_data(disease_code);
CREATE INDEX IF NOT EXISTS idx_staging_region ON staging_health_data(region_name);

-- ---------------------------------------------------------------------------
-- SEED DATA: dim_disease (5 rows)
-- ---------------------------------------------------------------------------
INSERT INTO dim_disease (disease_code, disease_name, disease_category, icd10_code, is_communicable, severity_level) VALUES
    ('CVD_001', 'Cardiovascular Disease', 'Non-communicable', 'I00-I99', FALSE, 'high'),
    ('DIA_001', 'Diabetes Mellitus', 'Non-communicable', 'E10-E14', FALSE, 'medium'),
    ('INF_001', 'Influenza', 'Communicable', 'J09-J11', TRUE, 'medium'),
    ('RES_001', 'Lower Respiratory Infections', 'Communicable', 'J12-J18', TRUE, 'high'),
    ('NEO_001', 'Malignant Neoplasms', 'Non-communicable', 'C00-C97', FALSE, 'critical')
ON CONFLICT (disease_code) DO NOTHING;

-- ---------------------------------------------------------------------------
-- SEED DATA: dim_region (5 rows)
-- ---------------------------------------------------------------------------
INSERT INTO dim_region (region_code, region_name, continent, sub_region, population_2023, who_region, income_group) VALUES
    ('USA', 'United States of America', 'Americas', 'Northern America', 339996563, 'AMRO', 'High'),
    ('PAK', 'Pakistan', 'Asia', 'Southern Asia', 231402117, 'EMRO', 'Lower-middle'),
    ('IND', 'India', 'Asia', 'Southern Asia', 1428627663, 'SEARO', 'Lower-middle'),
    ('GBR', 'United Kingdom', 'Europe', 'Northern Europe', 67736802, 'EURO', 'High'),
    ('NGA', 'Nigeria', 'Africa', 'Western Africa', 223804632, 'AFRO', 'Lower-middle')
ON CONFLICT (region_code) DO NOTHING;

-- ---------------------------------------------------------------------------
-- SEED DATA: dim_time (5 rows)
-- ---------------------------------------------------------------------------
INSERT INTO dim_time (year, quarter, month, month_name, week, day_of_year, is_leap_year) VALUES
    (2020, 1, 1, 'January', 1, 1, TRUE),
    (2021, 2, 4, 'April', 14, 91, FALSE),
    (2022, 3, 7, 'July', 27, 182, FALSE),
    (2023, 4, 10, 'October', 40, 273, FALSE),
    (2024, 1, 1, 'January', 1, 1, TRUE)
ON CONFLICT (year, quarter, month, week) DO NOTHING;

-- ---------------------------------------------------------------------------
-- SEED DATA: dim_age_group (5 rows)
-- ---------------------------------------------------------------------------
INSERT INTO dim_age_group (age_group_code, age_group_name, age_min, age_max, demographic) VALUES
    ('AGE_00_14', 'Children (0-14)', 0, 14, 'Pediatric'),
    ('AGE_15_24', 'Youth (15-24)', 15, 24, 'Young Adult'),
    ('AGE_25_49', 'Adults (25-49)', 25, 49, 'Adult'),
    ('AGE_50_64', 'Older Adults (50-64)', 50, 64, 'Senior'),
    ('AGE_65_PLUS', 'Elderly (65+)', 65, 120, 'Geriatric')
ON CONFLICT (age_group_code) DO NOTHING;

-- ---------------------------------------------------------------------------
-- SEED DATA: fact_cases (30 mock rows)
-- ---------------------------------------------------------------------------
INSERT INTO fact_cases (disease_id, region_id, time_id, age_group_id, case_count, cases_per_100k, deaths, hospitalizations, recoveries, source) VALUES
    -- CVD in USA across age groups
    (1, 1, 1, 1, 1200.0000, 25.4000, 45.0000, 180.0000, 975.0000, 'WHO'),
    (1, 1, 2, 2, 890.0000, 18.2000, 32.0000, 145.0000, 713.0000, 'WHO'),
    (1, 1, 3, 3, 3400.0000, 72.1000, 210.0000, 890.0000, 2300.0000, 'WHO'),
    (1, 1, 4, 4, 5600.0000, 118.9000, 445.0000, 2100.0000, 3055.0000, 'WHO'),
    (1, 1, 5, 5, 8900.0000, 189.3000, 890.0000, 3400.0000, 4610.0000, 'WHO'),
    -- Diabetes in Pakistan across age groups
    (2, 2, 1, 1, 340.0000, 5.1000, 8.0000, 45.0000, 287.0000, 'WHO'),
    (2, 2, 2, 2, 567.0000, 8.4000, 12.0000, 78.0000, 477.0000, 'WHO'),
    (2, 2, 3, 3, 4500.0000, 67.8000, 156.0000, 890.0000, 3454.0000, 'WHO'),
    (2, 2, 4, 4, 3200.0000, 48.2000, 134.0000, 670.0000, 2396.0000, 'WHO'),
    (2, 2, 5, 5, 2100.0000, 31.6000, 98.0000, 456.0000, 1546.0000, 'WHO'),
    -- Influenza in India across age groups
    (3, 3, 1, 1, 8900.0000, 14.2000, 45.0000, 1200.0000, 7655.0000, 'OWID'),
    (3, 3, 2, 2, 6700.0000, 10.7000, 23.0000, 890.0000, 5787.0000, 'OWID'),
    (3, 3, 3, 3, 12000.0000, 19.1000, 67.0000, 2100.0000, 9833.0000, 'OWID'),
    (3, 3, 4, 4, 8900.0000, 14.2000, 89.0000, 1567.0000, 7244.0000, 'OWID'),
    (3, 3, 5, 5, 15600.0000, 24.8000, 234.0000, 3456.0000, 11910.0000, 'OWID'),
    -- Lower respiratory infections in UK
    (4, 4, 1, 1, 2300.0000, 45.6000, 12.0000, 340.0000, 1948.0000, 'CDC'),
    (4, 4, 2, 2, 1800.0000, 35.7000, 8.0000, 267.0000, 1525.0000, 'CDC'),
    (4, 4, 3, 3, 1200.0000, 23.8000, 15.0000, 189.0000, 996.0000, 'CDC'),
    (4, 4, 4, 4, 3400.0000, 67.4000, 89.0000, 678.0000, 2633.0000, 'CDC'),
    (4, 4, 5, 5, 6700.0000, 132.8000, 234.0000, 1456.0000, 5010.0000, 'CDC'),
    -- Malignant neoplasms in Nigeria
    (5, 5, 1, 1, 89.0000, 0.8000, 34.0000, 56.0000, 0.0000, 'WHO'),
    (5, 5, 2, 2, 156.0000, 1.4000, 67.0000, 89.0000, 0.0000, 'WHO'),
    (5, 5, 3, 3, 890.0000, 8.1000, 345.0000, 456.0000, 89.0000, 'WHO'),
    (5, 5, 4, 4, 1200.0000, 10.9000, 567.0000, 678.0000, 34.0000, 'WHO'),
    (5, 5, 5, 5, 890.0000, 8.1000, 456.0000, 567.0000, 12.0000, 'WHO'),
    -- Additional CVD data across regions and years
    (1, 2, 1, 3, 2100.0000, 18.5000, 78.0000, 345.0000, 1677.0000, 'WHO'),
    (1, 3, 2, 3, 8900.0000, 12.4000, 234.0000, 1234.0000, 7432.0000, 'WHO'),
    (2, 4, 3, 3, 1800.0000, 35.6000, 45.0000, 345.0000, 1410.0000, 'OWID'),
    (3, 5, 4, 3, 5600.0000, 50.8000, 23.0000, 678.0000, 4899.0000, 'CDC'),
    (4, 2, 5, 3, 3400.0000, 30.0000, 89.0000, 567.0000, 2744.0000, 'WHO')
ON CONFLICT (disease_id, region_id, time_id, age_group_id) DO UPDATE SET
    case_count = EXCLUDED.case_count,
    cases_per_100k = EXCLUDED.cases_per_100k,
    deaths = EXCLUDED.deaths,
    hospitalizations = EXCLUDED.hospitalizations,
    recoveries = EXCLUDED.recoveries,
    source = EXCLUDED.source;

COMMIT;
