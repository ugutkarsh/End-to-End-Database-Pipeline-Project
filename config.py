"""
Configuration file for the weather data pipeline
Loads configuration from environment variables for security
"""
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Stockton, CA coordinates
STOCKTON_LAT = 37.9577
STOCKTON_LON = -121.2908

# MongoDB connection - SECURE: Uses environment variables
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
MONGODB_DB = os.getenv("MONGODB_DB", "Project2")
MONGODB_COLLECTION_RAW = os.getenv("MONGODB_COLLECTION_RAW", "raw_observations")
MONGODB_COLLECTION_ENRICHED = os.getenv("MONGODB_COLLECTION_ENRICHED", "enriched_observations")

# ClickHouse connection
CLICKHOUSE_HOST = os.getenv("CLICKHOUSE_HOST", "localhost")
CLICKHOUSE_PORT = int(os.getenv("CLICKHOUSE_PORT", "9000"))
CLICKHOUSE_DB = os.getenv("CLICKHOUSE_DB", "weather_warehouse")
CLICKHOUSE_USER = os.getenv("CLICKHOUSE_USER", "default")
CLICKHOUSE_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD", "default")

# Redis connection
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_TTL = int(os.getenv("REDIS_TTL", "3600"))  # 1 hour in seconds

# NWS API
NWS_API_BASE = os.getenv("NWS_API_BASE", "https://api.weather.gov")
NWS_USER_AGENT = os.getenv("NWS_USER_AGENT", "StocktonWeatherPipeline/1.0 (contact@example.com)")

# Sync intervals (in minutes)
SYNC_INTERVAL_API_TO_MONGODB = int(os.getenv("SYNC_INTERVAL_API_TO_MONGODB", "30"))
SYNC_INTERVAL_MONGODB_TO_CLICKHOUSE = int(os.getenv("SYNC_INTERVAL_MONGODB_TO_CLICKHOUSE", "60"))
SYNC_INTERVAL_CLICKHOUSE_TO_REDIS = int(os.getenv("SYNC_INTERVAL_CLICKHOUSE_TO_REDIS", "30"))

# Dashboard
DASHBOARD_HOST = os.getenv("DASHBOARD_HOST", "127.0.0.1")
DASHBOARD_PORT = int(os.getenv("DASHBOARD_PORT", "5001"))

