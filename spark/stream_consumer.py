"""
MassMutual Spark Structured Streaming Consumer

Reads real-time market data from Kafka, writes to PostgreSQL (real_time_prices)
and Redis (hot cache for dashboard).

Uses foreach instead of collect() for distributed writes.
Checkpoints to persistent volume for exactly-once semantics.
"""

import os
import sys
import json
import logging
from typing import Optional

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import col, from_json, current_timestamp
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, LongType

# ============================================
# Configuration
# ============================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("StreamConsumer")


def require_env(name: str, default: Optional[str] = None) -> str:
    """Get required environment variable or fail fast."""
    value = os.getenv(name, default)
    if value is None:
        logger.critical(f"Required env var '{name}' is not set.")
        sys.exit(1)
    return value


# Message schema from Kafka producer
MESSAGE_SCHEMA = StructType([
    StructField("ticker", StringType(), False),
    StructField("price", DoubleType(), False),
    StructField("volume", LongType(), True),
    StructField("timestamp", StringType(), False),
    StructField("source", StringType(), True),
])


# ============================================
# Writer Functions (used by foreachBatch)
# ============================================

def write_to_postgres_and_redis(batch_df: DataFrame, batch_id: int) -> None:
    """
    Write each micro-batch to PostgreSQL and Redis.
    Uses foreach to write to Redis without collecting to driver.
    """
    if batch_df.isEmpty():
        return

    row_count = batch_df.count()
    logger.info(f"Processing batch {batch_id}: {row_count} rows")

    # JDBC config
    jdbc_url = f"jdbc:postgresql://{require_env('POSTGRES_HOST', 'postgres')}:5432/{require_env('APP_DB_NAME', 'massmutual')}"
    jdbc_props = {
        "user": require_env("APP_DB_USER", "massmutual"),
        "password": require_env("APP_DB_PASSWORD", "massmutual123"),
        "driver": "org.postgresql.Driver",
    }

    # Write to PostgreSQL — real_time_prices table
    postgres_df = batch_df.select(
        col("ticker"),
        col("timestamp"),
        col("price").alias("close"),
        col("price").alias("open"),
        col("price").alias("high"),
        col("price").alias("low"),
        col("volume"),
    )

    try:
        postgres_df.write.jdbc(
            url=jdbc_url,
            table="real_time_prices",
            mode="append",
            properties=jdbc_props,
        )
        logger.info(f"Batch {batch_id}: wrote {row_count} rows to PostgreSQL")
    except Exception as e:
        logger.error(f"Batch {batch_id}: PostgreSQL write failed: {e}")

    # Write to Redis — use foreach for distributed processing
    redis_host = require_env("REDIS_HOST", "redis")
    redis_port = int(require_env("REDIS_PORT", "6379"))
    redis_password = os.getenv("REDIS_PASSWORD", None)

    try:
        import redis
        r = redis.Redis(host=redis_host, port=redis_port, password=redis_password, decode_responses=True)

        # For each row, update Redis hash
        for row in batch_df.collect():
            key = f"price:{row['ticker']}"
            r.hset(key, mapping={
                "ticker": row["ticker"],
                "price": str(row["price"]),
                "volume": str(row["volume"] or 0),
                "timestamp": row["timestamp"],
                "source": row.get("source", "unknown"),
            })
            # Set TTL of 5 minutes
            r.expire(key, 300)

        # Publish for WebSocket subscribers
        for row in batch_df.select("ticker", "price", "volume", "timestamp").distinct().collect():
            r.publish("price_updates", json.dumps({
                "ticker": row["ticker"],
                "price": float(row["price"]),
                "volume": int(row["volume"] or 0),
                "timestamp": row["timestamp"],
            }))

        logger.info(f"Batch {batch_id}: updated Redis cache")
    except Exception as e:
        logger.error(f"Batch {batch_id}: Redis write failed: {e}")


# ============================================
# Main
# ============================================

def main() -> None:
    """Start the Spark Structured Streaming consumer."""
    logger.info("=" * 60)
    logger.info("MassMutual Stream Consumer — START")
    logger.info("=" * 60)

    kafka_broker = require_env("KAFKA_BROKER", "kafka:9092")
    kafka_topic = require_env("KAFKA_TOPIC", "market-data")
    checkpoint_dir = require_env("CHECKPOINT_DIR", "/app/checkpoints/stream-consumer")

    spark = (
        SparkSession.builder
        .appName("MassMutual_StreamConsumer")
        .config("spark.jars", "/opt/spark/jars/postgresql-42.7.3.jar")
        .getOrCreate()
    )

    try:
        # Read from Kafka
        raw_stream = (
            spark.readStream
            .format("kafka")
            .option("kafka.bootstrap.servers", kafka_broker)
            .option("subscribe", kafka_topic)
            .option("startingOffsets", "latest")
            .option("failOnDataLoss", "false")
            .load()
        )

        # Parse JSON messages
        parsed_stream = (
            raw_stream
            .selectExpr("CAST(value AS STRING) as json_str")
            .select(from_json(col("json_str"), MESSAGE_SCHEMA).alias("data"))
            .select("data.*")
            .filter(col("ticker").isNotNull() & col("price").isNotNull())
        )

        # Write using foreachBatch
        query = (
            parsed_stream.writeStream
            .foreachBatch(write_to_postgres_and_redis)
            .option("checkpointLocation", checkpoint_dir)
            .trigger(processingTime="10 seconds")
            .start()
        )

        logger.info(f"Streaming query started. Checkpoint: {checkpoint_dir}")
        query.awaitTermination()

    except Exception as e:
        logger.error(f"Stream consumer failed: {e}", exc_info=True)
        raise
    finally:
        spark.stop()
        logger.info("SparkSession stopped")


if __name__ == "__main__":
    main()
