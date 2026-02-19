# Weather Data Pipeline - Stockton, CA

An end-to-end data pipeline system that collects, transforms, and visualizes weather data for Stockton, California. The pipeline fetches data from the National Weather Service (NWS) API, stores it in MongoDB, transforms and aggregates it in ClickHouse, caches results in Redis, and displays them on a web dashboard.

## Architecture Overview

```
NWS API → MongoDB → ClickHouse → Redis → Dashboard
```

### Pipeline Flow

1. **API → MongoDB**: Fetches weather data from NWS API and stores raw + enriched data
2. **MongoDB → ClickHouse**: Extracts observations, transforms to structured format, computes daily/monthly aggregates
3. **ClickHouse → Redis**: Caches aggregated results for fast dashboard access
4. **Redis → Dashboard**: Serves cached data to web interface with real-time visualizations

## Components

### ETL Scripts

- **`nws_api_fetcher_v2.py`**: Fetches weather data from National Weather Service API
  - Gets grid point information for Stockton coordinates
  - Retrieves forecasts, hourly forecasts, and station observations
  - Handles historical observations (last 7 days - NWS limitation)

- **`mongodb_etl.py`**: MongoDB ETL operations
  - Stores raw API responses in `raw_weather` collection
  - Enriches data with calculated metrics (averages, totals)
  - Stores enriched data in `enriched_weather` collection

- **`clickhouse_etl.py`**: ClickHouse ETL operations
  - Extracts observations from MongoDB
  - Transforms JSON documents to structured rows
  - Computes daily and monthly aggregates
  - Handles duplicate observations by aggregating hourly first

- **`redis_etl.py`**: Redis caching operations
  - Caches monthly averages (last 12 months)
  - Caches daily averages (last 30 days)
  - Implements TTL-based cache expiration (1 hour)

- **`dashboard.py`**: Flask web application
  - Serves interactive dashboard with Plotly charts
  - Displays daily temperature trends and monthly rainfall
  - Auto-refreshes every 5 minutes
  - Provides manual sync functionality

### Supporting Files

- **`config.py`**: Centralized configuration for all connections and settings
- **`run_pipeline.py`**: One-time full pipeline execution script
- **`scheduler.py`**: Automated scheduling for periodic syncs
- **`test_connections.py`**: Utility to test all database connections
- **`view_clickhouse_data.py`**: Utility to view ClickHouse data
- **`view_data.py`**: Utility to view Redis cached data
- **`fix_humidity_data.py`**: Data cleanup utility for aggregate tables

## Prerequisites

- Python 3.8+ (tested with Python 3.13)
- MongoDB Atlas account (or local MongoDB instance)
- ClickHouse server (local or remote)
- Redis server (local or remote)

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Database Connections

Edit `config.py` with your database credentials:

```python
# MongoDB connection
MONGODB_URI = "your_mongodb_connection_string"

# ClickHouse connection
CLICKHOUSE_HOST = "localhost"
CLICKHOUSE_PORT = 9000
CLICKHOUSE_DB = "weather_warehouse"
CLICKHOUSE_USER = "default"
CLICKHOUSE_PASSWORD = ""

# Redis connection
REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB = 0
```

### 3. Start Required Services

**ClickHouse:**
```bash
# macOS (Homebrew)
brew services start clickhouse

# Or using Docker
docker run -d -p 9000:9000 -p 8123:8123 clickhouse/clickhouse-server
```

**Redis:**
```bash
# macOS (Homebrew)
brew services start redis

# Or using Docker
docker run -d -p 6379:6379 redis:latest
```

### 4. Test Connections

```bash
python3 test_connections.py
```

This will verify connections to:
- MongoDB
- ClickHouse
- Redis
- NWS API

## Running the Project

### Option 1: Run Full Pipeline Once

```bash
python3 run_pipeline.py
```

This executes:
1. Fetch data from NWS API → MongoDB
2. Sync MongoDB → ClickHouse
3. Sync ClickHouse → Redis

### Option 2: Start Automated Scheduler

```bash
python3 scheduler.py
```

This runs the pipeline automatically at configured intervals:
- API → MongoDB: Every 30 minutes
- MongoDB → ClickHouse: Every 60 minutes
- ClickHouse → Redis: Every 30 minutes

### Option 3: Start Web Dashboard

```bash
python3 dashboard.py
```

Then open your browser to: `http://127.0.0.1:5000`

The dashboard displays:
- Average temperature, total rainfall, average humidity
- Daily temperature chart (last 90 days)
- Monthly rainfall chart (last 12 months)

## Component Descriptions

### MongoDB (Data Lake)
- **Purpose**: Stores raw and enriched weather data
- **Collections**:
  - `raw_weather`: Raw API responses with full metadata
  - `enriched_weather`: Enriched data with calculated metrics
- **Schema**: Document-based, flexible JSON structure

### ClickHouse (Data Warehouse)
- **Purpose**: Analytical queries and aggregations
- **Tables**:
  - `weather_observations`: Individual observations with timestamps
  - `daily_weather_aggregates`: Daily aggregated metrics
  - `monthly_weather_aggregates`: Monthly aggregated metrics
- **Engine**: MergeTree for observations, SummingMergeTree for aggregates

