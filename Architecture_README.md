# Weather Data Pipeline - Architecture Overview

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         NWS API (External)                          │
│                    National Weather Service                         │
└──────────────────────────────┬──────────────────────────────────────┘
                                │
                                │ HTTP/JSON
                                │ [Full/Partial Sync]
                                │ Metadata: source_timestamp, api_request_id
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         ETL Pipeline                                 │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  MongoDB (Data Lake)                                         │  │
│  │  ┌────────────────────┐  ┌────────────────────┐            │  │
│  │  │ raw_observations   │  │enriched_observations│            │  │
│  │  └────────────────────┘  └────────────────────┘            │  │
│  │                                                               │  │
│  │  Sync: Full/Partial (every 30 min)                          │  │
│  │  Metadata Added:                                             │  │
│  │    • etl_batch_id                                            │  │
│  │    • ingest_time_utc                                        │  │
│  │    • sync_type (full/partial)                              │  │
│  │    • transform_status                                       │  │
│  │    • metadata.team_name                                     │  │
│  └───────────────────────┬──────────────────────────────────────┘  │
│                          │                                          │
│                          │ Incremental Sync (every 60 min)          │
│                          │ Metadata Passed:                         │
│                          │   • source_timestamp                    │
│                          │   • api_request_id                      │
│                          │   • etl_batch_id                       │
│                          │   • ingest_time_utc                    │
│                          │ Metadata Added:                          │
│                          │   • warehouse_load_time                 │
│                          ▼                                          │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  ClickHouse (Data Warehouse)                                  │  │
│  │  ┌────────────────────┐  ┌────────────────────┐               │  │
│  │  │weather_observations│  │daily/monthly_agg  │               │  │
│  │  └────────────────────┘  └────────────────────┘               │  │
│  │                                                               │  │
│  │  Sync: Incremental Load                                      │  │
│  │  Aggregates: Daily & Monthly                                 │  │
│  └───────────────────────┬──────────────────────────────────────┘  │
│                          │                                          │
│                          │ Full Refresh (every 30 min)              │
│                          │ Metadata Added:                          │
│                          │   • cache_timestamp                      │
│                          │   • data_version                         │
│                          ▼                                          │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Redis (Cache Layer)                                          │  │
│  │  ┌────────────────────┐  ┌────────────────────┐               │  │
│  │  │monthly_averages    │  │daily_averages      │               │  │
│  │  └────────────────────┘  └────────────────────┘               │  │
│  │                                                               │  │
│  │  Sync: Full Refresh (TTL: 3600s)                             │  │
│  │  Cache Keys:                                                  │  │
│  │    • weather:stockton:monthly_averages                        │  │
│  │    • weather:stockton:daily_averages                         │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                          │                                          │
│                          │                                          │
│                          │                                          │
└──────────────────────────┼──────────────────────────────────────────┘
                           │
                           │ Data Retrieval (Cache-Aside Pattern)
                           │ Priority: Redis → ClickHouse → MongoDB
                           │
                           ▼
                ┌──────────────────────────────┐
                │   Dashboard (Flask Web App)   │
                │                               │
                │  • Reads from Redis (primary) │
                │  • Falls back to ClickHouse   │
                │  • Displays aggregated data   │
                └──────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                    Sync Types & Metadata Flow                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  API → MongoDB:                                                      │
│    • Full Sync: Initial load, manual sync                           │
│    • Partial Sync: Automated scheduler (every 30 min)               │
│    • Metadata: source_timestamp, api_request_id, etl_batch_id       │
│                                                                       │
│  MongoDB → ClickHouse:                                               │
│    • Incremental Sync: Only new data (every 60 min)                  │
│    • Metadata: All MongoDB metadata + warehouse_load_time           │
│                                                                       │
│  ClickHouse → Redis:                                                 │
│    • Full Refresh: Complete cache replacement (every 30 min)         │
│    • Metadata: cache_timestamp, data_version                         │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

