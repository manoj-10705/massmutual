"""
MassMutual Batch ETL Pipeline — Spark

Reads financial CSV data, transforms into star schema dimensions and facts,
and loads into PostgreSQL with idempotent upsert semantics.

Tables written:
  - dim_date            (dimension)
  - dim_stock           (dimension)
  - fact_daily_prices   (fact)
  - fact_monthly_summary (fact)
  - fact_volatility_index (fact)
  - kpi_summary         (aggregate)
"""

import os
import sys
import logging
from typing import Optional

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import (
    col, year, month, dayofmonth, date_format, quarter, avg, sum as spark_sum,
    stddev, count, when, lit, round as spark_round, row_number, lag,
)
from pyspark.sql.window import Window
from pyspark.sql.types import (
    StructType, StructField, StringType, DoubleType, LongType, DateType,
)

# ============================================
# Configuration
# ============================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("SparkETL")


def require_env(name: str, default: Optional[str] = None) -> str:
    """Get required environment variable or fail fast."""
    value = os.getenv(name, default)
    if value is None:
        logger.critical(f"Required env var '{name}' is not set.")
        sys.exit(1)
    return value


# ============================================
# Schema
# ============================================

CSV_SCHEMA = StructType([
    StructField("Date", DateType(), False),
    StructField("Open", DoubleType(), True),
    StructField("High", DoubleType(), True),
    StructField("Low", DoubleType(), True),
    StructField("Close", DoubleType(), True),
    StructField("Adj Close", DoubleType(), True),
    StructField("Volume", LongType(), True),
    StructField("GDP (constant 2015 MYR)", DoubleType(), True),
    StructField("GDP Growth YOY (%)", DoubleType(), True),
    StructField("Inflation Rate (%)", DoubleType(), True),
    StructField("OPR (%)", DoubleType(), True),
])


# ============================================
# ETL Functions
# ============================================

def create_spark_session() -> SparkSession:
    """Create and configure SparkSession."""
    import glob

    # Find the PostgreSQL JDBC jar in multiple possible locations
    jar_paths = [
        "/opt/spark-extra-jars/postgresql-42.7.3.jar",
        "/opt/spark/jars/postgresql-42.7.3.jar",
    ]
    found_jars = [p for p in jar_paths if os.path.exists(p)]
    jar_config = ",".join(found_jars) if found_jars else "/opt/spark-extra-jars/postgresql-42.7.3.jar"

    return (
        SparkSession.builder
        .appName("MassMutual_ETL")
        .config("spark.jars", jar_config)
        .config("spark.sql.legacy.timeParserPolicy", "LEGACY")
        .getOrCreate()
    )


def read_and_validate(spark: SparkSession, csv_path: str) -> DataFrame:
    """Read CSV, compute derived columns, and perform data quality checks."""
    logger.info(f"Reading CSV from {csv_path}")

    raw_df = spark.read.csv(csv_path, header=True, schema=CSV_SCHEMA)
    total_rows = raw_df.count()
    logger.info(f"Loaded {total_rows} rows")

    if total_rows == 0:
        raise ValueError(f"CSV file at {csv_path} is empty")

    # Compute daily_return from Close prices (not present in CSV)
    w = Window.orderBy("Date")
    raw_df = (
        raw_df
        .withColumn("prev_close", lag("Close", 1).over(w))
        .withColumn(
            "daily_return",
            when(
                col("prev_close").isNotNull() & (col("prev_close") != 0),
                spark_round((col("Close") - col("prev_close")) / col("prev_close"), 6),
            ).otherwise(lit(0.0)),
        )
        .drop("prev_close")
    )

    # Efficient null check: single aggregation instead of N separate counts
    null_counts = raw_df.select([
        count(when(col(c).isNull(), c)).alias(c)
        for c in raw_df.columns
    ]).collect()[0]

    for col_name in raw_df.columns:
        null_count = null_counts[col_name]
        if null_count > 0:
            logger.warning(f"  Column '{col_name}': {null_count} nulls ({100 * null_count / total_rows:.1f}%)")

    return raw_df


