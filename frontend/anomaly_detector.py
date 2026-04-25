"""
MassMutual Anomaly Detection Engine

Detects statistical anomalies in financial data:
- Price anomalies (Z-score based)
- Volume spikes
- Volatility regime changes

Designed to run as a lightweight check on API request or background schedule.
"""

import logging
from typing import Any, Callable
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger("AnomalyDetector")


@dataclass
class AnomalyAlert:
    """Represents a detected anomaly."""
    ticker: str
    alert_type: str
    severity: str  # "critical", "warning", "info"
    message: str
    metric_value: float
    threshold: float
    detected_at: datetime


class AnomalyDetector:
    """Statistical anomaly detection for financial time series."""

    def __init__(self, db_context_manager: Callable):
        self.get_db = db_context_manager

    def detect_volume_spikes(
        self, ticker: str = "1155.KL", z_threshold: float = 2.5
    ) -> list[AnomalyAlert]:
        """Detect volume spikes using Z-score against 30-day rolling average."""
        alerts = []
        try:
            with self.get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        WITH stats AS (
                            SELECT
                                d.date,
                                f.volume,
                                AVG(f.volume) OVER (ORDER BY d.date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) AS avg_vol,
                                STDDEV(f.volume) OVER (ORDER BY d.date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) AS std_vol
                            FROM fact_daily_prices f
                            JOIN dim_date d ON f.date_key = d.date_key
                            JOIN dim_stock s ON f.stock_id = s.stock_id
                            WHERE s.ticker = %s
                            ORDER BY d.date DESC
                            LIMIT 30
                        )
                        SELECT date, volume, avg_vol, std_vol,
                               CASE WHEN std_vol > 0 THEN (volume - avg_vol) / std_vol ELSE 0 END AS z_score
                        FROM stats
                        WHERE std_vol > 0
                        ORDER BY date DESC
                        LIMIT 10
                    """, (ticker,))
                    rows = cur.fetchall()

                    for row in rows:
                        z = float(row["z_score"]) if row["z_score"] else 0
                        if abs(z) >= z_threshold:
                            severity = "critical" if abs(z) >= 3.5 else "warning"
                            direction = "above" if z > 0 else "below"
                            alerts.append(AnomalyAlert(
                                ticker=ticker,
                                alert_type="volume_spike",
                                severity=severity,
                                message=f"Volume {direction} normal: {z:.1f}σ from 30-day average on {row['date']}",
                                metric_value=float(row["volume"]),
                                threshold=float(row["avg_vol"]),
                                detected_at=datetime.now(),
                            ))

        except Exception as e:
            logger.error(f"Volume spike detection failed: {e}")

        return alerts

    def detect_price_anomalies(
        self, ticker: str = "1155.KL", z_threshold: float = 2.0
    ) -> list[AnomalyAlert]:
        """Detect unusual daily returns using Z-score."""
        alerts = []
        try:
            with self.get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        WITH stats AS (
                            SELECT
                                d.date,
                                f.daily_return,
                                f.close,
                                AVG(f.daily_return) OVER (ORDER BY d.date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) AS avg_ret,
                                STDDEV(f.daily_return) OVER (ORDER BY d.date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) AS std_ret
                            FROM fact_daily_prices f
                            JOIN dim_date d ON f.date_key = d.date_key
                            JOIN dim_stock s ON f.stock_id = s.stock_id
                            WHERE s.ticker = %s AND f.daily_return IS NOT NULL
                            ORDER BY d.date DESC
                            LIMIT 30
                        )
                        SELECT date, daily_return, close, avg_ret, std_ret,
                               CASE WHEN std_ret > 0 THEN (daily_return - avg_ret) / std_ret ELSE 0 END AS z_score
                        FROM stats
                        WHERE std_ret > 0
                        ORDER BY date DESC
                        LIMIT 10
                    """, (ticker,))
                    rows = cur.fetchall()

                    for row in rows:
                        z = float(row["z_score"]) if row["z_score"] else 0
                        if abs(z) >= z_threshold:
                            severity = "critical" if abs(z) >= 3.0 else "warning"
                            direction = "gain" if z > 0 else "loss"
                            pct = float(row["daily_return"]) * 100 if row["daily_return"] else 0
                            alerts.append(AnomalyAlert(
                                ticker=ticker,
                                alert_type="price_anomaly",
                                severity=severity,
                                message=f"Unusual {direction}: {pct:.2f}% daily return ({z:.1f}σ) on {row['date']}",
                                metric_value=float(row["close"]) if row["close"] else 0,
                                threshold=float(row["avg_ret"]) if row["avg_ret"] else 0,
                                detected_at=datetime.now(),
                            ))

        except Exception as e:
            logger.error(f"Price anomaly detection failed: {e}")

        return alerts

    def run_all_checks(self, ticker: str = "1155.KL") -> list[AnomalyAlert]:
        """Run all anomaly detection checks."""
        alerts = []
        alerts.extend(self.detect_volume_spikes(ticker))
        alerts.extend(self.detect_price_anomalies(ticker))
        return sorted(alerts, key=lambda a: a.detected_at, reverse=True)
