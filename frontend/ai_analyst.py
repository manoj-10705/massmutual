"""
MassMutual AI Financial Analyst

Uses Google Gemini to provide natural language querying of the financial
database. Generates SQL from user questions, executes read-only queries,
and returns human-readable analysis with chart suggestions.

Safety:
  - Only SELECT queries are allowed (no mutations)
  - SQL is validated before execution
  - Query timeout enforced
  - All queries are logged to ai_query_log table
"""

import logging
import re
import time
from collections.abc import Callable
from typing import Any

logger = logging.getLogger("AIAnalyst")

# Database schema context for the LLM
SCHEMA_CONTEXT = """
You have access to a PostgreSQL database with the following star schema for Malaysian stock market data (Maybank/MBB - ticker 1155.KL):

DIMENSION TABLES:
- dim_date (date_key INT PK, date DATE, day INT, month INT, month_name VARCHAR, quarter INT, year INT, weekday VARCHAR)
- dim_stock (stock_id SERIAL PK, ticker VARCHAR, company_name VARCHAR, sector VARCHAR, market VARCHAR)

FACT TABLES:
- fact_daily_prices (fact_id PK, date_key FK→dim_date, stock_id FK→dim_stock, open NUMERIC, high NUMERIC, low NUMERIC, close NUMERIC, adj_close NUMERIC, volume BIGINT, daily_return NUMERIC, gdp NUMERIC, inflation NUMERIC)
  → JOIN with dim_date ON date_key for date queries
  → daily_return is a decimal (e.g., 0.015 = 1.5%)
  → gdp is in constant 2015 MYR
  → inflation is percentage

- fact_monthly_summary (summary_id PK, year INT, month INT, stock_id FK, avg_close NUMERIC, avg_return NUMERIC, total_volume BIGINT, volatility NUMERIC)
  → volatility is standard deviation of daily returns

- fact_volatility_index (vol_id PK, date_key FK→dim_date, stock_id FK, rolling_7d_vol NUMERIC, rolling_30d_vol NUMERIC)
  → Rolling window standard deviations

- kpi_summary (kpi_id PK, metric VARCHAR, year INT, value NUMERIC, updated_at TIMESTAMP)
  → Metrics: AVG_CLOSE, AVG_GDP, AVG_INFLATION, AVG_DAILY_RETURN_PCT, YEARLY_VOLATILITY, TOTAL_VOLUME
  → One row per metric per year

- real_time_prices (id PK, ticker VARCHAR, timestamp TIMESTAMP, open NUMERIC, high NUMERIC, low NUMERIC, close NUMERIC, volume BIGINT, created_at TIMESTAMP)
  → Streaming prices from Kafka pipeline

UNIFIED VIEWS:
- v_market_data (ticker VARCHAR, date DATE, open NUMERIC, high NUMERIC, low NUMERIC, close NUMERIC, volume BIGINT, daily_return NUMERIC, gdp NUMERIC, inflation NUMERIC)
  → This is the RECOMMENDED table for any general market data queries.
  → It automatically combines historical data (from fact_daily_prices) and today's live data (aggregated from real_time_prices).
  → Use this for price trends, OHLC lookups, and historical analysis that includes today.

IMPORTANT RULES:
- Always JOIN fact_daily_prices with dim_date using date_key to get actual dates
- stock_id = 1 is Maybank (1155.KL)
- Use LIMIT to prevent returning too many rows (max 1000)
- Round numeric results to 4 decimal places
- For percentage display, multiply decimal returns by 100
"""


def validate_sql(query: str) -> bool:
    """Validate that a SQL query is read-only (SELECT only)."""
    normalized = query.strip().upper()

    # Must start with SELECT or WITH (for CTEs)
    if not (normalized.startswith("SELECT") or normalized.startswith("WITH")):
        return False

    # Block dangerous keywords
    dangerous = [
        "INSERT",
        "UPDATE",
        "DELETE",
        "DROP",
        "ALTER",
        "CREATE",
        "TRUNCATE",
        "EXEC",
        "EXECUTE",
        "GRANT",
        "REVOKE",
        "COPY",
    ]
    for keyword in dangerous:
        # Match as whole word to avoid false positives
        if re.search(rf"\b{keyword}\b", normalized):
            return False

    return True


