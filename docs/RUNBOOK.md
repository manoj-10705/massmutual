# Operational Runbook

> Quick reference for operating, monitoring, and troubleshooting the MassMutual Financial Pipeline.

---

## Service Health Checks

| Service | Health Check | Expected |
|---|---|---|
| Frontend API | `curl http://localhost:5000/health` | `{"status": "healthy"}` |
| Frontend Ready | `curl http://localhost:5000/ready` | `{"status": "ready", "checks": {...}}` |
| PostgreSQL | `docker exec mm_postgres pg_isready` | `accepting connections` |
| Redis | `docker exec mm_redis redis-cli -a $REDIS_PASSWORD ping` | `PONG` |
| Kafka | `docker exec mm_kafka kafka-topics.sh --bootstrap-server localhost:9092 --list` | Lists topics |
| Airflow | `curl http://localhost:8080/health` | `{"status": "healthy"}` |

## Common Operations

### Restart a Single Service

```bash
docker compose restart frontend    # Restart API + dashboard
docker compose restart market-producer  # Restart streaming
```

### View Service Logs

```bash
docker compose logs -f frontend --tail 50
docker compose logs -f market-producer --tail 50
docker compose logs -f airflow --tail 50
```

### Manually Trigger ETL Pipeline

1. Open Airflow UI: http://localhost:8080
2. Navigate to `financial_data_pipeline` DAG
3. Click "Trigger DAG" (play button)
4. Monitor task progress in Graph view

### Scale Spark Workers

```bash
# Remove container_name from docker-compose.yml first
docker compose up -d --scale spark-worker=3
```

### Database Maintenance

```bash
# Connect to application database
docker exec -it mm_postgres psql -U massmutual -d massmutual

# Check table sizes
SELECT relname, pg_size_pretty(pg_relation_size(relid))
FROM pg_stat_user_tables ORDER BY pg_relation_size(relid) DESC;

# Run data retention cleanup
DELETE FROM real_time_prices WHERE created_at < NOW() - INTERVAL '90 days';
DELETE FROM ai_query_log WHERE created_at < NOW() - INTERVAL '1 year';
VACUUM ANALYZE;
```

### Redis Cache Management

```bash
# Connect to Redis
docker exec -it mm_redis redis-cli -a massmutual_redis

# Check cache contents
KEYS price:*
HGETALL price:1155.KL

# Clear all cache
FLUSHDB
```

## Incident Response

### Pipeline Data is Stale

1. Check Airflow DAG status: http://localhost:8080
2. If DAG is paused → unpause it
3. If last run failed → check task logs, re-trigger
4. Verify Spark master is running: `docker compose ps spark-master`

### Real-Time Prices Stopped

1. Check producer: `docker compose logs market-producer --tail 20`
2. If Finnhub key expired → rotate key in `.env`, restart
3. If Kafka down → `docker compose restart kafka`, wait 30s
4. If simulation mode → verify `FINNHUB_API_KEY` in `.env`

### AI Analyst Returns Errors

1. Check API key: `curl http://localhost:5000/ready` → verify `ai_analyst` status
2. If "not configured" → set `GEMINI_API_KEY` in `.env`
3. If rate limited → wait 60 seconds (Gemini free tier: 15 RPM)
4. Check query log: `SELECT * FROM ai_query_log ORDER BY created_at DESC LIMIT 5;`

### High Memory Usage

1. Check container stats: `docker stats`
2. Spark worker using >1.5GB → normal under load
3. Redis >256MB → check maxmemory policy: `INFO memory`
4. PostgreSQL >512MB → run `VACUUM FULL` on large tables

## Backup & Recovery

### Database Backup

```bash
docker exec mm_postgres pg_dump -U massmutual massmutual > backup_$(date +%Y%m%d).sql
```

### Database Restore

```bash
docker exec -i mm_postgres psql -U massmutual massmutual < backup_20240105.sql
```

## Contact

For production incidents, escalate to the team lead.
