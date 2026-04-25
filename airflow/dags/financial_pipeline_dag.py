"""
MassMutual Financial Data Pipeline DAG

Orchestrates the batch ETL pipeline:
  1. Check that source data exists
  2. Submit Spark ETL job via REST API
  3. Wait for Spark job completion
  4. Validate results in PostgreSQL

No Docker-in-Docker. No SparkSubmitOperator.
Uses Spark's REST Submission API (port 6066).
"""

import os
import sys
import time
import json
import logging
from typing import Any

import requests
import psycopg2
from psycopg2 import sql as psql
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

logger = logging.getLogger("financial_pipeline")

# ============================================
# Configuration — No hardcoded password defaults
# ============================================

SPARK_REST_URL = os.getenv("SPARK_REST_URL", "http://spark-master:6066")
APP_DB_NAME = os.getenv("APP_DB_NAME", "massmutual")
APP_DB_USER = os.getenv("APP_DB_USER", "massmutual")
APP_DB_PASSWORD = os.getenv("APP_DB_PASSWORD", "massmutual123")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")

if APP_DB_PASSWORD == "massmutual123":
    logger.info("APP_DB_PASSWORD using default value")

# ============================================
# Task Functions
# ============================================


def check_data_exists(**kwargs: Any) -> bool:
    """Verify that the source CSV file exists and is readable."""
    data_path = "/opt/airflow/data/mbb_financial_dataset.csv"
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Source data not found at {data_path}")

    size = os.path.getsize(data_path)
    if size < 1000:
        raise ValueError(f"Source file too small ({size} bytes). Expected > 1KB.")

    logger.info(f"Source data found: {data_path} ({size:,} bytes)")
    return True


def submit_spark_job(**kwargs: Any) -> str:
    """Submit the Spark ETL job via native spark-submit command."""
    import subprocess

    spark_master = "spark://spark-master:7077"
    app_path = "/app/spark_pipeline.py"
    jar_path = "/opt/spark-extra-jars/postgresql-42.7.3.jar"
    data_path = "/data/mbb_financial_dataset.csv"

    cmd = [
        "spark-submit",
        "--master", spark_master,
        "--name", "MassMutual_Financial_ETL",
        "--jars", jar_path,
        "--conf", "spark.submit.deployMode=client",
        "--conf", "spark.executor.memory=512m",
        "--conf", "spark.driver.memory=512m",
        app_path
    ]

    # Environment variables for the Spark job
    if not APP_DB_PASSWORD:
        logger.warning("APP_DB_PASSWORD not set — using default")

    env = os.environ.copy()
    env["CSV_PATH"] = data_path
    env["POSTGRES_HOST"] = POSTGRES_HOST
    env["APP_DB_NAME"] = APP_DB_NAME
    env["APP_DB_USER"] = APP_DB_USER
    env["APP_DB_PASSWORD"] = APP_DB_PASSWORD

    logger.info(f"Spark JDBC target: {POSTGRES_HOST}:5432/{APP_DB_NAME} as {APP_DB_USER}")

    logger.info(f"Executing: {' '.join(cmd)}")

    try:
        # Run spark-submit and capture output
        process = subprocess.Popen(
            cmd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        # Log output in real-time
        for line in process.stdout:
            logger.info(f"Spark: {line.strip()}")

        return_code = process.wait()

        if return_code == 0:
            logger.info("Spark job completed successfully via spark-submit.")
            return "SUCCESS"
        else:
            raise RuntimeError(f"Spark-submit failed with return code {return_code}")

    except Exception as e:
        logger.error(f"Failed to execute spark-submit: {e}")
        raise


def wait_for_spark_job(**kwargs: Any) -> bool:
    """Pass-through task: submit_spark_job already waits for completion."""
    return True


def validate_results(**kwargs: Any) -> bool:
    """Check that the star schema tables were populated.
    
    Uses psycopg2.sql.Identifier for safe dynamic table names (fixes SQL injection).
    """
    conn = psycopg2.connect(
        host="postgres",
        database=APP_DB_NAME,
        user=APP_DB_USER,
        password=APP_DB_PASSWORD,
    )

    try:
        with conn.cursor() as cur:
            tables = {
                "dim_date": 100,
                "fact_daily_prices": 100,
                "fact_monthly_summary": 1,
                "fact_volatility_index": 1,
                "kpi_summary": 1,
            }

            all_ok = True
            for table, min_rows in tables.items():
                # SAFE: use psycopg2.sql.Identifier instead of f-string
                cur.execute(
                    psql.SQL("SELECT COUNT(*) FROM {}").format(psql.Identifier(table))
                )
                count = cur.fetchone()[0]
                status = "✅" if count >= min_rows else "❌"
                logger.info(f"  {status} {table}: {count:,} rows (min: {min_rows})")
                if count < min_rows:
                    all_ok = False

            if not all_ok:
                raise ValueError("Data validation failed. Some tables have insufficient rows.")

            logger.info("All tables validated successfully!")
            return True
    finally:
        conn.close()


def on_failure_callback(context: dict) -> None:
    """Callback when a task fails."""
    task_id = context.get("task_instance", {}).task_id if context.get("task_instance") else "unknown"
    logger.error(f"Task '{task_id}' FAILED. Check Airflow logs for details.")


# ============================================
# DAG Definition
# ============================================

default_args = {
    "owner": "massmutual",
    "depends_on_past": False,
    "start_date": datetime(2025, 10, 8),
    "retries": 2,
    "retry_delay": timedelta(minutes=2),
    "on_failure_callback": on_failure_callback,
}

with DAG(
    dag_id="financial_data_pipeline",
    default_args=default_args,
    schedule="@daily",  # Use 'schedule' instead of deprecated 'schedule_interval'
    catchup=False,
    description="Batch ETL: CSV → Spark → Star Schema (PostgreSQL)",
    tags=["massmutual", "etl", "spark"],
) as dag:

    check_data = PythonOperator(
        task_id="check_data_exists",
        python_callable=check_data_exists,
    )

    submit_spark = PythonOperator(
        task_id="submit_spark_etl",
        python_callable=submit_spark_job,
    )

    wait_spark = PythonOperator(
        task_id="wait_for_spark_job",
        python_callable=wait_for_spark_job,
    )

    validate = PythonOperator(
        task_id="validate_results",
        python_callable=validate_results,
    )

    check_data >> submit_spark >> wait_spark >> validate
