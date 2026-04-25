"""
Shared test fixtures for the MassMutual test suite.
"""

import os
import sys
import pytest
from unittest.mock import MagicMock, patch

# Add frontend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'frontend'))


@pytest.fixture
def mock_db_pool():
    """Mock database connection pool."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    mock_pool = MagicMock()
    mock_pool.getconn.return_value = mock_conn
    return mock_pool, mock_conn, mock_cursor


@pytest.fixture
def app(mock_db_pool):
    """Create Flask test app with mocked database."""
    mock_pool, mock_conn, mock_cursor = mock_db_pool

    with patch.dict(os.environ, {
        'POSTGRES_HOST': 'localhost',
        'APP_DB_NAME': 'test_db',
        'APP_DB_USER': 'test_user',
        'APP_DB_PASSWORD': 'test_pass',
        'REDIS_HOST': 'localhost',
        'REDIS_PORT': '6379',
    }):
        with patch('psycopg2.pool.ThreadedConnectionPool', return_value=mock_pool):
            from app import app as flask_app, init_db_pool
            flask_app.config['TESTING'] = True
            init_db_pool()
            yield flask_app


@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()


@pytest.fixture
def sample_kpi_data():
    """Sample KPI data for testing."""
    return [
        {'metric': 'AVG_CLOSE', 'year': 2023, 'value': 9.45},
        {'metric': 'AVG_CLOSE', 'year': 2024, 'value': 9.82},
        {'metric': 'AVG_GDP', 'year': 2023, 'value': 398000000000.0},
        {'metric': 'AVG_GDP', 'year': 2024, 'value': 415000000000.0},
    ]


@pytest.fixture
def sample_daily_data():
    """Sample daily price data."""
    from datetime import date
    return [
        {
            'date': date(2024, 1, 2), 'open': 9.40, 'high': 9.55,
            'low': 9.35, 'close': 9.50, 'volume': 15000000,
            'daily_return': 0.015, 'gdp': 398000000000.0, 'inflation': 2.1,
        },
        {
            'date': date(2024, 1, 3), 'open': 9.50, 'high': 9.60,
            'low': 9.45, 'close': 9.55, 'volume': 12000000,
            'daily_return': 0.005, 'gdp': 398000000000.0, 'inflation': 2.1,
        },
    ]


@pytest.fixture
def sample_csv_path(tmp_path):
    """Create a sample CSV file for testing."""
    csv_content = """Date,Open,High,Low,Close,Adj Close,Volume,daily_return,GDP (constant 2015 US$),Inflation,rolling_volatility_30d
2024-01-02,9.40,9.55,9.35,9.50,9.50,15000000,0.015,398000000000,2.1,0.012
2024-01-03,9.50,9.60,9.45,9.55,9.55,12000000,0.005,398000000000,2.1,0.011
2024-01-04,9.55,9.65,9.50,9.60,9.60,18000000,0.008,398000000000,2.1,0.013
2024-01-05,9.60,9.62,9.40,9.42,9.42,20000000,-0.019,398000000000,2.1,0.015
"""
    csv_file = tmp_path / "test_data.csv"
    csv_file.write_text(csv_content)
    return str(csv_file)