### Redis (Cache Layer)
- **Purpose**: Fast access to aggregated results for dashboard
- **Keys**:
  - `weather:stockton:monthly_averages`: Monthly data (TTL: 1 hour)
  - `weather:stockton:daily_averages`: Daily data (TTL: 1 hour)
- **Strategy**: Cache-aside pattern with TTL expiration

### Dashboard (Visualization)
- **Framework**: Flask with Plotly.js
- **Features**:
  - Real-time data visualization
  - Auto-refresh every 5 minutes
  - Manual sync button
  - Dark theme with modern UI
  - Temperature in Fahrenheit
  - Daily temperature points on chart

## Data Flow Details

### 1. API → MongoDB
- Fetches weather data from NWS API
- Stores raw response with metadata (timestamp, API request ID, ETL batch ID)
- Enriches data by calculating:
  - Average temperature (converted from Kelvin to Celsius)
  - Total/avg rainfall (converted from meters to millimeters)
  - Average humidity percentage

### 2. MongoDB → ClickHouse
- Extracts observations from enriched MongoDB documents
- Parses NWS API structure (properties.temperature.value, etc.)
- Handles duplicate observations by:
  - Grouping by hour first
  - Taking max rainfall per hour (to avoid double-counting)
  - Summing hourly values for daily totals
- Creates structured rows with proper data types

### 3. ClickHouse → Redis
- Queries aggregated data from ClickHouse
- Calculates overall averages across time periods
- Stores JSON in Redis with TTL for cache expiration
- Includes metadata (cache timestamp, data version)

### 4. Redis → Dashboard
- Retrieves cached data from Redis
- Falls back to ClickHouse if cache expired
- Renders interactive charts with Plotly
- Converts temperatures from Celsius to Fahrenheit for display

## Known Issues and Limitations

### 1. NWS API Historical Data Limitation
- **Issue**: NWS API only provides weather observations for the last ~7 days
- **Impact**: Limited historical data availability
- **Workaround**: Pipeline accumulates data over time as it runs periodically

### 2. Duplicate Observations
- **Issue**: Multiple observations may exist for the same timestamp
- **Impact**: Can cause inflated totals if not handled correctly
- **Solution**: Aggregation logic groups by hour first, then sums hourly values

### 3. Rainfall Data Accuracy
- **Issue**: `precipitationLastHour` field represents hourly precipitation, not cumulative
- **Impact**: Summing all observations can overcount rainfall
- **Solution**: Uses max per hour, then sums hourly values to get daily totals
- **Note**: Final totals may still differ from official sources due to API limitations

### 4. MongoDB SSL Certificate
- **Issue**: MongoDB Atlas may have SSL certificate verification issues
- **Solution**: Uses `tlsAllowInvalidCertificates=True` for development (not recommended for production)

### 5. ClickHouse SummingMergeTree
- **Issue**: SummingMergeTree engine sums numeric values on duplicate keys
- **Impact**: Re-inserting aggregates can cause values to be summed incorrectly
- **Solution**: DELETE old aggregates before inserting new ones, or query directly from source

### 6. Humidity Values
- **Issue**: Humidity values were being summed instead of averaged
- **Solution**: Fixed aggregation logic to properly average humidity values
- **Safety**: Added cap at 100% to prevent invalid values

### 7. Temperature Conversion
- **Note**: NWS API returns temperatures in Kelvin for some fields, Celsius for others
- **Solution**: Automatic conversion logic detects and converts Kelvin to Celsius
- **Display**: Dashboard converts Celsius to Fahrenheit for user display

## Troubleshooting

### Connection Issues

**MongoDB:**
```bash
# Test connection
python3 -c "from mongodb_etl import MongoDBETL; m = MongoDBETL(); print('Connected!')"
```

**ClickHouse:**
```bash
# Test connection
python3 -c "from clickhouse_etl import ClickHouseETL; c = ClickHouseETL(); print('Connected!')"
```

**Redis:**
```bash
# Test connection
python3 -c "from redis_etl import RedisETL; r = RedisETL(); print('Connected!')"
```

### Data Issues

**Clear and Recompute Aggregates:**
```bash
python3 fix_humidity_data.py
```

**View ClickHouse Data:**
```bash
python3 view_clickhouse_data.py
```

**View Redis Cache:**
```bash
python3 view_data.py
```

## File Structure

```
Project2_DBMS/
├── nws_api_fetcher_v2.py      # NWS API data fetcher
├── mongodb_etl.py              # MongoDB ETL operations
├── clickhouse_etl.py          # ClickHouse ETL operations
├── redis_etl.py               # Redis caching operations
├── dashboard.py               # Flask web dashboard
├── config.py                 # Configuration settings
├── run_pipeline.py           # One-time pipeline execution
├── scheduler.py              # Automated scheduling
├── test_connections.py       # Connection testing utility
├── view_clickhouse_data.py   # ClickHouse data viewer
├── view_data.py              # Redis data viewer
├── fix_humidity_data.py      # Data cleanup utility
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

## Configuration

All configuration is centralized in `config.py`:

- **Location**: Stockton, CA coordinates
- **Sync Intervals**: Configurable sync intervals for each pipeline stage
- **Database Connections**: MongoDB, ClickHouse, Redis settings
- **Dashboard**: Host and port configuration
- **API Settings**: NWS API base URL and user agent

## License

This project is for educational purposes as part of a database management systems course.

## Contact

For issues or questions, please refer to the project documentation or contact the development team.