## Component Architecture

### 1. Data Ingestion Layer

**Component**: `nws_api_fetcher_v2.py`

**Responsibilities**:
- Fetches weather data from National Weather Service API
- Handles API authentication and rate limiting
- Retrieves multiple data types:
  - Grid point information
  - Forecast data (7-day)
  - Hourly forecasts
  - Station observations
  - Historical observations (last 7 days)

**Technology**: Python `requests` library

**Data Format**: GeoJSON from NWS API

**Output**: Raw JSON documents with metadata

---

### 2. Data Lake (MongoDB)

**Component**: `mongodb_etl.py`

**Storage**:
- **Collection**: `raw_weather`
  - Stores complete API responses
  - Preserves original data structure
  - Includes metadata: timestamps, API request IDs, ETL batch IDs

- **Collection**: `enriched_weather`
  - Stores processed and enriched data
  - Calculated metrics: averages, totals
  - Additional metadata: ingest time, transform status

**Schema**: Document-based (NoSQL)
```json
{
  "source_timestamp": "2025-11-30T18:00:00Z",
  "api_request_id": "req_1234567890",
  "etl_batch_id": "batch_1234567890",
  "location": {
    "city": "Stockton",
    "state": "CA",
    "latitude": 37.9577,
    "longitude": -121.2908
  },
  "observations": [...],
  "calculated_metrics": {
    "avg_temperature_c": 10.5,
    "total_rainfall_mm": 5.2,
    "avg_humidity_percent": 65.0
  }
}
```

**Technology**: MongoDB Atlas (Cloud) or Local MongoDB

**Purpose**: 
- Data lake for raw data preservation
- Flexible schema for varying API responses
- Historical data retention

---

### 3. Data Warehouse (ClickHouse)

**Component**: `clickhouse_etl.py`

**Storage**:

#### Table: `weather_observations`
- **Engine**: MergeTree
- **Purpose**: Store individual observations
- **Schema**:
  ```sql
  observation_id String
  station_id String
  timestamp DateTime
  temperature_c Nullable(Float64)
  rainfall_mm Nullable(Float64)
  humidity_percent Nullable(Float64)
  wind_speed_ms Nullable(Float64)
  pressure_pa Nullable(Float64)
  ingest_time_utc DateTime
  source_timestamp DateTime
  api_request_id String
  etl_batch_id String
  ```

#### Table: `daily_weather_aggregates`
- **Engine**: SummingMergeTree
- **Purpose**: Daily aggregated metrics
- **Schema**:
  ```sql
  date Date
  avg_temperature_c Nullable(Float64)
  total_rainfall_mm Nullable(Float64)
  avg_humidity_percent Nullable(Float64)
  max_temperature_c Nullable(Float64)
  min_temperature_c Nullable(Float64)
  observation_count UInt32
  warehouse_load_time DateTime
  ```

#### Table: `monthly_weather_aggregates`
- **Engine**: SummingMergeTree
- **Purpose**: Monthly aggregated metrics
- **Schema**:
  ```sql
  year UInt16
  month UInt8
  avg_temperature_c Nullable(Float64)
  total_rainfall_mm Nullable(Float64)
  avg_humidity_percent Nullable(Float64)
  max_temperature_c Nullable(Float64)
  min_temperature_c Nullable(Float64)
  observation_count UInt32
  warehouse_load_time DateTime
  ```

**Technology**: ClickHouse (Columnar Database)

**Purpose**:
- Fast analytical queries
- Time-series data optimization
- Aggregation performance
- OLAP workloads

**Key Features**:
- Columnar storage for efficient aggregations
- MergeTree engines for time-series data
- Automatic data compression

---

### 4. Cache Layer (Redis)

**Component**: `redis_etl.py`

**Storage**:

#### Key: `weather:stockton:monthly_averages`
- **Type**: String (JSON)
- **TTL**: 3600 seconds (1 hour)
- **Content**: Monthly aggregated data for last 12 months