def build_dim_date(raw_df: DataFrame) -> DataFrame:
    """Build date dimension table."""
    return (
        raw_df.select(col("Date").alias("date"))
        .distinct()
        .withColumn("date_key", date_format("date", "yyyyMMdd").cast("integer"))
        .withColumn("day", dayofmonth("date"))
        .withColumn("month", month("date"))
        .withColumn("month_name", date_format("date", "MMMM"))
        .withColumn("quarter", quarter("date"))
        .withColumn("year", year("date"))
        .withColumn("weekday", date_format("date", "EEEE"))
    )


def build_dim_stock() -> list[dict]:
    """Build stock dimension data."""
    return [{"ticker": "1155.KL", "company_name": "Maybank", "sector": "Finance", "market": "KLSE"}]


def build_fact_daily(raw_df: DataFrame) -> DataFrame:
    """Build daily prices fact table."""
    return raw_df.select(
        date_format("Date", "yyyyMMdd").cast("integer").alias("date_key"),
        lit(1).alias("stock_id"),
        col("Open").alias("open"),
        col("High").alias("high"),
        col("Low").alias("low"),
        col("Close").alias("close"),
        col("Adj Close").alias("adj_close"),
        col("Volume").alias("volume"),
        col("daily_return"),
        col("GDP (constant 2015 MYR)").alias("gdp"),
        col("Inflation Rate (%)").alias("inflation"),
    )


def build_fact_monthly(raw_df: DataFrame) -> DataFrame:
    """Build monthly summary fact table."""
    return (
        raw_df
        .withColumn("year", year("Date"))
        .withColumn("month", month("Date"))
        .groupBy("year", "month")
        .agg(
            spark_round(avg("Close"), 4).alias("avg_close"),
            spark_round(avg("daily_return"), 6).alias("avg_return"),
            spark_sum("Volume").alias("total_volume"),
            spark_round(stddev("daily_return"), 6).alias("volatility"),
        )
        .withColumn("stock_id", lit(1))
    )


def build_fact_volatility(raw_df: DataFrame) -> DataFrame:
    """Build rolling volatility fact table."""
    window_7d = Window.orderBy("Date").rowsBetween(-6, 0)
    window_30d = Window.orderBy("Date").rowsBetween(-29, 0)

    return (
        raw_df.select("Date", "daily_return")
        .withColumn("rolling_7d_vol", spark_round(stddev("daily_return").over(window_7d), 6))
        .withColumn("rolling_30d_vol", spark_round(stddev("daily_return").over(window_30d), 6))
        .select(
            date_format("Date", "yyyyMMdd").cast("integer").alias("date_key"),
            lit(1).alias("stock_id"),
            "rolling_7d_vol",
            "rolling_30d_vol",
        )
    )


def build_kpi_summary(raw_df: DataFrame) -> DataFrame:
    """Build KPI summary (unpivoted metrics per year)."""
    yearly = (
        raw_df
        .withColumn("year", year("Date"))
        .groupBy("year")
        .agg(
            spark_round(avg("Close"), 4).alias("AVG_CLOSE"),
            spark_round(avg("GDP (constant 2015 MYR)"), 4).alias("AVG_GDP"),
            spark_round(avg("Inflation Rate (%)"), 4).alias("AVG_INFLATION"),
            spark_round(avg("daily_return") * 100, 4).alias("AVG_DAILY_RETURN_PCT"),
            spark_round(stddev("daily_return"), 6).alias("YEARLY_VOLATILITY"),
            spark_sum("Volume").alias("TOTAL_VOLUME"),
        )
    )

    # Unpivot metrics to rows
    metrics = ["AVG_CLOSE", "AVG_GDP", "AVG_INFLATION", "AVG_DAILY_RETURN_PCT", "YEARLY_VOLATILITY", "TOTAL_VOLUME"]
    union_df = None

    for metric in metrics:
        metric_df = yearly.select(
            lit(metric).alias("metric"),
            col("year"),
            col(metric).cast("double").alias("value"),
        )
        union_df = metric_df if union_df is None else union_df.unionAll(metric_df)

    return union_df


