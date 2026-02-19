"""
Configuration file for the weather data pipeline
"""
import os
from datetime import datetime

# Stockton, CA coordinates
STOCKTON_LAT = 37.9577
STOCKTON_LON = -121.2908

# MongoDB connection
MONGODB_URI = "mongodb+srv://i40:dbms2@cluster0.lixbqmp.mongodb.net/"
MONGODB_DB = "Project2"
MONGODB_COLLECTION_RAW = "raw_observations"
MONGODB_COLLECTION_ENRICHED = "enriched_observations"

# ClickHouse connection
CLICKHOUSE_HOST = "localhost"
CLICKHOUSE_PORT = 9000
CLICKHOUSE_DB = "weather_warehouse"
CLICKHOUSE_USER = "default"
CLICKHOUSE_PASSWORD = "default"

# Redis connection
REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB = 0
REDIS_TTL = 3600  # 1 hour in seconds

# NWS API
NWS_API_BASE = "https://api.weather.gov"
NWS_USER_AGENT = "StocktonWeatherPipeline/1.0 (contact@example.com)"

# Sync intervals (in minutes)
SYNC_INTERVAL_API_TO_MONGODB = 30
SYNC_INTERVAL_MONGODB_TO_CLICKHOUSE = 60
SYNC_INTERVAL_CLICKHOUSE_TO_REDIS = 30

# Dashboard
DASHBOARD_HOST = "127.0.0.1"
DASHBOARD_PORT = 5001