#### Key: `weather:stockton:daily_averages`
- **Type**: String (JSON)
- **TTL**: 3600 seconds (1 hour)
- **Content**: Daily aggregated data for last 30 days

**Technology**: Redis (In-Memory Data Store)

**Purpose**:
- Fast data retrieval for dashboard
- Reduces load on ClickHouse
- Cache-aside pattern implementation

**Cache Strategy**:
- TTL-based expiration
- Automatic refresh on sync
- Fallback to ClickHouse if cache miss

---

### 5. Presentation Layer (Dashboard)

**Component**: `dashboard.py`

**Technology Stack**:
- **Backend**: Flask (Python web framework)
- **Frontend**: HTML, CSS, JavaScript
- **Visualization**: Plotly.js
- **Styling**: Custom dark theme with glassmorphism

**Features**:
- Real-time data visualization
- Interactive charts (zoom, pan, hover)
- Auto-refresh every 5 minutes
- Manual sync functionality
- Responsive design

**Endpoints**:
- `GET /`: Main dashboard page
- `GET /api/data`: JSON API for dashboard data
- `POST /api/sync`: Trigger manual data sync

**Data Flow**:
1. Dashboard requests data from `/api/data`
2. API checks Redis cache first
3. If cache miss, queries ClickHouse directly
4. Returns JSON response with monthly/daily data
5. Frontend renders charts using Plotly.js

---

## Data Flow Architecture

### ETL Pipeline Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    ETL Pipeline Stages                       │
└─────────────────────────────────────────────────────────────┘

Stage 1: API → MongoDB
├── Fetch data from NWS API
├── Store raw response in raw_weather collection
├── Enrich data with calculated metrics
└── Store enriched data in enriched_weather collection

Stage 2: MongoDB → ClickHouse
├── Extract observations from MongoDB
├── Parse NWS API JSON structure
├── Transform to structured rows
├── Handle duplicates (hourly aggregation)
├── Insert into weather_observations table
├── Compute daily aggregates
└── Compute monthly aggregates

Stage 3: ClickHouse → Redis
├── Query monthly averages (last 12 months)
├── Query daily averages (last 30 days)
├── Calculate overall statistics
├── Serialize to JSON
└── Store in Redis with TTL

Stage 4: Redis → Dashboard
├── Retrieve cached data from Redis
├── Fallback to ClickHouse if cache expired
├── Convert temperatures (Celsius → Fahrenheit)
└── Return JSON response to frontend
```

### Detailed Data Transformation

#### 1. API Response → MongoDB Document
```
NWS API GeoJSON
    ↓
Parse properties.temperature.value (Kelvin)
    ↓
Convert to Celsius
    ↓
Extract precipitationLastHour (meters)
    ↓
Convert to millimeters
    ↓
Calculate averages/totals
    ↓
MongoDB Document with metadata
```

#### 2. MongoDB Document → ClickHouse Row
```
MongoDB JSON Document
    ↓
Extract observations array
    ↓
Parse each observation:
  - timestamp → DateTime
  - temperature (Kelvin) → Celsius
  - precipitationLastHour (meters) → millimeters
  - relativeHumidity → percentage
    ↓
Create structured row
    ↓
Insert into weather_observations
```

#### 3. Observations → Aggregates
```
Individual Observations
    ↓
Group by hour (toDate, toStartOfHour)
    ↓
Take max(rainfall) per hour (avoid duplicates)
    ↓
Group by day
    ↓
Sum hourly rainfall → daily total
    ↓
Group by month
    ↓
Sum daily rainfall → monthly total
    ↓
