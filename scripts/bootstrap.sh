#!/usr/bin/env bash
# ============================================
# MassMutual Financial Pipeline — Bootstrap
# ============================================
# Usage:
#   chmod +x scripts/bootstrap.sh
#   ./scripts/bootstrap.sh
#
# This script initializes the complete pipeline stack.

set -euo pipefail

echo "🚀 MassMutual Financial Pipeline — Bootstrap"
echo "=============================================="

# Check prerequisites
command -v docker >/dev/null 2>&1 || { echo "❌ Docker is required but not installed."; exit 1; }
command -v docker compose >/dev/null 2>&1 || command -v docker-compose >/dev/null 2>&1 || { echo "❌ Docker Compose is required but not installed."; exit 1; }

# Check .env exists
if [ ! -f .env ]; then
    echo "📋 Creating .env from .env.example..."
    cp .env.example .env
    echo "⚠️  Please edit .env and set your API keys before continuing."
    echo "   Required: FINNHUB_API_KEY, GEMINI_API_KEY"
    exit 1
fi

# Step 1: Start databases first
echo ""
echo "1️⃣  Starting databases (postgres, postgres-airflow, redis)..."
docker compose up -d postgres postgres-airflow redis
echo "   Waiting 15s for databases to initialize..."
sleep 15

# Step 2: Start Kafka
echo "2️⃣  Starting Kafka..."
docker compose up -d kafka
echo "   Waiting 20s for Kafka to be ready..."
sleep 20

# Step 3: Start Spark cluster
echo "3️⃣  Starting Spark cluster..."
docker compose up -d spark-master spark-worker

# Step 4: Start remaining services
echo "4️⃣  Starting Airflow, Market Producer, and Frontend..."
docker compose up -d airflow market-producer frontend

# Step 5: Verify
echo ""
echo "5️⃣  Checking service health..."
sleep 10
docker compose ps

echo ""
echo "=============================================="
echo "✅ All services started!"
echo ""
echo "📊 Dashboard:    http://localhost:5000"
echo "🔧 Airflow UI:   http://localhost:8080"
echo "⚡ Spark UI:     http://localhost:8081"
echo "=============================================="
