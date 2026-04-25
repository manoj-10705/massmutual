"""
Integration tests for database schema validation.

Requires a running PostgreSQL instance with the massmutual schema.
Run with: pytest tests/integration -m integration
"""

import os
import pytest
import psycopg2

DB_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': int(os.getenv('POSTGRES_PORT', '5433')),
    'database': os.getenv('APP_DB_NAME', 'massmutual'),
    'user': os.getenv('APP_DB_USER', 'massmutual'),
    'password': os.getenv('APP_DB_PASSWORD', 'massmutual123'),
}


def get_connection():
    try:
        return psycopg2.connect(**DB_CONFIG)
    except Exception:
        pytest.skip("Database not available for integration tests")


@pytest.mark.integration
class TestSchemaExists:
    """Verify all expected tables exist."""

    EXPECTED_TABLES = [
        'dim_date', 'dim_stock',
        'fact_daily_prices', 'fact_monthly_summary', 'fact_volatility_index',
        'kpi_summary', 'real_time_prices',
        'ai_query_log', 'anomaly_alerts',
    ]

    def test_all_tables_exist(self):
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT table_name FROM information_schema.tables
                    WHERE table_schema = 'public'
                """)
                tables = {row[0] for row in cur.fetchall()}

            for table in self.EXPECTED_TABLES:
                assert table in tables, f"Missing table: {table}"
        finally:
            conn.close()


@pytest.mark.integration
class TestColumnTypes:
    """Verify critical column types match expectations."""

    def test_dim_date_columns(self):
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_name = 'dim_date'
                    ORDER BY ordinal_position
                """)
                cols = {row[0]: row[1] for row in cur.fetchall()}

            assert 'date_key' in cols
            assert 'date' in cols
            assert 'year' in cols
            assert cols['date'] == 'date'
            assert cols['year'] == 'integer'
        finally:
            conn.close()

    def test_fact_daily_columns(self):
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT column_name FROM information_schema.columns
                    WHERE table_name = 'fact_daily_prices'
                """)
                cols = {row[0] for row in cur.fetchall()}

            expected = {'fact_id', 'date_key', 'stock_id', 'open', 'high',
                       'low', 'close', 'adj_close', 'volume', 'daily_return',
                       'gdp', 'inflation'}
            assert expected.issubset(cols), f"Missing columns: {expected - cols}"
        finally:
            conn.close()


@pytest.mark.integration
class TestIndexes:
    """Verify indexes exist for query performance."""

    def test_critical_indexes_exist(self):
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT indexname FROM pg_indexes
                    WHERE schemaname = 'public'
                """)
                indexes = {row[0] for row in cur.fetchall()}

            critical = ['idx_dim_date_year', 'idx_fact_daily_date',
                       'idx_kpi_metric', 'idx_rt_timestamp']
            for idx in critical:
                assert idx in indexes, f"Missing index: {idx}"
        finally:
            conn.close()


@pytest.mark.integration
class TestSeedData:
    """Verify seed data was loaded."""

    def test_dim_stock_has_maybank(self):
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT ticker FROM dim_stock WHERE ticker = '1155.KL'")
                assert cur.fetchone() is not None, "Maybank seed data missing"
        finally:
            conn.close()
