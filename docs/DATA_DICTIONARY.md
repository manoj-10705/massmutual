# Data Dictionary

> Complete documentation of all database tables, columns, and data lineage.

---

## Star Schema Overview

```
                    ┌─────────────┐
                    │  dim_date   │
                    │─────────────│
                    │ date_key PK │─────┐
                    │ date, day   │     │
                    │ month, year │     │
                    └─────────────┘     │
                                        │
┌─────────────┐    ┌──────────────┐    │    ┌────────────────┐
│  dim_stock  │───▶│ fact_daily   │◀───┘    │ kpi_summary    │
│─────────────│    │──────────────│         │────────────────│
│ stock_id PK │    │ OHLCV data   │         │ metric, year   │
│ ticker      │    │ returns, GDP │         │ aggregate vals │
│ company     │    └──────────────┘         └────────────────┘
│ sector      │
└─────────────┘
```

---

## Dimension Tables

### dim_date

| Column | Type | Nullable | Description |
|---|---|---|---|
| date_key | INT (PK) | No | Surrogate key (auto-generated) |
| date | DATE (UNIQUE) | No | Calendar date |
| day | INT | No | Day of month (1-31) |
| month | INT | No | Month number (1-12) |
| month_name | VARCHAR(20) | No | Full month name (e.g., "January") |
| quarter | INT | No | Quarter number (1-4) |
| year | INT | No | Calendar year |
| weekday | VARCHAR(20) | No | Day name (e.g., "Monday") |

**Source:** Derived from `fact_daily_prices.Date` during Spark ETL
**Update Frequency:** On each batch ETL run (daily)
**Indexes:** `idx_dim_date_year(year)`, `idx_dim_date_month(year, month)`

### dim_stock

| Column | Type | Nullable | Description |
|---|---|---|---|
| stock_id | SERIAL (PK) | No | Auto-increment surrogate key |
| ticker | VARCHAR(20) (UNIQUE) | No | Stock ticker symbol |
| company_name | VARCHAR(100) | Yes | Full company name |
| sector | VARCHAR(50) | Yes | Industry sector |
| market | VARCHAR(50) | Yes | Stock exchange |

**Source:** Seed data via `02_create_tables.sh`
**Seed Data:** `1155.KL` = Malayan Banking Berhad (Maybank), Finance, KLSE

---

## Fact Tables

### fact_daily_prices

| Column | Type | Nullable | Description |
|---|---|---|---|
| fact_id | SERIAL (PK) | No | Auto-increment ID |
| date_key | INT (FK → dim_date) | Yes | Date dimension key |
| stock_id | INT (FK → dim_stock) | Yes | Stock dimension key |
| open | NUMERIC(12,4) | Yes | Opening price (MYR) |
| high | NUMERIC(12,4) | Yes | Daily high (MYR) |
| low | NUMERIC(12,4) | Yes | Daily low (MYR) |
| close | NUMERIC(12,4) | Yes | Closing price (MYR) |
| adj_close | NUMERIC(12,4) | Yes | Adjusted close (split/dividend adjusted) |
| volume | BIGINT | Yes | Trading volume (shares) |
| daily_return | NUMERIC(8,6) | Yes | Daily return (decimal, e.g., 0.015 = 1.5%) |
| gdp | NUMERIC(20,4) | Yes | Malaysian GDP constant 2015 MYR |
| inflation | NUMERIC(8,4) | Yes | Inflation rate (percentage) |

**Unique Constraint:** `(date_key, stock_id)`
**Source:** CSV dataset via Spark batch ETL
**Update Frequency:** Daily (idempotent — truncate + insert)

### fact_monthly_summary