def truncate_table(jdbc_url: str, jdbc_props: dict, table: str) -> None:
    """Truncate a table before loading (idempotent pattern)."""
    import psycopg2

    # Parse JDBC URL to get connection params
    # jdbc:postgresql://host:port/db
    parts = jdbc_url.replace("jdbc:postgresql://", "").split("/")
    host_port = parts[0].split(":")
    host = host_port[0]
    port = int(host_port[1]) if len(host_port) > 1 else 5432
    database = parts[1] if len(parts) > 1 else "massmutual"

    conn = psycopg2.connect(
        host=host,
        port=port,
        database=database,
        user=jdbc_props.get("user", ""),
        password=jdbc_props.get("password", ""),
    )
    try:
        with conn.cursor() as cur:
            # Use DELETE instead of TRUNCATE to avoid lock issues with FK
            from psycopg2 import sql
            cur.execute(sql.SQL("DELETE FROM {}").format(sql.Identifier(table)))
        conn.commit()
        logger.info(f"Cleared table: {table}")
    finally:
        conn.close()


def write_to_jdbc(df: DataFrame, jdbc_url: str, jdbc_props: dict, table: str) -> None:
    """Write DataFrame to PostgreSQL with idempotent pattern (truncate then append)."""
    try:
        truncate_table(jdbc_url, jdbc_props, table)
    except Exception as e:
        err_msg = str(e).lower()
        # Auth / connection errors must fail fast — never silently continue
        if any(kw in err_msg for kw in ("password", "authentication", "connection refused")):
            logger.error(f"FATAL: database connection error for {table}: {e}")
            raise
        # Table-not-found is expected on first run
        logger.warning(f"Could not clear {table} (may not exist yet): {e}")

    row_count = df.count()
    logger.info(f"Writing {row_count} rows to {table} ...")
    df.write.jdbc(url=jdbc_url, table=table, mode="append", properties=jdbc_props)
    logger.info(f"Successfully wrote {row_count} rows to {table}")


# ============================================
# Main
# ============================================

def main() -> None:
    """Run the batch ETL pipeline."""
    logger.info("=" * 60)
    logger.info("MassMutual Financial ETL Pipeline — START")
    logger.info("=" * 60)

    # Config
    jdbc_url = f"jdbc:postgresql://{require_env('POSTGRES_HOST', 'postgres')}:5432/{require_env('APP_DB_NAME', 'massmutual')}"
    jdbc_props = {
        "user": require_env("APP_DB_USER", "massmutual"),
        "password": require_env("APP_DB_PASSWORD", "massmutual123"),
        "driver": "org.postgresql.Driver",
    }
    csv_path = require_env("CSV_PATH", "/data/mbb_financial_dataset.csv")

    spark = create_spark_session()

    try:
        # Read & validate
        raw_df = read_and_validate(spark, csv_path)

        # Build dimension tables
        dim_date = build_dim_date(raw_df)
        write_to_jdbc(dim_date, jdbc_url, jdbc_props, "dim_date")

        # dim_stock is seed data — handled by DB init script, skip here

        # Build fact tables
        fact_daily = build_fact_daily(raw_df)
        write_to_jdbc(fact_daily, jdbc_url, jdbc_props, "fact_daily_prices")

        fact_monthly = build_fact_monthly(raw_df)
        write_to_jdbc(fact_monthly, jdbc_url, jdbc_props, "fact_monthly_summary")

        fact_volatility = build_fact_volatility(raw_df)
        write_to_jdbc(fact_volatility, jdbc_url, jdbc_props, "fact_volatility_index")

        # Build KPI summary
        kpi = build_kpi_summary(raw_df)
        write_to_jdbc(kpi, jdbc_url, jdbc_props, "kpi_summary")

        logger.info("=" * 60)
        logger.info("ETL Pipeline — COMPLETE")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"ETL pipeline failed: {e}", exc_info=True)
        raise
    finally:
        spark.stop()
        logger.info("SparkSession stopped")


if __name__ == "__main__":
    main()
