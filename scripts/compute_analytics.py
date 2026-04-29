import os
import logging
import psycopg2

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ComputeAnalytics")

POSTGRES_HOST = os.getenv("DATABASE_URL")

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

    logger.info("Computing analytics...")
    
    try:
        # Simple analytic: Delete old real time prices
        cur.execute("DELETE FROM real_time_prices WHERE created_at < NOW() - INTERVAL '7 days'")
        logger.info("Cleaned up old real time prices.")
    except Exception as e:
        logger.error(f"Error computing analytics: {e}")

if __name__ == "__main__":
    main()
