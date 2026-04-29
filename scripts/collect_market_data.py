import os
import json
import logging
from datetime import datetime, timezone

import requests
import psycopg2

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CollectMarketData")

# Env vars
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")
POSTGRES_HOST = os.getenv("DATABASE_URL")  # Render uses DATABASE_URL
TICKERS = os.getenv("TICKERS", "1155.KL").split(",")

def fetch_finnhub_quote(ticker):
    # If ticker contains prefix, remove for Finnhub if needed. But Finnhub format usually takes it.
    url = f"https://finnhub.io/api/v1/quote?symbol={ticker}&token={FINNHUB_API_KEY}"
    resp = requests.get(url)
    if resp.status_code == 200:
        return resp.json()
    logger.error(f"Failed to fetch {ticker}: {resp.status_code} {resp.text}")
    return None

def main():
    if not POSTGRES_HOST:
        logger.error("No DATABASE_URL configured.")
        return
        
    try:
        conn = psycopg2.connect(POSTGRES_HOST)
        conn.autocommit = True
        cur = conn.cursor()
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        return

    # Use redis if configured
    r = None
    if os.getenv("UPSTASH_REDIS_URL"):
        try:
            import redis
            r = redis.from_url(os.getenv("UPSTASH_REDIS_URL"))
        except Exception:
            pass

    for ticker in TICKERS:
        ticker = ticker.strip()
        data = fetch_finnhub_quote(ticker)
        if not data:
            continue
            
        # Finnhub quote format: c=current price, h=high, l=low, o=open, pc=previous close
        price = data.get("c")
        timestamp = datetime.now(timezone.utc).isoformat()
        
        if price:
            logger.info(f"Writing {ticker} @ {price}")
            
            try:
                cur.execute("""
                    INSERT INTO real_time_prices (ticker, timestamp, open, high, low, close, volume)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (ticker, timestamp, data.get("o", price), data.get("h", price), data.get("l", price), price, 0))
            except Exception as e:
                logger.error(f"DB Error: {e}")
                
            if r:
                key = f"price:{ticker}"
                try:
                    r.hset(key, mapping={
                        "ticker": ticker,
                        "price": str(price),
                        "volume": "0",
                        "timestamp": timestamp
                    })
                    r.expire(key, 300)
                    r.publish("price_updates", json.dumps({
                        "ticker": ticker,
                        "price": float(price),
                        "volume": 0,
                        "timestamp": timestamp
                    }))
                except Exception as e:
                    logger.error(f"Redis error: {e}")

if __name__ == "__main__":
    main()
