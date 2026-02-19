"""
Quick start script to run the full pipeline
"""
from mongodb_etl import MongoDBETL
from clickhouse_etl import ClickHouseETL
from redis_etl import RedisETL
import time

def main():
    print("=" * 60)
    print("Weather Data Pipeline - Full Sync")
    print("=" * 60)
    
    # Initialize ETL components
    print("\nInitializing ETL components...")
    m = MongoDBETL()
    c = ClickHouseETL()
    r = RedisETL()
    
    # Step 1: API → MongoDB
    print("\n" + "=" * 60)
    print("Step 1: Fetching data from NWS API → MongoDB")
    print("=" * 60)
    try:
        batch_id = m.sync_from_api("full")
        print(f"✓ Completed with batch ID: {batch_id}")
    except Exception as e:
        print(f"✗ Error: {e}")
        return
    
    time.sleep(2)
    
    # Step 2: MongoDB → ClickHouse
    print("\n" + "=" * 60)
    print("Step 2: Syncing MongoDB → ClickHouse")
    print("=" * 60)
    try:
        metadata = c.sync_from_mongodb("incremental")
        print(f"✓ Completed: {metadata['rows_loaded']} rows loaded")
    except Exception as e:
        print(f"✗ Error: {e}")
        return
    
    time.sleep(2)
    
    # Step 3: ClickHouse → Redis
    print("\n" + "=" * 60)
    print("Step 3: Syncing ClickHouse → Redis")
    print("=" * 60)
    try:
        cache_result = r.sync_from_clickhouse()
        print(f"✓ Completed: Monthly and daily data cached")
    except Exception as e:
        print(f"✗ Error: {e}")
        return
    
    print("\n" + "=" * 60)
    print("Pipeline Complete! ✓")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Check MongoDB Compass for raw and enriched data")
    print("2. Check ClickHouse for aggregated data")
    print("3. Check Redis for cached data")
    print("4. Start dashboard: python dashboard.py")
    print("5. Start scheduler: python scheduler.py")

if __name__ == '__main__':
    main()

