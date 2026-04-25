# Cloud Deployment Guide

This guide explains how to host the MassMutual Financial Platform online using **free-tier** services.

## 1. Database (PostgreSQL)
Use **Supabase** or **Neon.tech** for a managed PostgreSQL instance.
- Create a new project.
- Go to Settings → Database → Connection String (URI).
- Save this as `DATABASE_URL`.

## 2. Real-Time Infrastructure (Kafka & Redis)
Use **Upstash** for serverless Kafka and Redis.
- **Kafka**: Create a cluster and a topic named `market-data`. Save the Broker URL and credentials.
- **Redis**: Create a database. Save the URL and Token.

## 3. Web Hosting (Flask Dashboard)
Deploy to **Render.com** using the included `render.yaml`.
- Connect your GitHub repository to Render.
- Render will automatically detect the blueprint and start provisioning.
- In the Render Dashboard, add the following Environment Variables:
  - `FINNHUB_API_KEY`: Your Finnhub key.
  - `GEMINI_API_KEY`: Your Google AI key.
  - `DATABASE_URL`: Your Supabase/Neon connection string.
  - `REDIS_URL`: Your Upstash Redis URL.
  - `KAFKA_BROKER`: Your Upstash Kafka Broker.

## 4. Automated Pipeline (GitHub Actions)
The project includes a workflow in `.github/workflows/market_pipeline.yml`.
- Go to your GitHub Repo → Settings → Secrets and variables → Actions.
- Add the following **Secrets**:
  - `DATABASE_URL`
  - `FINNHUB_API_KEY`
  - `UPSTASH_KAFKA_BROKER`
  - `UPSTASH_KAFKA_USER`
  - `UPSTASH_KAFKA_PASS`
  - `UPSTASH_REDIS_URL`
  - `UPSTASH_REDIS_TOKEN`

The pipeline will now run automatically:
- **Market Data**: Every 30 minutes during market hours.
- **Crypto Data**: Every 2 hours, 24/7.

---

## Troubleshooting Cloud Deployment
- **Cold Starts**: Render's free tier "sleeps" after 15 minutes of inactivity. The first load might take ~30 seconds.
- **DB Connections**: If using Supabase, ensure you use the **Connection Pooling** (Port 6543) if you experience connection timeouts.
- **Upstash Limits**: Monitor your Upstash console; the free tier allows 10k messages/day.
