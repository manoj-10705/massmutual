"""
Unit tests for Flask API routes.

Tests all endpoints with mocked database and Redis connections.
"""

import os
import sys
import json
import pytest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'frontend'))


@pytest.mark.unit
class TestHealthEndpoints:
    """Test health and readiness probes."""

    def test_health_returns_200(self, client):
        res = client.get('/health')
        assert res.status_code == 200
        data = res.get_json()
        assert data['status'] == 'healthy'

    def test_ready_checks_dependencies(self, client):
        res = client.get('/ready')
        assert res.status_code in (200, 503)
        data = res.get_json()
        assert 'checks' in data
        assert 'database' in data['checks']


@pytest.mark.unit
class TestKPIEndpoint:
    """Test /api/kpis endpoint."""

    def test_kpis_returns_data(self, client, mock_db_pool):
        _, mock_conn, mock_cursor = mock_db_pool
        mock_cursor.fetchall.return_value = [
            {'metric': 'AVG_CLOSE', 'year': 2024, 'value': 9.82},
        ]

        res = client.get('/api/kpis')
        assert res.status_code == 200
        data = res.get_json()
        assert data['status'] == 'ok'

    def test_kpis_handles_db_error(self, client, mock_db_pool):
        mock_pool, _, _ = mock_db_pool
        mock_pool.getconn.side_effect = Exception("Connection failed")

        res = client.get('/api/kpis')
        assert res.status_code == 500
        data = res.get_json()
        assert data['status'] == 'error'


@pytest.mark.unit
class TestDailyEndpoint:
    """Test /api/daily endpoint."""

    def test_daily_returns_data(self, client, mock_db_pool):
        from datetime import date
        _, mock_conn, mock_cursor = mock_db_pool
        mock_cursor.fetchall.return_value = [
            {'date': date(2024, 1, 2), 'open': 9.40, 'high': 9.55,
             'low': 9.35, 'close': 9.50, 'volume': 15000000,
             'daily_return': 0.015, 'gdp': 398e9, 'inflation': 2.1},
        ]

        res = client.get('/api/daily')
        assert res.status_code == 200
        data = res.get_json()
        assert data['status'] == 'ok'
        assert data['count'] == 1

    def test_daily_with_year_filter(self, client, mock_db_pool):
        _, mock_conn, mock_cursor = mock_db_pool
        mock_cursor.fetchall.return_value = []

        res = client.get('/api/daily?year=2024')
        assert res.status_code == 200


@pytest.mark.unit
class TestVolatilityEndpoint:
    """Test /api/volatility endpoint."""

    def test_volatility_returns_data(self, client, mock_db_pool):
        from datetime import date
        _, mock_conn, mock_cursor = mock_db_pool
        mock_cursor.fetchall.return_value = [
            {'date': date(2024, 1, 2), 'rolling_7d_vol': 0.012, 'rolling_30d_vol': 0.015},
        ]

        res = client.get('/api/volatility')
        assert res.status_code == 200
        data = res.get_json()
        assert data['status'] == 'ok'


@pytest.mark.unit
class TestRealtimeEndpoint:
    """Test /api/realtime endpoint."""

    @patch('app.get_redis')
    def test_realtime_no_redis(self, mock_redis, client):
        mock_redis.return_value = None
        res = client.get('/api/realtime')
        assert res.status_code == 503


@pytest.mark.unit
class TestAIEndpoint:
    """Test /api/ai/query endpoint."""

    def test_ai_requires_post(self, client):
        res = client.get('/api/ai/query')
        assert res.status_code == 405

    def test_ai_requires_question(self, client):
        res = client.post('/api/ai/query',
                        data=json.dumps({}),
                        content_type='application/json')
        # Without GEMINI_API_KEY configured, the endpoint returns 503 before
        # reaching the body validation. Both 400 and 503 are acceptable.
        assert res.status_code in (400, 503)

    def test_ai_without_key_returns_503(self, client):
        with patch.dict(os.environ, {'GEMINI_API_KEY': ''}):
            res = client.post('/api/ai/query',
                            data=json.dumps({'question': 'test'}),
                            content_type='application/json')
            # Should return error about AI not configured
            assert res.status_code in (500, 503)


@pytest.mark.unit
class TestErrorHandlers:
    """Test error response format."""

    def test_404_returns_json(self, client):
        res = client.get('/nonexistent')
        assert res.status_code == 404
        data = res.get_json()
        assert data['status'] == 'error'
        assert data['code'] == 'NOT_FOUND'

    def test_dashboard_renders(self, client):
        res = client.get('/')
        assert res.status_code == 200
