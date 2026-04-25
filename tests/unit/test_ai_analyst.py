"""
Unit tests for AI Financial Analyst.

Tests SQL validation, safety guardrails, and graceful degradation.
"""

import os
import sys
import pytest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'frontend'))


@pytest.mark.unit
class TestSQLValidation:
    """Test SQL query safety validation."""

    def test_select_allowed(self):
        from ai_analyst import validate_sql
        assert validate_sql("SELECT * FROM dim_date LIMIT 10") is True

    def test_with_cte_allowed(self):
        from ai_analyst import validate_sql
        assert validate_sql("WITH cte AS (SELECT 1) SELECT * FROM cte") is True

    def test_insert_blocked(self):
        from ai_analyst import validate_sql
        assert validate_sql("INSERT INTO dim_date VALUES (1, '2024-01-01')") is False

    def test_update_blocked(self):
        from ai_analyst import validate_sql
        assert validate_sql("UPDATE dim_date SET year = 2025") is False

    def test_delete_blocked(self):
        from ai_analyst import validate_sql
        assert validate_sql("DELETE FROM dim_date") is False

    def test_drop_blocked(self):
        from ai_analyst import validate_sql
        assert validate_sql("DROP TABLE dim_date") is False

    def test_truncate_blocked(self):
        from ai_analyst import validate_sql
        assert validate_sql("TRUNCATE dim_date") is False

    def test_alter_blocked(self):
        from ai_analyst import validate_sql
        assert validate_sql("ALTER TABLE dim_date ADD COLUMN foo INT") is False

    def test_grant_blocked(self):
        from ai_analyst import validate_sql
        assert validate_sql("GRANT ALL ON dim_date TO public") is False

    def test_empty_blocked(self):
        from ai_analyst import validate_sql
        assert validate_sql("") is False

    def test_mixed_case_blocked(self):
        from ai_analyst import validate_sql
        assert validate_sql("select * from dim_date; DROP TABLE dim_date;") is False

    def test_select_with_subquery_allowed(self):
        from ai_analyst import validate_sql
        assert validate_sql("SELECT * FROM (SELECT 1 AS x) t") is True


@pytest.mark.unit
class TestFinancialAnalyst:
    """Test FinancialAnalyst class."""

    def test_init_fails_without_genai(self):
        """Should raise ImportError if google-genai isn't installed."""
        with patch.dict(sys.modules, {'google': None, 'google.genai': None}):
            from ai_analyst import FinancialAnalyst
            with pytest.raises(Exception):
                FinancialAnalyst("fake-key", MagicMock())

    def test_query_returns_structure(self):
        """Result should have expected keys."""
        from ai_analyst import FinancialAnalyst

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "SELECT year, AVG(close) FROM fact_daily_prices GROUP BY year LIMIT 10"
        mock_client.models.generate_content.return_value = mock_response

        with patch('ai_analyst.genai') as mock_genai:
            mock_genai.Client.return_value = mock_client

            mock_db = MagicMock()
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.description = [('year',), ('avg',)]
            mock_cursor.fetchall.return_value = [{'year': 2024, 'avg': 9.5}]
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
            mock_db.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_db.return_value.__exit__ = MagicMock(return_value=False)

            analyst = FinancialAnalyst.__new__(FinancialAnalyst)
            analyst.client = mock_client
            analyst.model = "test-model"
            analyst.get_db = mock_db
            analyst.api_key = "test"

            result = analyst.query("What is the average close price?")

            assert 'analysis' in result
            assert 'sql' in result
            assert 'data' in result
            assert 'latency_ms' in result