Store in aggregate tables
```

---

## Sync Types: Full vs Partial vs Incremental

The pipeline uses different sync strategies at each stage to optimize performance and data freshness:

### API → MongoDB Sync

**Sync Types**:
- **Full Sync** (`sync_type: "full"`):
  - Used in one-time pipeline execution (`run_pipeline.py`)
  - Fetches complete current weather data from NWS API
  - Stores both raw and enriched data
  - Marks data with `sync_type: "full"` for tracking

- **Partial Sync** (`sync_type: "partial"`):
  - Used in automated scheduler (`scheduler.py`)
  - Fetches only recent/current weather data
  - More efficient for periodic updates
  - Runs every 30 minutes (configurable)

**Location**: `mongodb_etl.py::sync_from_api()`

**Behavior**:
- Both sync types perform the same operation (fetch current data)
- The distinction is mainly for metadata tracking
- All data is appended to collections (no deletion)

---

### MongoDB → ClickHouse Sync

**Sync Type**: **Incremental** (`load_mode: "incremental"`)

**Location**: `clickhouse_etl.py::sync_from_mongodb()`

**Behavior**:
- Extracts all observations from MongoDB enriched collection
- Inserts new observations into `weather_observations` table
- Does NOT truncate existing data (incremental load)
- Recomputes daily and monthly aggregates from all observations
- Runs every 60 minutes (configurable)

**Aggregation Strategy**:
- Deletes old aggregates for dates/periods being updated
- Inserts new aggregates to prevent double-counting in SummingMergeTree
- Ensures data accuracy while maintaining performance

**Alternative Mode**: `load_mode: "overwrite"` (not used in scheduler)
- Would truncate `weather_observations` table
- Useful for complete data refresh

---

### ClickHouse → Redis Sync

**Sync Type**: **Full Refresh**

**Location**: `redis_etl.py::sync_from_clickhouse()`

**Behavior**:
- Queries fresh data directly from ClickHouse
- Completely replaces existing cache entries
- Caches monthly averages (last 12 months)
- Caches daily averages (last 30 days)
- Sets TTL to 3600 seconds (1 hour)
- Runs every 30 minutes (configurable)

**Cache Keys**:
- `weather:stockton:monthly_averages`: Full refresh on each sync
- `weather:stockton:daily_averages`: Full refresh on each sync

**Why Full Refresh?**:
- Ensures cache always has latest aggregated data
- TTL provides safety net if sync fails
- Simple implementation (no complex cache invalidation)

---

### Sync Schedule Summary

```
┌─────────────────────────────────────────────────────────┐
│              Automated Sync Schedule                     │
└─────────────────────────────────────────────────────────┘

Every 30 minutes:
├── API → MongoDB (Partial Sync)
└── ClickHouse → Redis (Full Refresh)

