"""
Scheduler - Automates sync intervals across the pipeline
"""
import schedule
import time
from datetime import datetime
from mongodb_etl import MongoDBETL
from clickhouse_etl import ClickHouseETL
from redis_etl import RedisETL
import config

class PipelineScheduler:
    def __init__(self):
        self.mongodb_etl = MongoDBETL()
        self.clickhouse_etl = ClickHouseETL()
        self.redis_etl = RedisETL()
    
    def sync_api_to_mongodb(self):
        """Sync from API to MongoDB"""
        print(f"\n[{datetime.now()}] Starting API -> MongoDB sync...")
        try:
            self.mongodb_etl.sync_from_api("partial")
            print(f"[{datetime.now()}] API -> MongoDB sync completed")
        except Exception as e:
            print(f"[{datetime.now()}] Error in API -> MongoDB sync: {e}")
    
    def sync_mongodb_to_clickhouse(self):
        """Sync from MongoDB to ClickHouse"""
        print(f"\n[{datetime.now()}] Starting MongoDB -> ClickHouse sync...")
        try:
            self.clickhouse_etl.sync_from_mongodb("incremental")
            print(f"[{datetime.now()}] MongoDB -> ClickHouse sync completed")
        except Exception as e:
            print(f"[{datetime.now()}] Error in MongoDB -> ClickHouse sync: {e}")
    
    def sync_clickhouse_to_redis(self):
        """Sync from ClickHouse to Redis"""
        print(f"\n[{datetime.now()}] Starting ClickHouse -> Redis sync...")
        try:
            self.redis_etl.sync_from_clickhouse()
            print(f"[{datetime.now()}] ClickHouse -> Redis sync completed")
        except Exception as e:
            print(f"[{datetime.now()}] Error in ClickHouse -> Redis sync: {e}")
    
    def start(self):
        """Start the scheduler"""
        print("=" * 60)
        print("Weather Data Pipeline Scheduler")
        print("=" * 60)
        print(f"API -> MongoDB: Every {config.SYNC_INTERVAL_API_TO_MONGODB} minutes")
        print(f"MongoDB -> ClickHouse: Every {config.SYNC_INTERVAL_MONGODB_TO_CLICKHOUSE} minutes")
        print(f"ClickHouse -> Redis: Every {config.SYNC_INTERVAL_CLICKHOUSE_TO_REDIS} minutes")
        print("=" * 60)
        print("Scheduler started. Press Ctrl+C to stop.")
        print()
        
        # Schedule jobs
        schedule.every(config.SYNC_INTERVAL_API_TO_MONGODB).minutes.do(self.sync_api_to_mongodb)
        schedule.every(config.SYNC_INTERVAL_MONGODB_TO_CLICKHOUSE).minutes.do(self.sync_mongodb_to_clickhouse)
        schedule.every(config.SYNC_INTERVAL_CLICKHOUSE_TO_REDIS).minutes.do(self.sync_clickhouse_to_redis)
        
        # Run initial sync
        print(f"[{datetime.now()}] Running initial sync...")
        self.sync_api_to_mongodb()
        time.sleep(5)
        self.sync_mongodb_to_clickhouse()
        time.sleep(5)
        self.sync_clickhouse_to_redis()
        
        # Keep running
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute

if __name__ == '__main__':
    scheduler = PipelineScheduler()
    try:
        scheduler.start()
    except KeyboardInterrupt:
        print("\n\nScheduler stopped by user")

