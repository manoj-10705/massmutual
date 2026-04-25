#!/bin/bash
set -e

# Wait for Postgres to be ready
echo "Waiting for PostgreSQL (Airflow Meta)..."
while ! nc -z postgres-airflow 5432; do
  sleep 1
done
echo "PostgreSQL is up!"

# Initialize the database
echo "Running database migrations..."
airflow db migrate

# Create admin user
echo "Checking for admin user..."
airflow users create \
    --username admin \
    --password admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@massmutual.local || echo "User might already exist, skipping..."

# Run scheduler and webserver
echo "Starting Airflow webserver and scheduler..."
airflow scheduler &
exec airflow webserver