Every 60 minutes:
└── MongoDB → ClickHouse (Incremental Load)
```

---

## Metadata Flow Between Layers

Metadata is tracked throughout the pipeline to enable data lineage, debugging, and audit trails. Here's how metadata moves between each layer:

### Metadata Fields

1. **`source_timestamp`**: Original API request timestamp (UTC)
2. **`api_request_id`**: Unique identifier for each API request
3. **`etl_batch_id`**: Unique identifier for each ETL batch
4. **`ingest_time_utc`**: When data was ingested into MongoDB
5. **`warehouse_load_time`**: When data was loaded into ClickHouse
6. **`cache_timestamp`**: When data was cached in Redis
7. **`sync_type`**: Type of sync (full/partial)
8. **`load_mode`**: Load mode (incremental/overwrite)
9. **`transform_status`**: Data transformation status

---

### Metadata Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Metadata Flow                             │
└─────────────────────────────────────────────────────────────┘

Stage 1: API → MongoDB
├── Created at API Fetch:
│   ├── source_timestamp: Current UTC time
│   └── api_request_id: "req_{timestamp_ms}"
│
├── Created at MongoDB Sync:
│   └── etl_batch_id: "batch_{timestamp_ms}"
│
└── Stored in MongoDB:
    ├── raw_weather collection:
    │   ├── source_timestamp ✓
    │   ├── api_request_id ✓
    │   ├── etl_batch_id ✓
    │   └── sync_type ✓
    │
    └── enriched_weather collection:
        ├── source_timestamp ✓ (copied)
        ├── api_request_id ✓ (copied)
        ├── etl_batch_id ✓ (copied)
        ├── ingest_time_utc ✓ (new: enrichment time)
        ├── sync_type ✓ (copied)
        └── transform_status: "enriched" ✓ (new)

Stage 2: MongoDB → ClickHouse
├── Extracted from MongoDB:
│   ├── source_timestamp → source_timestamp
│   ├── api_request_id → api_request_id
│   ├── etl_batch_id → etl_batch_id
│   └── ingest_time_utc → ingest_time_utc
│
└── Stored in ClickHouse:
    ├── weather_observations table:
    │   ├── source_timestamp ✓
    │   ├── api_request_id ✓
    │   ├── etl_batch_id ✓
    │   └── ingest_time_utc ✓
    │
    ├── daily_weather_aggregates table:
    │   └── warehouse_load_time ✓ (new: aggregation time)
    │
    └── monthly_weather_aggregates table:
        └── warehouse_load_time ✓ (new: aggregation time)

Stage 3: ClickHouse → Redis
├── Queried from ClickHouse:
│   └── (No metadata fields queried, only aggregated values)
│
└── Stored in Redis:
    ├── weather:stockton:monthly_averages:
    │   ├── cache_timestamp ✓ (new: cache time)
    │   ├── data_version ✓ (new: "v{timestamp}")
    │   └── refresh_interval_sec ✓ (new: TTL value)
    │
    └── weather:stockton:daily_averages:
        ├── cache_timestamp ✓ (new: cache time)
        ├── data_version ✓ (new: "v{timestamp}")
        └── refresh_interval_sec ✓ (new: TTL value)

Stage 4: Redis → Dashboard
└── Retrieved from Redis:
    └── All metadata fields available in JSON response
```

---

### Detailed Metadata Tracking

#### 1. API Layer (NWS API Fetcher)

**Created Metadata**:
```python
source_timestamp = datetime.utcnow().isoformat() + "Z"
api_request_id = f"req_{int(time.time() * 1000)}"
```

**Purpose**: Track when and how data was fetched from external API

---

#### 2. MongoDB Layer (Data Lake)

**Created Metadata**:
```python
etl_batch_id = f"batch_{int(datetime.utcnow().timestamp() * 1000)}"
ingest_time_utc = datetime.utcnow().isoformat() + "Z"
sync_type = "full" | "partial"
transform_status = "enriched"
```

**Stored Metadata**:
- All API metadata (source_timestamp, api_request_id)
- ETL batch ID for grouping related operations
- Ingest time for data freshness tracking
- Sync type for understanding data source

**Purpose**: 
- Data lineage tracking
- Audit trail
- Debugging data issues
- Understanding data freshness

---

#### 3. ClickHouse Layer (Data Warehouse)

**Preserved Metadata**:
- `source_timestamp`: Original API fetch time
- `api_request_id`: Original API request identifier
- `etl_batch_id`: MongoDB ETL batch identifier
- `ingest_time_utc`: MongoDB ingestion time

**Created Metadata**:
```python
warehouse_load_time = datetime.utcnow()
```

**Stored Locations**:
- **weather_observations**: All metadata fields preserved per observation
- **daily_weather_aggregates**: Only `warehouse_load_time` (aggregation time)
- **monthly_weather_aggregates**: Only `warehouse_load_time` (aggregation time)

**Purpose**:
- Trace observations back to source
- Understand when data was processed
- Debug aggregation issues
- Data quality monitoring

---

#### 4. Redis Layer (Cache)

**Created Metadata**:
```python
cache_timestamp = datetime.utcnow().isoformat() + "Z"
data_version = f"v{int(datetime.utcnow().timestamp())}"
refresh_interval_sec = 3600  # TTL value
```

