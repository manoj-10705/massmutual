"""
Finnhub WebSocket → Kafka Producer

Connects to Finnhub's WebSocket API for real-time trade data
and publishes to Kafka topic 'market-data'.

Architecture: Class-based with graceful shutdown support.
"""

import os
import sys
import json
import time
import signal
import logging
from datetime import datetime, timezone
from typing import Optional

import websocket
from kafka import KafkaProducer

# ============================================
# Configuration
# ============================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("MarketProducer")


def require_env(name: str, default: Optional[str] = None) -> str:
    """Get required environment variable or fail fast."""
    value = os.getenv(name, default)
    if value is None:
        logger.critical(f"Required env var '{name}' is not set.")
        sys.exit(1)
    return value


# ============================================
# Market Producer Class
# ============================================

class MarketProducer:
    """Publishes real-time market data from Finnhub to Kafka."""

    def __init__(self) -> None:
        self.kafka_broker = require_env("KAFKA_BROKER", "kafka:9092")
        self.kafka_topic = require_env("KAFKA_TOPIC", "market-data")
        self.tickers = require_env("TICKERS", "1155.KL").split(",")
        self.finnhub_key = os.getenv("FINNHUB_API_KEY", "")
        self.use_simulation = (
            not self.finnhub_key
            or self.finnhub_key == "your_finnhub_api_key_here"
        )
        self._producer: Optional[KafkaProducer] = None
        self._running = True
        self._message_count = 0

        # Register shutdown handlers
        signal.signal(signal.SIGTERM, self._shutdown)
        signal.signal(signal.SIGINT, self._shutdown)

    def _shutdown(self, signum: int, frame) -> None:
        """Graceful shutdown handler."""
        logger.info(f"Received signal {signum}. Shutting down gracefully...")
        self._running = False
        if self._producer:
            self._producer.flush(timeout=5)
            self._producer.close(timeout=5)
            logger.info(f"Kafka producer closed. Total messages sent: {self._message_count}")

    def _create_kafka_producer(self, max_retries: int = 10) -> KafkaProducer:
        """Create Kafka producer with retry logic."""
        for attempt in range(max_retries):
            try:
                producer = KafkaProducer(
                    bootstrap_servers=self.kafka_broker,
                    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                    acks="all",
                    retries=3,
                )
                logger.info(f"Connected to Kafka at {self.kafka_broker}")
                return producer
            except Exception as e:
                logger.warning(f"Kafka attempt {attempt + 1}/{max_retries} failed: {e}")
                time.sleep(5)
        raise ConnectionError(f"Could not connect to Kafka after {max_retries} attempts")

    def _publish(self, record: dict) -> None:
        """Publish a record to Kafka."""
        if self._producer:
            self._producer.send(self.kafka_topic, value=record)
            self._message_count += 1

    # ============================================
    # Finnhub WebSocket Mode
    # ============================================

    def _on_message(self, ws, message: str) -> None:
        """Handle incoming WebSocket messages from Finnhub."""
        try:
            data = json.loads(message)
            if data.get("type") == "trade":
                for trade in data.get("data", []):
                    record = {
                        "ticker": trade.get("s", "UNKNOWN"),
                        "price": trade.get("p", 0.0),
                        "volume": trade.get("v", 0),
                        "timestamp": datetime.fromtimestamp(
                            trade.get("t", 0) / 1000, tz=timezone.utc
                        ).isoformat(),
                        "source": "finnhub",
                    }
                    self._publish(record)
                    logger.info(f"Published: {record['ticker']} @ {record['price']}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")

    def _on_error(self, ws, error) -> None:
        logger.error(f"WebSocket error: {error}")

    def _on_close(self, ws, close_status, close_msg) -> None:
        logger.info(f"WebSocket closed: {close_status} - {close_msg}")

    def _on_open(self, ws) -> None:
        """Subscribe to configured tickers on WebSocket open."""
        logger.info("WebSocket connected to Finnhub")
        for ticker in self.tickers:
            ticker = ticker.strip()
            ws.send(json.dumps({"type": "subscribe", "symbol": ticker}))
            logger.info(f"Subscribed to {ticker}")

    def _run_finnhub(self) -> None:
        """Start Finnhub WebSocket streaming."""
        ws_url = f"wss://ws.finnhub.io?token={self.finnhub_key}"
        logger.info("Connecting to Finnhub WebSocket...")

        while self._running:
            try:
                ws = websocket.WebSocketApp(
                    ws_url,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close,
                    on_open=self._on_open,
                )
                ws.run_forever(ping_interval=30, ping_timeout=10)
            except Exception as e:
                logger.error(f"WebSocket connection failed: {e}")

            if self._running:
                logger.info("Reconnecting in 10 seconds...")
                time.sleep(10)

    # ============================================
    # Simulation Mode
    # ============================================

    def _run_simulation(self) -> None:
        """Generate simulated market data when no Finnhub API key is available."""
        import random

        logger.info("Running in SIMULATION mode (no real market data)")
        base_price = 9.50  # Approximate MBB price in MYR

        while self._running:
            for ticker in self.tickers:
                ticker = ticker.strip()
                change = random.uniform(-0.05, 0.05)
                base_price = max(1.0, base_price + change)

                record = {
                    "ticker": ticker,
                    "price": round(base_price, 4),
                    "volume": random.randint(100, 10000),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "source": "simulation",
                }
                self._publish(record)
                logger.info(f"[SIM] {record['ticker']} @ {record['price']}")

            time.sleep(15)

    # ============================================
    # Entry Point
    # ============================================

    def run(self) -> None:
        """Start the producer."""
        logger.info("=" * 50)
        logger.info("MassMutual Market Data Producer")
        logger.info(f"  Tickers: {self.tickers}")
        logger.info(f"  Kafka:   {self.kafka_broker} / Topic: {self.kafka_topic}")
        logger.info(f"  Mode:    {'SIMULATION' if self.use_simulation else 'LIVE (Finnhub)'}")
        logger.info("=" * 50)

        self._producer = self._create_kafka_producer()

        if self.use_simulation:
            self._run_simulation()
        else:
            self._run_finnhub()


# ============================================
# Main
# ============================================

if __name__ == "__main__":
    producer = MarketProducer()
    producer.run()