| Column | Type | Nullable | Description |
|---|---|---|---|
| summary_id | SERIAL (PK) | No | Auto-increment ID |
| year | INT | No | Year |
| month | INT | No | Month (1-12) |
| stock_id | INT (FK → dim_stock) | Yes | Stock dimension key |
| avg_close | NUMERIC(12,4) | Yes | Average closing price for the month |
| avg_return | NUMERIC(8,6) | Yes | Average daily return for the month |
| total_volume | BIGINT | Yes | Total trading volume for the month |
| volatility | NUMERIC(8,6) | Yes | Std dev of daily returns (risk measure) |

**Unique Constraint:** `(year, month, stock_id)`
**Source:** Aggregated from `fact_daily_prices` by Spark ETL

### fact_volatility_index

| Column | Type | Nullable | Description |
|---|---|---|---|
| vol_id | SERIAL (PK) | No | Auto-increment ID |
| date_key | INT (FK → dim_date) | Yes | Date dimension key |
| stock_id | INT (FK → dim_stock) | Yes | Stock dimension key |
| rolling_7d_vol | NUMERIC(8,6) | Yes | 7-day rolling std dev of returns |
| rolling_30d_vol | NUMERIC(8,6) | Yes | 30-day rolling std dev of returns |

**Unique Constraint:** `(date_key, stock_id)`
**Source:** Window function over `fact_daily_prices.daily_return`

### kpi_summary

| Column | Type | Nullable | Description |
|---|---|---|---|
| kpi_id | SERIAL (PK) | No | Auto-increment ID |
| metric | VARCHAR(50) | No | Metric name |
| year | INT | No | Year |
| value | NUMERIC(20,4) | Yes | Metric value |
| updated_at | TIMESTAMP | Yes | Last update timestamp |

**Unique Constraint:** `(metric, year)`
**Metrics:** AVG_CLOSE, AVG_GDP, AVG_INFLATION, AVG_DAILY_RETURN_PCT, YEARLY_VOLATILITY, TOTAL_VOLUME

---

## Real-Time Tables

### real_time_prices

| Column | Type | Description |
|---|---|---|
| id | SERIAL (PK) | Auto-increment ID |
| ticker | VARCHAR(20) | Stock ticker |
| timestamp | TIMESTAMP | Price timestamp |
| open/high/low/close | NUMERIC(12,4) | OHLC prices |
| volume | BIGINT | Trade volume |
| created_at | TIMESTAMP | Record creation time |

**Source:** Spark Structured Streaming from Kafka
**Retention:** 90 days (manual cleanup recommended)

---

## AI & Analytics Tables

### ai_query_log

| Column | Type | Description |
|---|---|---|
| id | SERIAL (PK) | Auto-increment ID |
| question | TEXT | User's natural language question |
| generated_sql | TEXT | AI-generated SQL query |
| response | TEXT | AI analysis response |
| latency_ms | INT | Processing time in milliseconds |
| created_at | TIMESTAMP | Query timestamp |

**Purpose:** Audit trail for all AI analyst queries

### anomaly_alerts

| Column | Type | Description |
|---|---|---|
| id | SERIAL (PK) | Auto-increment ID |
| ticker | VARCHAR(20) | Stock ticker |
| alert_type | VARCHAR(50) | Type: `volume_spike`, `price_anomaly` |
| severity | VARCHAR(10) | `critical`, `warning`, `info` |
| message | TEXT | Human-readable alert message |
| metric_value | NUMERIC(12,4) | Actual observed value |
| threshold | NUMERIC(12,4) | Expected/average value |
| detected_at | TIMESTAMP | Detection timestamp |

---

## Data Lineage

```
Finnhub API ──► Kafka ──► Spark Streaming ──► real_time_prices (PostgreSQL)
                                           ──► Redis Cache (hot path)

CSV Dataset ──► Spark Batch ETL ──► dim_date
                                ──► fact_daily_prices
                                ──► fact_monthly_summary
                                ──► fact_volatility_index
                                ──► kpi_summary

User Question ──► Gemini API ──► SQL Query ──► PostgreSQL ──► ai_query_log
```