**Stored Metadata**:
- Cache timestamp for freshness checks
- Data version for cache invalidation
- Refresh interval for TTL management

**Purpose**:
- Cache freshness validation
- Dashboard sync status display
- Cache hit/miss optimization

---

### Metadata Usage Examples

#### Data Lineage Query
```sql
-- ClickHouse: Find all observations from a specific API request
SELECT * FROM weather_observations 
WHERE api_request_id = 'req_1234567890';
```

#### Audit Trail
```python
# MongoDB: Find all data from a specific ETL batch
db.enriched_weather.find({"etl_batch_id": "batch_1234567890"})
```

#### Cache Freshness Check
```python
# Redis: Check if cache is fresh
cache_data = redis.get("weather:stockton:monthly_averages")
cache_timestamp = cache_data['cache_timestamp']
# Compare with current time to determine freshness
```

#### Dashboard Sync Status
```javascript
// Dashboard: Display sync status based on cache freshness
if (cache_timestamp && (now - cache_timestamp) < 3600) {
    sync_status = 'full';  // Cache is fresh
} else {
    sync_status = 'partial';  // Cache expired, using ClickHouse
}
```

---

### Metadata Best Practices

1. **Preservation**: Metadata is preserved through all layers to maintain data lineage
2. **Timestamps**: All timestamps use UTC for consistency
3. **Unique IDs**: Each operation has unique identifiers for traceability
4. **Versioning**: Cache uses version numbers for invalidation strategies
5. **TTL Management**: Redis metadata includes TTL information for cache management

---

## Technology Stack

### Backend
- **Python 3.8+**: Core programming language
- **Flask 3.0.0**: Web framework for dashboard
- **requests 2.31.0**: HTTP client for API calls
- **pymongo 4.6.1**: MongoDB driver
- **clickhouse-driver >=0.2.10**: ClickHouse client
- **redis 5.0.1**: Redis client
- **schedule 1.2.0**: Task scheduling

### Databases
- **MongoDB**: Document database (Data Lake)
- **ClickHouse**: Columnar database (Data Warehouse)
- **Redis**: In-memory cache

### Frontend
- **HTML5/CSS3**: Structure and styling
- **JavaScript (ES6+)**: Client-side logic
- **Plotly.js**: Interactive data visualization

### External Services
- **NWS API**: National Weather Service REST API
  - Base URL: `https://api.weather.gov`
  - Format: GeoJSON
  - Rate Limiting: Built-in delays

---

## Design Patterns

### 1. ETL Pattern
- **Extract**: Fetch from NWS API
- **Transform**: Parse, convert units, calculate metrics
- **Load**: Store in appropriate storage layer

### 2. Cache-Aside Pattern
- Application checks cache first
- On cache miss, queries data source
- Updates cache with fetched data
- TTL ensures freshness

### 3. Lambda Architecture (Simplified)
- **Batch Layer**: MongoDB (raw data storage)
- **Speed Layer**: Redis (real-time cache)
- **Serving Layer**: ClickHouse (analytical queries)

### 4. Layered Architecture
```
┌─────────────────┐
│  Presentation   │  Dashboard
├─────────────────┤
│   Application   │  ETL Scripts
├─────────────────┤
│     Storage     │  MongoDB, ClickHouse, Redis
└─────────────────┘
```

---

## Scalability Considerations

### Horizontal Scaling
- **MongoDB**: Sharding support for large datasets
- **ClickHouse**: Distributed tables and clusters
- **Redis**: Redis Cluster for high availability
- **Dashboard**: Multiple Flask instances behind load balancer

### Vertical Scaling
- **ClickHouse**: Optimized for single-node performance
- **Redis**: In-memory performance scales with RAM
- **MongoDB**: Replica sets for read scaling

