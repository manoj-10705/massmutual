# AI Financial Analyst — Technical Documentation

## Overview

The AI Financial Analyst uses Google Gemini to provide natural language querying of the financial database. Users can ask questions in plain English and receive data-backed analysis with auto-generated visualizations.

## How It Works

```
User Question
    │
    ▼
┌─── Gemini API ───────────────────────┐
│ System prompt includes:              │
│   - Full database schema             │
│   - Column descriptions              │
│   - Business context (Maybank/KLSE)  │
│   - SQL safety rules                 │
└──────────┬───────────────────────────┘
           │
           ▼
    Generated SQL Query
           │
    ┌──────┴──────┐
    │  Validation  │  ← Only SELECT/WITH allowed
    └──────┬──────┘
           │
           ▼
    Execute on PostgreSQL
           │
           ▼
┌─── Gemini API ───────────────────────┐
│ Receives:                            │
│   - Original question                │
│   - SQL query                        │
│   - Query results (first 50 rows)    │
│ Returns:                             │
│   - Human-readable analysis          │
│   - Chart type suggestion            │
└──────────┬───────────────────────────┘
           │
           ▼
    Response: {analysis, sql, data, chart}
```

## Supported Question Types

| Category | Example Questions |
|---|---|
| **Trends** | "What was the trend in Maybank stock price over 2023?" |
| **Volatility** | "What was the most volatile month in 2023?" |
| **Comparisons** | "Compare average returns in 2022 vs 2023" |
| **Correlations** | "Is there a correlation between GDP and stock price?" |
| **Aggregations** | "What is the average daily return by year?" |
| **Volume** | "Which quarter had the highest trading volume?" |
| **Macro** | "How does inflation relate to stock performance?" |

## Safety Guardrails

1. **Read-Only Queries:** Only `SELECT` and `WITH` (CTE) statements are allowed
2. **Blocklist:** `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`, `EXEC`, `GRANT`, `REVOKE`, `COPY` are all blocked
3. **Query Timeout:** 10-second execution timeout prevents runaway queries
4. **Row Limit:** Results capped at 100 rows in response
5. **Input Limit:** Questions capped at 500 characters
6. **Rate Limiting:** 20 AI queries per minute per IP
7. **Audit Log:** Every query is logged to `ai_query_log` table

## Configuration

Set `GEMINI_API_KEY` in `.env`:

```bash
# Get your key at https://aistudio.google.com/
GEMINI_API_KEY=your_key_here
```

**Free Tier Limits:** 15 requests per minute, 1 million tokens per day.

## Graceful Degradation

If `GEMINI_API_KEY` is not set:
- AI tab shows "Set up your Gemini API key to enable AI analysis"
- `/api/ai/query` returns `503` with setup instructions
- All other dashboard features work normally

## API Reference

### POST /api/ai/query

**Request:**
```json
{
    "question": "What was the most volatile month in 2023?"
}
```

**Response:**
```json
{
    "status": "ok",
    "analysis": "October 2023 had the highest volatility at 0.0234...",
    "sql": "SELECT month, volatility FROM fact_monthly_summary WHERE year=2023...",
    "data": [{"month": 10, "volatility": 0.0234}, ...],
    "chart": {
        "type": "bar",
        "labels": ["Jan", "Feb", ...],
        "values": [0.012, 0.015, ...],
        "title": "Monthly Volatility 2023"
    },
    "latency_ms": 2340
}
```

## Limitations

- Cannot answer questions outside the available dataset
- No real-time data awareness (queries the star schema, not live cache)
- Complex multi-step reasoning may produce incorrect SQL
- Gemini free tier has rate limits (15 RPM)
