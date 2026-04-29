"""
MassMutual Financial Dashboard — Flask REST API + WebSocket + AI

Endpoints:
  GET  /                — Dashboard page
  GET  /health          — Liveness probe
  GET  /ready           — Readiness probe (checks DB + Redis)
  GET  /api/kpis        — Year-over-year KPI data
  GET  /api/daily       — Daily OHLCV prices (optional ?year=YYYY)
  GET  /api/volatility  — Rolling volatility data
  GET  /api/monthly     — Monthly summary data
  GET  /api/realtime    — Latest price from Redis
  GET  /api/anomalies   — Recent anomaly alerts
  POST /api/ai/query    — AI-powered natural language query

WebSocket Events:
  subscribe_prices      — Subscribe to live price updates
  price_update          — Server pushes real-time prices
"""

import json
import logging
import os
import sys
import threading
from contextlib import contextmanager
from functools import wraps

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_socketio import SocketIO, emit
from psycopg2 import pool
from psycopg2.extras import RealDictCursor

# ============================================
# Configuration
# ============================================


def require_env(name: str, default: str | None = None) -> str:
    """Get required environment variable or fail fast."""
    value = os.getenv(name, default)
    if value is None:
        logging.critical(f"Required environment variable '{name}' is not set.")
        sys.exit(1)
    return value


# Database
DB_CONFIG = {
    "host": require_env("POSTGRES_HOST", "postgres"),
    "database": require_env("APP_DB_NAME", "massmutual"),
    "user": require_env("APP_DB_USER", "massmutual"),
    "password": require_env("APP_DB_PASSWORD", "massmutual123"),
}

# Redis
REDIS_HOST = require_env("REDIS_HOST", "redis")
REDIS_PORT = int(require_env("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

# Security
API_SECRET_KEY = os.getenv("API_SECRET_KEY", None)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", None)

# ============================================
# Logging
# ============================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("MassMutualAPI")

# ============================================
# Flask App Setup
# ============================================

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET", "dev-secret-change-me")

# CORS — allow dashboard origin
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Rate limiting
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per minute"],
    storage_uri="memory://",
)

# WebSocket
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# ============================================
# Connection Pool
# ============================================

db_pool: pool.ThreadedConnectionPool | None = None


def init_db_pool() -> None:
    """Initialize the PostgreSQL connection pool."""
    global db_pool
    try:
        db_pool = pool.ThreadedConnectionPool(
            minconn=2,
            maxconn=10,
            **DB_CONFIG,
        )
        logger.info("Database connection pool initialized (min=2, max=10)")
    except Exception as e:
        logger.error(f"Failed to initialize DB pool: {e}")
        db_pool = None


@contextmanager
def get_db():
    """Get a pooled PostgreSQL connection with context manager."""
    if db_pool is None:
        init_db_pool()
    conn = None
    try:
        conn = db_pool.getconn()
        conn.cursor_factory = RealDictCursor
        yield conn
    except Exception:
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            db_pool.putconn(conn)


def get_redis():
    """Get a Redis connection."""
    try:
        import redis

        return redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            password=REDIS_PASSWORD,
            decode_responses=True,
        )
    except Exception:
        return None


# ============================================
# Authentication (optional)
# ============================================


def require_api_key(f):
    """Decorator: require X-API-Key header if API_SECRET_KEY is set."""

    @wraps(f)
    def decorated(*args, **kwargs):
        if API_SECRET_KEY and API_SECRET_KEY != "dev_secret_key_change_in_production":  # noqa: S105
            provided = request.headers.get("X-API-Key", "")
            if provided != API_SECRET_KEY:
                return (
                    jsonify(
                        {
                            "status": "error",
                            "code": "UNAUTHORIZED",
                            "message": "Invalid or missing API key",
                        }
                    ),
                    401,
                )
        return f(*args, **kwargs)

    return decorated


# ============================================
# Health Endpoints
# ============================================


@app.route("/health")
def health():
    """Liveness probe — always returns 200 if the process is running."""
    return jsonify({"status": "healthy"}), 200


