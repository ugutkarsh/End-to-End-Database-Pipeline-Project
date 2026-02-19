"""
Redis ETL - Caches aggregated results for fast dashboard access
"""
import redis
import json
from datetime import datetime
from typing import Dict, Optional
import config
from clickhouse_etl import ClickHouseETL

class RedisETL:
    def __init__(self):
        self.client = redis.Redis(
            host=config.REDIS_HOST,
            port=config.REDIS_PORT,
            db=config.REDIS_DB,
            decode_responses=True
        )
        self.clickhouse_etl = ClickHouseETL()
        self.ttl = config.REDIS_TTL
    
    def cache_monthly_averages(self, months: int = 12) -> Dict:
        """Cache monthly averages from ClickHouse"""
        print("Fetching monthly averages from ClickHouse...")
        monthly_data = self.clickhouse_etl.get_monthly_averages(months)
        
        if not monthly_data:
            print("No monthly data available")
            return {}
        
        # Calculate overall averages for the period
        total_temp = sum(d['avg_temperature_c'] for d in monthly_data if d['avg_temperature_c'])
        total_rainfall = sum(d['total_rainfall_mm'] for d in monthly_data if d['total_rainfall_mm'])
        humidity_values = [d['avg_humidity_percent'] for d in monthly_data if d.get('avg_humidity_percent') is not None]
        total_humidity = sum(humidity_values)
        
        count = len(monthly_data)
        humidity_count = len(humidity_values)
        overall_avg_temp = total_temp / count if count > 0 else None
        overall_total_rainfall = total_rainfall
        overall_avg_humidity = total_humidity / humidity_count if humidity_count > 0 else None
        
        cache_data = {
            'cache_timestamp': datetime.utcnow().isoformat() + "Z",
            'data_version': f"v{int(datetime.utcnow().timestamp())}",
            'refresh_interval_sec': config.REDIS_TTL,
            'location': {
                'city': 'Stockton',
                'state': 'CA'
            },
            'overall_averages': {
                'avg_temperature_c': overall_avg_temp,
                'total_rainfall_mm': overall_total_rainfall,
                'avg_humidity_percent': overall_avg_humidity,
                'period_months': count
            },
            'monthly_data': monthly_data
        }
        
        # Store in Redis with TTL
        cache_key = "weather:stockton:monthly_averages"
        self.client.setex(
            cache_key,
            self.ttl,
            json.dumps(cache_data, default=str)
        )
        
        print(f"Cached monthly averages (TTL: {self.ttl}s)")
        return cache_data
    
    def cache_daily_averages(self, days: int = 30) -> Dict:
        """Cache daily averages from ClickHouse"""
        print("Fetching daily averages from ClickHouse...")
        
        query = f"""
            SELECT 
                date,
                avg_temperature_c,
                total_rainfall_mm,
                avg_humidity_percent
            FROM daily_weather_aggregates
            ORDER BY date DESC
            LIMIT {days}
        """
        
        results = self.clickhouse_etl.client.execute(query)
        
        daily_data = [
            {
                'date': row[0].isoformat() if hasattr(row[0], 'isoformat') else str(row[0]),
                'avg_temperature_c': row[1],
                'total_rainfall_mm': row[2],
                'avg_humidity_percent': row[3]
            }
            for row in results
        ]
        
        cache_data = {
            'cache_timestamp': datetime.utcnow().isoformat() + "Z",
            'data_version': f"v{int(datetime.utcnow().timestamp())}",
            'refresh_interval_sec': config.REDIS_TTL,
            'location': {
                'city': 'Stockton',
                'state': 'CA'
            },
            'daily_data': daily_data
        }
        
        cache_key = "weather:stockton:daily_averages"
        self.client.setex(
            cache_key,
            self.ttl,
            json.dumps(cache_data, default=str)
        )
        
        print(f"Cached daily averages (TTL: {self.ttl}s)")
        return cache_data
    
    def get_cached_data(self, key: str = "weather:stockton:monthly_averages") -> Optional[Dict]:
        """Retrieve cached data from Redis"""
        cached = self.client.get(key)
        if cached:
            return json.loads(cached)
        return None
    
    def sync_from_clickhouse(self) -> Dict:
        """Sync aggregated data from ClickHouse to Redis"""
        print("Starting Redis sync from ClickHouse...")
        
        monthly_cache = self.cache_monthly_averages(12)
        daily_cache = self.cache_daily_averages(30)
        
        print("Redis sync completed")
        return {
            'monthly_cached': bool(monthly_cache),
            'daily_cached': bool(daily_cache),
            'cache_timestamp': datetime.utcnow().isoformat() + "Z"
        }
    
    def check_cache_status(self) -> Dict:
        """Check cache status and freshness"""
        monthly_key = "weather:stockton:monthly_averages"
        daily_key = "weather:stockton:daily_averages"
        
        monthly_ttl = self.client.ttl(monthly_key)
        daily_ttl = self.client.ttl(daily_key)
        
        monthly_data = self.get_cached_data(monthly_key)
        daily_data = self.get_cached_data(daily_key)
        
        return {
            'monthly_cache': {
                'exists': monthly_data is not None,
                'ttl_seconds': monthly_ttl,
                'fresh': monthly_ttl > 0,
                'data_version': monthly_data.get('data_version') if monthly_data else None
            },
            'daily_cache': {
                'exists': daily_data is not None,
                'ttl_seconds': daily_ttl,
                'fresh': daily_ttl > 0,
                'data_version': daily_data.get('data_version') if daily_data else None
            }
        }