class FinancialAnalyst:
    """AI-powered financial data analyst using Google Gemini."""

    def __init__(self, api_key: str, db_context_manager: Callable):
        """
        Args:
            api_key: Google Gemini API key
            db_context_manager: Callable that returns a context manager yielding a DB connection
        """
        self.api_key = api_key
        self.get_db = db_context_manager

        try:
            from google import genai

            self.client = genai.Client(api_key=api_key)
            self.model = "gemini-2.5-flash"
            logger.info("Gemini AI client initialized")
        except ImportError:
            logger.error("google-genai package not installed")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {e}")
            raise

    def query(self, question: str) -> dict[str, Any]:
        """
        Process a natural language question about financial data.

        Returns:
            {
                "analysis": str,       # Human-readable analysis
                "sql": str,            # Generated SQL query
                "data": list,          # Query results
                "chart": dict | None,  # Chart suggestion
                "latency_ms": int      # Processing time
            }
        """
        start_time = time.time()

        try:
            # Step 1: Generate SQL from question
            sql_query = self._generate_sql(question)

            if not sql_query or not validate_sql(sql_query):
                return {
                    "analysis": "I couldn't generate a safe query for that question. Please try rephrasing.",
                    "sql": sql_query or "",
                    "data": [],
                    "chart": None,
                    "latency_ms": int((time.time() - start_time) * 1000),
                }

            # Step 2: Execute SQL
            data = self._execute_sql(sql_query)

            # Step 3: Generate analysis from results
            analysis, chart = self._generate_analysis(question, sql_query, data)

            latency = int((time.time() - start_time) * 1000)

            return {
                "analysis": analysis,
                "sql": sql_query,
                "data": data[:100],  # Limit response size
                "chart": chart,
                "latency_ms": latency,
            }

        except Exception as e:
            latency = int((time.time() - start_time) * 1000)
            logger.error(f"AI query failed: {e}")
            return {
                "analysis": f"An error occurred while processing your question: {str(e)}",
                "sql": "",
                "data": [],
                "chart": None,
                "latency_ms": latency,
            }

    def _generate_sql(self, question: str) -> str | None:
        """Use Gemini to generate SQL from a natural language question."""
        prompt = f"""{SCHEMA_CONTEXT}

Given the above database schema, generate a PostgreSQL SELECT query to answer this question:

"{question}"

Rules:
- Return ONLY the SQL query, no explanation
- Use proper JOINs with dim_date for date-related queries
- Always LIMIT results to at most 100 rows
- Round numeric values to 4 decimal places
- If the question can't be answered with the available data, return: SELECT 'Question cannot be answered with available data' AS message
"""

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
            )
            sql = response.text.strip()

            # Clean up: remove markdown code blocks if present
            if sql.startswith("```"):
                lines = sql.split("\n")
                sql = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
                sql = sql.strip()

            return sql
        except Exception as e:
            logger.error(f"SQL generation failed: {e}")
            return None

    def _execute_sql(self, query: str) -> list[dict]:
        """Execute a read-only SQL query and return results."""
        with self.get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SET statement_timeout = '10s'")
                cur.execute(query)
                _ = [desc[0] for desc in cur.description] if cur.description else []  # noqa: F841
                rows = cur.fetchall()

        # Convert to serializable format
        result = []
        for row in rows:
            record = {}
            for key, value in row.items():
                if hasattr(value, "isoformat"):
                    record[key] = value.isoformat()
                elif isinstance(value, (int, float, str, bool, type(None))):
                    record[key] = value
                else:
                    record[key] = float(value) if value is not None else None
            result.append(record)

        return result

    def _generate_analysis(self, question: str, sql: str, data: list) -> tuple[str, dict | None]:
        """Use Gemini to generate human-readable analysis from query results."""
        if not data:
            return "No data found for your query.", None

        # Limit data sent to LLM
        sample = data[:50]

        prompt = f"""You are an expert financial analyst for Maybank (MBB), listed on KLSE as 1155.KL.

The user asked: "{question}"

The following SQL was executed:
```sql
{sql}
```

Results ({len(data)} rows, showing first {len(sample)}):
{sample}

Please provide:
1. A clear, insightful analysis of the data (3-5 sentences)
2. Key takeaways and any notable trends
3. If relevant, suggest a chart type and specify the data format

Format your response as:
ANALYSIS:
[your analysis here]

CHART:
[If a chart would be helpful, specify: type (bar/line/scatter), x_field, y_field(s), title. Otherwise write "none"]
"""

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
            )
            text = response.text.strip()

            # Parse analysis and chart suggestion
            analysis = text
            chart = None

            if "ANALYSIS:" in text and "CHART:" in text:
                parts = text.split("CHART:")
                analysis = parts[0].replace("ANALYSIS:", "").strip()
                chart_text = parts[1].strip().lower()

                if chart_text != "none":
                    chart = self._parse_chart_suggestion(chart_text, data)

            return analysis, chart

        except Exception as e:
            logger.error(f"Analysis generation failed: {e}")
            return f"Query returned {len(data)} rows. Raw data is available below.", None

    def _parse_chart_suggestion(self, text: str, data: list) -> dict | None:
        """Parse chart suggestion from LLM response."""
        try:
            chart_type = "bar"
            if "line" in text:
                chart_type = "line"
            elif "scatter" in text:
                chart_type = "scatter"

            if data and len(data) > 0:
                keys = list(data[0].keys())
                return {
                    "type": chart_type,
                    "labels": [str(row.get(keys[0], "")) for row in data[:50]],
                    "values": [row.get(keys[1] if len(keys) > 1 else keys[0], 0) for row in data[:50]],
                    "title": f"AI Generated: {keys[1] if len(keys) > 1 else keys[0]} by {keys[0]}",
                    "x_label": keys[0],
                    "y_label": keys[1] if len(keys) > 1 else keys[0],
                }
        except Exception:  # noqa: S110
            pass
        return None
