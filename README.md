# MassMutual Financial Intelligence Platform

[![Market Pipeline](https://github.com/manoj-10705/massmutual/actions/workflows/market_pipeline.yml/badge.svg)](https://github.com/manoj-10705/massmutual/actions)
![Python 3.12](https://img.shields.io/badge/python-3.12-blue)
![Docker](https://img.shields.io/badge/docker-compose-2496ED)
![Hosting: Render](https://img.shields.io/badge/hosting-Render-4353ff)

A professional, real-time financial intelligence dashboard for market analysis (Maybank 1155.KL & Crypto). Features a high-performance streaming pipeline, statistical anomaly detection, and a Gemini-powered AI analyst.

---

## ✨ Core Features

- 🕯️ **Advanced Financial Charts** — TradingView-style interactive candlestick and volatility charts with smart date clamping (prevents vanishing candles).
- 🤖 **AI Financial Analyst** — Natural language interface to query the database. Ask "What was the average return in 2023?" and get instant insights + charts.
- 📡 **Real-Time Streaming** — Live price updates via Finnhub WebSocket → Kafka → Python Stream Consumer → Redis & PostgreSQL.
- ⚡ **Instant Anomaly Detection** — Real-time monitoring of price spikes (>5%) with automated dashboard alerts.
- ☁️ **Cloud Native** — Ready for free-tier hosting on Render, Supabase (Postgres), and Upstash (Redis/Kafka).
- ⚙️ **Automated Data Ops** — Scheduled data collection and analytics via GitHub Actions cron jobs.

---

## 🛠️ Technology Stack

- **Broker/Cache**: Apache Kafka, Redis
- **Processing**: Apache Spark, Python (Stream Consumer)
- **Orchestration**: GitHub Actions, Apache Airflow
- **AI**: Google Gemini Pro 1.5
- **Frontend**: Lightweight Charts, Chart.js, Vanilla CSS (Glassmorphism)
- **Database**: PostgreSQL (Star Schema)

---

## 🚀 Quick Start (Local)

1. **Clone & Configure**:
   ```bash
   git clone https://github.com/manoj-10705/massmutual.git
   cd massmutual
   cp .env.example .env
   # Add your FINNHUB_API_KEY and GEMINI_API_KEY to .env
   ```

2. **Launch Infrastructure**:
   ```bash
   docker compose up -d
   ```

3. **Access Dashboard**:
   Open [http://localhost:5000](http://localhost:5000)

---

## ☁️ Cloud Deployment

This project is optimized for **free-tier** hosting:
- **Render.com**: Web Service (Flask Dashboard)
- **Supabase**: Managed PostgreSQL
- **Upstash**: Serverless Kafka & Redis
- **GitHub Actions**: Automated Data Pipeline

See [docs/CLOUD_DEPLOYMENT.md](docs/CLOUD_DEPLOYMENT.md) for a step-by-step guide.

---

## 📁 Project Structure

```text
├── .github/workflows/    # CI/CD & Scheduled Data Pipeline
├── airflow/              # Batch Orchestration (Local)
├── db/                   # Schema & Table Migrations
├── docs/                 # Detailed Documentation
├── frontend/             # Flask API & Glassmorphism Dashboard
├── spark/                # Spark Processing Jobs
├── streaming/            # Real-time Ingestion & Consumer
├── render.yaml           # One-click Render Deployment
└── docker-compose.yml    # Full-stack Container Config
```

---

## 🔒 Security & Privacy

Credentials and secrets are managed via `.env` files and GitHub Secrets. Never commit your `.env` file. See [SECURITY.md](SECURITY.md) for more info.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
