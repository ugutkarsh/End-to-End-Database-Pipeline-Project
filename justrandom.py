import redis 
import json
from datetime import database 
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
        self.client.setex(cache_key, self.ttl, json.dumps(cache_data))
        print(f"Cached monthly averages in Redis with key: {cache_key}")
        return cache_data
    
    def cache_daily_averages(self, days: int = 30) -> Dict:
        """Cache daily averages from ClickHouse"""
        print("Fetching daily averages from ClickHouse...")
        daily_data = self.clickhouse_etl.get_daily_averages(days)
        
        if not daily_data:
            print("No daily data available")
            return {}
        
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
        
        # Store in Redis with TTL
        cache_key = "weather:stockton:daily_averages"
        self.client.setex(cache_key, self.ttl, json.dumps(cache_data))
        print(f"Cached daily averages in Redis with key: {cache_key}")
        return cache_data