### Performance Optimizations
- **ClickHouse**: Columnar storage for fast aggregations
- **Redis**: In-memory caching reduces database load
- **Indexing**: ClickHouse primary keys optimized for time-series
- **Batch Processing**: Aggregates computed in batches

---

## Data Quality & Reliability

### Data Validation
- Temperature range checks (Kelvin conversion)
- Humidity capping (0-100%)
- Null value handling (Nullable columns)
- Duplicate detection and handling

### Error Handling
- API rate limiting with retries
- Connection retry logic
- Graceful degradation (fallback to ClickHouse if Redis fails)
- Error logging and monitoring

### Data Consistency
- Transactional inserts where possible
- Idempotent operations
- DELETE before INSERT for aggregates (prevents double-counting)

---

## Security Considerations

### API Security
- User-Agent header for NWS API
- Rate limiting compliance
- HTTPS for all API calls

### Database Security
- MongoDB: Connection string authentication
- ClickHouse: User/password authentication
- Redis: Network isolation (localhost by default)

### Development vs Production
- SSL certificate bypass for development (MongoDB)
- Should use proper SSL in production
- Environment-based configuration

---

## Monitoring & Observability

### Metrics to Track
- API request success rate
- ETL job execution time
- Cache hit/miss ratio
- Database query performance
- Dashboard response time

### Logging
- ETL batch IDs for traceability
- API request IDs
- Error messages with context
- Data quality warnings

---

## Future Enhancements

### Potential Improvements
1. **Real-time Streaming**: Kafka/Kinesis for real-time data ingestion
2. **Data Quality Framework**: Automated data validation and alerting
3. **Multi-location Support**: Extend to multiple cities
4. **Machine Learning**: Weather prediction models
5. **API Gateway**: Centralized API management
6. **Containerization**: Docker/Kubernetes deployment
7. **Monitoring Dashboard**: Grafana/Prometheus integration
8. **Automated Testing**: Unit and integration tests

---

## Architecture Decisions

### Why MongoDB for Data Lake?
- **Flexibility**: Schema-less storage for varying API responses
- **Scalability**: Horizontal scaling capabilities
- **Document Model**: Natural fit for JSON API responses

### Why ClickHouse for Warehouse?
- **Performance**: Columnar storage optimized for analytics
- **Time-Series**: Built-in support for time-based queries
- **Aggregations**: Fast GROUP BY and aggregation functions
- **Compression**: Efficient storage for large datasets

### Why Redis for Cache?
- **Speed**: In-memory performance
- **Simplicity**: Easy key-value storage
- **TTL Support**: Built-in expiration
- **Low Latency**: Sub-millisecond response times

### Why Flask for Dashboard?
- **Simplicity**: Lightweight framework
- **Python Integration**: Seamless with ETL scripts
- **Flexibility**: Easy to extend and customize

---

## Deployment Architecture

### Development Environment
```
Local Machine
├── Python Virtual Environment
├── Local ClickHouse (Docker/Homebrew)
├── Local Redis (Docker/Homebrew)
└── MongoDB Atlas (Cloud)
```

### Production Environment (Recommended)
```
Cloud Infrastructure
├── Application Server (Flask)
│   ├── ETL Scripts
│   └── Dashboard
├── MongoDB Atlas (Managed)
├── ClickHouse Cluster (Managed)
├── Redis Cluster (Managed)
└── Load Balancer
```

---

## Data Retention Policy

### MongoDB
- **Raw Data**: Retain indefinitely (data lake)
- **Enriched Data**: Retain indefinitely
- **Purpose**: Historical analysis and audit trail

### ClickHouse
- **Observations**: Retain based on storage capacity
- **Aggregates**: Retain indefinitely (smaller size)
- **Purpose**: Analytical queries and reporting

### Redis
- **Cache**: TTL-based expiration (1 hour)
- **Purpose**: Performance optimization only

---

This architecture provides a robust, scalable foundation for weather data collection, transformation, and visualization while maintaining flexibility for future enhancements.

