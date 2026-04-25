#!/bin/bash
# ============================================
# Initialize the massmutual application database
# Runs after 01_create_db.sql via docker-entrypoint-initdb.d
# ============================================

set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "massmutual" <<-EOSQL

    -- ========================
    -- DIMENSION TABLES
    -- ========================

    CREATE TABLE IF NOT EXISTS dim_date (
        date_key    INT PRIMARY KEY,
        date        DATE NOT NULL UNIQUE,
        day         INT NOT NULL,
        month       INT NOT NULL,
        month_name  VARCHAR(20) NOT NULL,
        quarter     INT NOT NULL,
        year        INT NOT NULL,
        weekday     VARCHAR(20) NOT NULL
    );

    CREATE INDEX IF NOT EXISTS idx_dim_date_year ON dim_date(year);
    CREATE INDEX IF NOT EXISTS idx_dim_date_month ON dim_date(year, month);

    CREATE TABLE IF NOT EXISTS dim_stock (
        stock_id      SERIAL PRIMARY KEY,
        ticker        VARCHAR(20) NOT NULL UNIQUE,
        company_name  VARCHAR(100),
        sector        VARCHAR(50),
        market        VARCHAR(50)
    );

    INSERT INTO dim_stock (ticker, company_name, sector, market)
    VALUES ('1155.KL', 'Malayan Banking Berhad (Maybank)', 'Finance', 'KLSE')
    ON CONFLICT (ticker) DO NOTHING;

    -- ========================
    -- FACT TABLES
    -- ========================

    CREATE TABLE IF NOT EXISTS fact_daily_prices (
        fact_id       SERIAL PRIMARY KEY,
        date_key      INT REFERENCES dim_date(date_key),
        stock_id      INT REFERENCES dim_stock(stock_id),
        open          NUMERIC(12,4),
        high          NUMERIC(12,4),
        low           NUMERIC(12,4),
        close         NUMERIC(12,4),
        adj_close     NUMERIC(12,4),
        volume        BIGINT,
        daily_return  NUMERIC(8,6),
        gdp           NUMERIC(20,4),
        inflation     NUMERIC(8,4),
        UNIQUE(date_key, stock_id)
    );

    CREATE INDEX IF NOT EXISTS idx_fact_daily_date ON fact_daily_prices(date_key);
    CREATE INDEX IF NOT EXISTS idx_fact_daily_stock ON fact_daily_prices(stock_id);

    CREATE TABLE IF NOT EXISTS fact_monthly_summary (
        summary_id    SERIAL PRIMARY KEY,
        year          INT NOT NULL,
        month         INT NOT NULL,
        stock_id      INT REFERENCES dim_stock(stock_id),
        avg_close     NUMERIC(12,4),
        avg_return    NUMERIC(8,6),
        total_volume  BIGINT,
        volatility    NUMERIC(8,6),
        UNIQUE(year, month, stock_id)
    );

    CREATE TABLE IF NOT EXISTS fact_volatility_index (
        vol_id          SERIAL PRIMARY KEY,
        date_key        INT REFERENCES dim_date(date_key),
        stock_id        INT REFERENCES dim_stock(stock_id),
        rolling_7d_vol  NUMERIC(8,6),
        rolling_30d_vol NUMERIC(8,6),
        UNIQUE(date_key, stock_id)
    );

    CREATE INDEX IF NOT EXISTS idx_vol_date ON fact_volatility_index(date_key);

    CREATE TABLE IF NOT EXISTS kpi_summary (
        kpi_id      SERIAL PRIMARY KEY,
        metric      VARCHAR(50) NOT NULL,
        year        INT NOT NULL,
        value       NUMERIC(20,4),
        updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(metric, year)
    );

    CREATE INDEX IF NOT EXISTS idx_kpi_metric ON kpi_summary(metric);
    CREATE INDEX IF NOT EXISTS idx_kpi_year ON kpi_summary(year);

    -- ========================
    -- REAL-TIME TABLE
    -- ========================

    CREATE TABLE IF NOT EXISTS real_time_prices (
        id          SERIAL PRIMARY KEY,
        ticker      VARCHAR(20) NOT NULL,
        timestamp   TIMESTAMP NOT NULL,
        open        NUMERIC(12,4),
        high        NUMERIC(12,4),
        low         NUMERIC(12,4),
        close       NUMERIC(12,4),
        volume      BIGINT,
        created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE INDEX IF NOT EXISTS idx_rt_ticker ON real_time_prices(ticker);
    CREATE INDEX IF NOT EXISTS idx_rt_timestamp ON real_time_prices(timestamp DESC);

    -- ========================
    -- AI ANALYTICS TABLES (NEW)
    -- ========================

    -- AI query audit log — tracks every natural language query
    CREATE TABLE IF NOT EXISTS ai_query_log (
        id            SERIAL PRIMARY KEY,
        question      TEXT NOT NULL,
        generated_sql TEXT,
        response      TEXT,
        latency_ms    INT,
        created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE INDEX IF NOT EXISTS idx_ai_log_created ON ai_query_log(created_at DESC);

    -- Anomaly alerts — statistical anomalies detected by the system
    CREATE TABLE IF NOT EXISTS anomaly_alerts (
        id            SERIAL PRIMARY KEY,
        ticker        VARCHAR(20) NOT NULL,
        alert_type    VARCHAR(50) NOT NULL,
        severity      VARCHAR(10) NOT NULL CHECK (severity IN ('critical', 'warning', 'info')),
        message       TEXT,
        metric_value  NUMERIC(12,4),
        threshold     NUMERIC(12,4),
        detected_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE INDEX IF NOT EXISTS idx_anomaly_ticker ON anomaly_alerts(ticker);
    CREATE INDEX IF NOT EXISTS idx_anomaly_detected ON anomaly_alerts(detected_at DESC);

    -- ========================
    -- DATA RETENTION POLICY
    -- ========================
    -- Real-time prices older than 90 days should be archived/deleted.
    -- Run this periodically via Airflow or cron:
    --   DELETE FROM real_time_prices WHERE created_at < NOW() - INTERVAL '90 days';
    --
    -- AI query logs older than 1 year should be archived:
    --   DELETE FROM ai_query_log WHERE created_at < NOW() - INTERVAL '1 year';

    -- ========================
    -- PERMISSIONS
    -- ========================

    GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO massmutual;
    GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO massmutual;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO massmutual;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO massmutual;

EOSQL

echo "✅ massmutual database initialized successfully (including AI tables)"
