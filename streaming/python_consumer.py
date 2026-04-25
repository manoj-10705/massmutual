import os
import json
import logging
import redis
import psycopg2
from kafka import KafkaConsumer

# Configuration
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("PythonConsumer")

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "market-data")
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "massmutual_redis")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
DB_NAME = os.getenv("APP_DB_NAME", "massmutual")
DB_USER = os.getenv("APP_DB_USER", "massmutual")
DB_PASS = os.getenv("APP_DB_PASSWORD", "massmutual123")

def main():
    logger.info("Starting Python Market Data Consumer...")
    
    # Initialize Redis
    r = redis.Redis(host=REDIS_HOST, port=6379, password=REDIS_PASSWORD, decode_responses=True)
    
    # Initialize Postgres
    conn = psycopg2.connect(host=POSTGRES_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS)
    conn.autocommit = True
    cur = conn.cursor()
    
    # Initialize Kafka
    consumer = KafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=[KAFKA_BROKER],
        value_deserializer=lambda m: json.loads(m.decode('utf-8')),
        auto_offset_reset='latest'
    )
    
    logger.info(f"Connected to Kafka: {KAFKA_BROKER}, Topic: {KAFKA_TOPIC}")

    for message in consumer:
        data = message.value
        ticker = data.get("ticker")
        price = data.get("price")
        volume = data.get("volume", 0)
        timestamp = data.get("timestamp")
        
        if not ticker or price is None:
            continue
            
        logger.info(f"Processing: {ticker} @ {price}")
        
        # 1. Update Redis Cache
        key = f"price:{ticker}"
        r.hset(key, mapping={
            "ticker": ticker,
            "price": str(price),
            "volume": str(volume),
            "timestamp": timestamp
        })
        r.expire(key, 300)
        
        # 2. Publish to Redis for UI
        r.publish("price_updates", json.dumps({
            "ticker": ticker,
            "price": float(price),
            "volume": int(volume),
            "timestamp": timestamp
        }))
        
        # 3. Store in Postgres real_time_prices
        try:
            cur.execute("""
                INSERT INTO real_time_prices (ticker, timestamp, open, high, low, close, volume)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (ticker, timestamp, price, price, price, price, volume))

            # 4. Simple Anomaly Detection (Price Jump > 5%)
            last_price = r.get(f"last_price:{ticker}")
            if last_price:
                diff = abs(float(price) - float(last_price)) / float(last_price)
                if diff > 0.05:
                    logger.warning(f"ANOMALY DETECTED: {ticker} moved {diff:.2%}")
                    cur.execute("""
                        INSERT INTO anomaly_alerts (ticker, alert_type, severity, message, metric_value, threshold, detected_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (ticker, 'Price Spike', 'critical', f"Price moved {diff:.2%} in one tick", price, 0.05, timestamp))
            
            r.set(f"last_price:{ticker}", str(price), ex=300)

        except Exception as e:
            logger.error(f"Postgres insert failed: {e}")

if __name__ == "__main__":
    main()