@app.route("/ready")
def ready():
    """Readiness probe — checks DB and Redis connectivity."""
    checks = {}
    all_ok = True

    # Check DB
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"
        all_ok = False

    # Check Redis
    r = get_redis()
    if r:
        try:
            r.ping()
            checks["redis"] = "ok"
        except Exception as e:
            checks["redis"] = f"error: {e}"
            all_ok = False
    else:
        checks["redis"] = "unavailable"

    # Check AI
    checks["ai_analyst"] = "available" if GEMINI_API_KEY else "not configured"

    status_code = 200 if all_ok else 503
    return jsonify({"status": "ready" if all_ok else "degraded", "checks": checks}), status_code


# ============================================
# API Routes
# ============================================


@app.route("/api/kpis")
@require_api_key
@limiter.limit("100 per minute")
def api_kpis():
    """Year-over-year KPI data from kpi_summary table."""
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT metric, year, value
                    FROM kpi_summary
                    ORDER BY metric, year
                """)
                rows = cur.fetchall()

        result: dict[str, list] = {}
        for row in rows:
            metric = row["metric"]
            if metric not in result:
                result[metric] = []
            result[metric].append(
                {
                    "year": row["year"],
                    "value": float(row["value"]) if row["value"] else None,
                }
            )

        return jsonify({"status": "ok", "data": result})
    except Exception as e:
        logger.error(f"KPI query failed: {e}")
        return jsonify({"status": "error", "code": "DB_ERROR", "message": str(e)}), 500


@app.route("/api/daily")
@require_api_key
@limiter.limit("60 per minute")
def api_daily():
    """Daily OHLCV price data. Optional ?year=YYYY filter."""
    try:
        year_filter = request.args.get("year", None)
        ticker_filter = request.args.get("ticker", "1155.KL")

        with get_db() as conn:
            with conn.cursor() as cur:
                query = """
                    SELECT date, open, high, low, close,
                           volume, daily_return, gdp, inflation
                    FROM v_market_data
                    WHERE ticker = %s
                """
                params = [ticker_filter]
                if year_filter:
                    query += " AND EXTRACT(YEAR FROM date) = %s"
                    params.append(int(year_filter))

                query += " ORDER BY date"
                cur.execute(query, params)
                rows = cur.fetchall()

        data = [
            {
                "date": row["date"].isoformat() if row["date"] else None,
                "open": float(row["open"]) if row["open"] else None,
                "high": float(row["high"]) if row["high"] else None,
                "low": float(row["low"]) if row["low"] else None,
                "close": float(row["close"]) if row["close"] else None,
                "volume": int(row["volume"]) if row["volume"] else None,
                "daily_return": float(row["daily_return"]) if row["daily_return"] else None,
                "gdp": float(row["gdp"]) if row["gdp"] else None,
                "inflation": float(row["inflation"]) if row["inflation"] else None,
            }
            for row in rows
        ]

        return jsonify({"status": "ok", "count": len(data), "data": data})
    except Exception as e:
        logger.error(f"Daily query failed: {e}")
        return jsonify({"status": "error", "code": "DB_ERROR", "message": str(e)}), 500


@app.route("/api/volatility")
@require_api_key
@limiter.limit("100 per minute")
def api_volatility():
    """Rolling volatility data."""
    try:
        year_filter = request.args.get("year", None)
        ticker_filter = request.args.get("ticker", "1155.KL")

        with get_db() as conn:
            with conn.cursor() as cur:
                query = """
                    SELECT d.date, v.rolling_7d_vol, v.rolling_30d_vol
                    FROM fact_volatility_index v
                    JOIN dim_date d ON v.date_key = d.date_key
                    JOIN dim_stock s ON v.stock_id = s.stock_id
                    WHERE s.ticker = %s
                """
                params = [ticker_filter]
                if year_filter:
                    query += " AND d.year = %s"
                    params.append(int(year_filter))
                query += " ORDER BY d.date"
                cur.execute(query, params)
                rows = cur.fetchall()

        data = [
            {
                "date": row["date"].isoformat(),
                "vol_7d": float(row["rolling_7d_vol"]) if row["rolling_7d_vol"] else None,
                "vol_30d": float(row["rolling_30d_vol"]) if row["rolling_30d_vol"] else None,
            }
            for row in rows
        ]

        return jsonify({"status": "ok", "count": len(data), "data": data})
    except Exception as e:
        logger.error(f"Volatility query failed: {e}")
        return jsonify({"status": "error", "code": "DB_ERROR", "message": str(e)}), 500


@app.route("/api/monthly")
@require_api_key
@limiter.limit("100 per minute")
def api_monthly():
    """Monthly summary data."""
    try:
        year_filter = request.args.get("year", None)

        with get_db() as conn:
            with conn.cursor() as cur:
                if year_filter:
                    cur.execute(
                        """
                        SELECT year, month, avg_close, avg_return,
                               total_volume, volatility
                        FROM fact_monthly_summary
                        WHERE year = %s
                        ORDER BY year, month
                    """,
                        (int(year_filter),),
                    )
                else:
                    cur.execute("""
                        SELECT year, month, avg_close, avg_return,
                               total_volume, volatility
                        FROM fact_monthly_summary
                        ORDER BY year, month
                    """)
                rows = cur.fetchall()

        data = [
            {
                "year": row["year"],
                "month": row["month"],
                "avg_close": float(row["avg_close"]) if row["avg_close"] else None,
                "avg_return": float(row["avg_return"]) if row["avg_return"] else None,
                "total_volume": int(row["total_volume"]) if row["total_volume"] else None,
                "volatility": float(row["volatility"]) if row["volatility"] else None,
            }
            for row in rows
        ]

        return jsonify({"status": "ok", "count": len(data), "data": data})
    except Exception as e:
        logger.error(f"Monthly query failed: {e}")
        return jsonify({"status": "error", "code": "DB_ERROR", "message": str(e)}), 500


@app.route("/api/realtime")
@require_api_key
def api_realtime():
    """Latest real-time price from Redis."""
    r = get_redis()
    if not r:
        return jsonify({"status": "error", "code": "REDIS_UNAVAILABLE", "message": "Redis not available"}), 503

    try:
        ticker = request.args.get("ticker", "1155.KL")
        price_data = r.hgetall(f"price:{ticker}")

        if not price_data:
            return jsonify({"status": "ok", "data": None, "message": "No real-time data yet"})

        return jsonify({"status": "ok", "data": price_data})
    except Exception as e:
        logger.error(f"Realtime query failed: {e}")
        return jsonify({"status": "error", "code": "REDIS_ERROR", "message": str(e)}), 500


# ============================================
# AI Analyst Endpoint
# ============================================


@app.route("/api/ai/query", methods=["POST"])
@require_api_key
@limiter.limit("20 per minute")
def ai_query():
    """Natural language query → SQL → Analysis → Chart data."""
    if not GEMINI_API_KEY or GEMINI_API_KEY == "your_gemini_api_key_here":
        return (
            jsonify(
                {
                    "status": "error",
                    "code": "AI_NOT_CONFIGURED",
                    "message": "Gemini API key not configured. Set GEMINI_API_KEY in .env",
                }
            ),
            503,
        )

    body = request.get_json(silent=True)
    if not body or not body.get("question"):
        return (
            jsonify(
                {
                    "status": "error",
                    "code": "BAD_REQUEST",
                    "message": "Request body must include 'question' field",
                }
            ),
            400,
        )

    question = body["question"].strip()
    if len(question) > 500:
        return (
            jsonify(
                {
                    "status": "error",
                    "code": "BAD_REQUEST",
                    "message": "Question must be under 500 characters",
                }
            ),
            400,
        )

    try:
        from ai_analyst import FinancialAnalyst

        analyst = FinancialAnalyst(GEMINI_API_KEY, get_db)
        result = analyst.query(question)

        # Log to audit table
        try:
            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """INSERT INTO ai_query_log (question, generated_sql, response, latency_ms)
                           VALUES (%s, %s, %s, %s)""",
                        (question, result.get("sql", ""), result.get("analysis", ""), result.get("latency_ms", 0)),
                    )
                    conn.commit()
        except Exception:  # noqa: S110
            pass  # Non-fatal: audit logging should never break the response

        return jsonify({"status": "ok", **result})
    except Exception as e:
        logger.error(f"AI query failed: {e}")
        return jsonify({"status": "error", "code": "AI_ERROR", "message": str(e)}), 500


# ============================================
# Anomaly Endpoint
# ============================================


@app.route("/api/anomalies")
@require_api_key
def api_anomalies():
    """Recent anomaly alerts."""
    try:
        year_filter = request.args.get("year", None)
        ticker_filter = request.args.get("ticker", "1155.KL")

        with get_db() as conn:
            with conn.cursor() as cur:
                query = """
                    SELECT ticker, alert_type, severity, message,
                           metric_value, threshold, detected_at
                    FROM anomaly_alerts
                    WHERE ticker = %s
                """
                params = [ticker_filter]
                if year_filter:
                    query += " AND EXTRACT(YEAR FROM detected_at) = %s"
                    params.append(int(year_filter))
                query += " ORDER BY detected_at DESC LIMIT 100"
                cur.execute(query, params)
                rows = cur.fetchall()

        data = [
            {
                "ticker": row["ticker"],
                "alert_type": row["alert_type"],
                "severity": row["severity"],
                "message": row["message"],
                "metric_value": float(row["metric_value"]) if row["metric_value"] else None,
                "threshold": float(row["threshold"]) if row["threshold"] else None,
                "detected_at": row["detected_at"].isoformat() if row["detected_at"] else None,
            }
            for row in rows
        ]

        return jsonify({"status": "ok", "data": data})
    except Exception as e:
        logger.error(f"Anomalies query failed: {e}")
        return jsonify({"status": "error", "code": "DB_ERROR", "message": str(e)}), 500


# ============================================
# WebSocket Events
# ============================================


@socketio.on("subscribe_prices")
def handle_subscribe(data: dict) -> None:
    """Client subscribes to live price updates."""
    ticker = data.get("ticker", "BINANCE:BTCUSDT")
    logger.info(f"Client subscribed to price updates for {ticker}")
    emit("subscribed", {"ticker": ticker, "status": "ok"})


def price_publisher() -> None:
    """Background thread: poll Redis for price changes, push via WebSocket."""
    tickers = os.getenv("TICKERS", "1155.KL,BINANCE:BTCUSDT").split(",")
    r = get_redis()
    if not r:
        logger.warning("Redis not available — price publisher disabled")
        return

    # Use PubSub for instantaneous updates instead of polling
    pubsub = r.pubsub()
    pubsub.subscribe("price_updates")

    logger.info("Price publisher started (Redis PubSub mode)")

    for message in pubsub.listen():
        try:
            if message["type"] == "message":
                data = json.loads(message["data"])
                # The data from Spark is already a dict
                ticker = data.get("ticker")
                if ticker in tickers:
                    socketio.emit("price_update", data)
        except Exception as e:
            logger.warning(f"Price publisher error: {e}")


# ============================================
# Dashboard Route
# ============================================


@app.route("/")
def index():
    """Serve the main dashboard page."""
    return render_template("index.html")


# ============================================
# Error Handlers
# ============================================


@app.errorhandler(404)
def not_found(e):
    return jsonify({"status": "error", "code": "NOT_FOUND", "message": "Resource not found"}), 404


@app.errorhandler(429)
def rate_limited(e):
    return jsonify({"status": "error", "code": "RATE_LIMITED", "message": "Too many requests"}), 429


@app.errorhandler(500)
def internal_error(e):
    return jsonify({"status": "error", "code": "INTERNAL_ERROR", "message": "Internal server error"}), 500


# ============================================
# App Initialization
# ============================================


def create_app() -> Flask:
    """Application factory for testing and production."""
    init_db_pool()

    # Start price publisher in background
    publisher_thread = threading.Thread(target=price_publisher, daemon=True)
    publisher_thread.start()

    return app


# ============================================
# Run
# ============================================

if __name__ == "__main__":
    create_app()
    socketio.run(app, host="0.0.0.0", port=5000, debug=False, allow_unsafe_werkzeug=True)  # noqa: S104
