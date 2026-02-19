"""
ClickHouse ETL - Performs structured transformations and stores aggregated data
"""
from clickhouse_driver import Client
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import config
from mongodb_etl import MongoDBETL

class ClickHouseETL:
    def __init__(self):
        # First connect to default database to create our database
        temp_client = Client(
            host=config.CLICKHOUSE_HOST,
            port=config.CLICKHOUSE_PORT,
            database='default',  # Connect to default database first
            user=config.CLICKHOUSE_USER,
            password=config.CLICKHOUSE_PASSWORD
        )
        
        # Create database if not exists
        temp_client.execute(f"CREATE DATABASE IF NOT EXISTS {config.CLICKHOUSE_DB}")
        
        # Now create client connected to our database
        self.client = Client(
            host=config.CLICKHOUSE_HOST,
            port=config.CLICKHOUSE_PORT,
            database=config.CLICKHOUSE_DB,
            user=config.CLICKHOUSE_USER,
            password=config.CLICKHOUSE_PASSWORD
        )
        self.mongodb_etl = MongoDBETL()
        self._initialize_schema()
    
    def _initialize_schema(self):
        """Initialize ClickHouse database and tables"""
        # Database already created in __init__, just create tables
        # Only create tables if they don't exist (don't drop existing data)
        
        # Create raw observations table
        self.client.execute("""
            CREATE TABLE IF NOT EXISTS weather_observations (
                observation_id String,
                station_id String,
                timestamp DateTime,
                temperature_c Nullable(Float64),
                rainfall_mm Nullable(Float64),
                humidity_percent Nullable(Float64),
                wind_speed_ms Nullable(Float64),
                pressure_pa Nullable(Float64),
                ingest_time_utc DateTime,
                source_timestamp DateTime,
                api_request_id String,
                etl_batch_id String
            ) ENGINE = MergeTree()
            ORDER BY (timestamp, station_id)
        """)
        
        # Create daily aggregates table
        self.client.execute("""
            CREATE TABLE IF NOT EXISTS daily_weather_aggregates (
                date Date,
                avg_temperature_c Nullable(Float64),
                total_rainfall_mm Nullable(Float64),
                avg_humidity_percent Nullable(Float64),
                max_temperature_c Nullable(Float64),
                min_temperature_c Nullable(Float64),
                observation_count UInt32,
                warehouse_load_time DateTime,
                rows_loaded UInt32,
                sync_interval_min UInt16,
                load_mode String
            ) ENGINE = SummingMergeTree()
            ORDER BY date
        """)
        
        # Create monthly aggregates table
        self.client.execute("""
            CREATE TABLE IF NOT EXISTS monthly_weather_aggregates (
                year UInt16,
                month UInt8,
                avg_temperature_c Nullable(Float64),
                total_rainfall_mm Nullable(Float64),
                avg_humidity_percent Nullable(Float64),
                max_temperature_c Nullable(Float64),
                min_temperature_c Nullable(Float64),
                observation_count UInt32,
                warehouse_load_time DateTime,
                rows_loaded UInt32,
                sync_interval_min UInt16,
                load_mode String
            ) ENGINE = SummingMergeTree()
            ORDER BY (year, month)
        """)
        
        print("ClickHouse schema initialized")
    
    def extract_observations_from_mongodb(self) -> List[Dict]:
        """Extract observation data from MongoDB enriched collection"""
        enriched_docs = self.mongodb_etl.get_all_enriched_data()
        observations = []
        
        for doc in enriched_docs:
            # Extract from NWS API observations (new format)
            for obs in doc.get('observations', []):
                props = obs.get('properties', {})
                obs_data = self._parse_observation(props, doc)
                if obs_data:
                    observations.append(obs_data)
            
            # Extract from historical observations
            for obs in doc.get('historical_observations', []):
                props = obs.get('properties', {})
                obs_data = self._parse_observation(props, doc)
                if obs_data:
                    observations.append(obs_data)
            
            # Extract from daily aggregate format (legacy format)
            if 'date' in doc and 'max_temp_c' in doc:
                obs_data = self._parse_daily_aggregate(doc)
                if obs_data:
                    observations.append(obs_data)
        
        return observations
    
    def _parse_daily_aggregate(self, doc: Dict) -> Optional[Dict]:
        """Parse daily aggregate data from MongoDB legacy format"""
        try:
            from datetime import datetime
            date_str = doc.get('date')
            if not date_str:
                return None
            
            # Parse date (could be string or date object)
            if isinstance(date_str, str):
                try:
                    timestamp = datetime.strptime(date_str, "%Y-%m-%d")
                except:
                    timestamp = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            else:
                timestamp = datetime.combine(date_str, datetime.min.time())
            
            # Calculate average temperature from max/min
            max_temp = doc.get('max_temp_c')
            min_temp = doc.get('min_temp_c')
            avg_temp = None
            if max_temp is not None and min_temp is not None:
                avg_temp = (max_temp + min_temp) / 2
            elif max_temp is not None:
                avg_temp = max_temp
            elif min_temp is not None:
                avg_temp = min_temp
            
            return {
                'observation_id': f"daily_{doc.get('_id', 'unknown')}_{int(timestamp.timestamp())}",
                'station_id': 'stockton_aggregate',
                'timestamp': timestamp,
                'temperature_c': avg_temp,
                'rainfall_mm': doc.get('precip_mm'),
                'humidity_percent': None,  # Not available in this format
                'wind_speed_ms': None,
                'pressure_pa': None,
                'ingest_time_utc': datetime.fromisoformat(doc.get('ingest_time_utc', datetime.utcnow().isoformat()).replace('Z', '+00:00')) if isinstance(doc.get('ingest_time_utc'), str) else datetime.utcnow(),
                'source_timestamp': timestamp,
                'api_request_id': doc.get('api_request_id', ''),
                'etl_batch_id': doc.get('etl_batch_id', '')
            }
        except Exception as e:
            print(f"Error parsing daily aggregate: {e}")
            return None
    
    def _parse_openmeteo_daily(self, date_str: str, temp_max: Optional[float], 
                               temp_min: Optional[float], temp_mean: Optional[float],
                               precip: Optional[float], humidity: Optional[float],
                               doc: Dict) -> Optional[Dict]:
        """Parse Open-Meteo daily data"""
        try:
            # Parse date (format: YYYY-MM-DD)
            timestamp = datetime.strptime(date_str, "%Y-%m-%d")
            
            # Use mean temperature if available, otherwise average of max/min
            if temp_mean is not None:
                temp_c = temp_mean
            elif temp_max is not None and temp_min is not None:
                temp_c = (temp_max + temp_min) / 2
            else:
                temp_c = None
            
            return {
                'observation_id': f"openmeteo_{int(timestamp.timestamp())}",
                'station_id': 'openmeteo_stockton',
                'timestamp': timestamp,
                'temperature_c': temp_c,
                'rainfall_mm': precip,
                'humidity_percent': humidity,
                'wind_speed_ms': None,
                'pressure_pa': None,
                'ingest_time_utc': datetime.utcnow(),
                'source_timestamp': datetime.fromisoformat(doc.get('source_timestamp', '').replace('Z', '+00:00')),
                'api_request_id': doc.get('api_request_id', ''),
                'etl_batch_id': doc.get('etl_batch_id', '')
            }
        except Exception as e:
            print(f"Error parsing Open-Meteo daily data: {e}")
            return None
    
    def _parse_observation(self, props: Dict, doc: Dict) -> Optional[Dict]:
        """Parse a single observation from NWS API format"""
        try:
            timestamp_str = props.get('timestamp')
            if not timestamp_str:
                return None
            
            # Parse timestamp
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            
            # Extract temperature (convert from Kelvin if needed)
            temp = props.get('temperature', {}).get('value')
            temp_c = None
            if temp is not None:
                temp_c = temp - 273.15 if temp > 100 else temp
            
            # Extract other fields
            rainfall = props.get('precipitationLastHour', {}).get('value')
            # Convert from meters to millimeters if needed (NWS uses meters)
            if rainfall is not None and rainfall < 1:
                rainfall = rainfall * 1000  # Convert meters to mm
            
            humidity = props.get('relativeHumidity', {}).get('value')
            wind_speed = props.get('windSpeed', {}).get('value')
            # Convert wind speed from m/s if needed (NWS typically uses m/s)
            if wind_speed is not None and wind_speed < 50:  # Likely m/s, keep as is
                pass  # Already in m/s
            
            pressure = props.get('seaLevelPressure', {}).get('value')
            # Convert from Pa to Pa (NWS uses Pascals, which is what we want)
            
            station_id = props.get('station', '').split('/')[-1] if props.get('station') else None
            
            return {
                'observation_id': f"{station_id}_{int(timestamp.timestamp())}",
                'station_id': station_id or 'unknown',
                'timestamp': timestamp,
                'temperature_c': temp_c,
                'rainfall_mm': rainfall,
                'humidity_percent': humidity,
                'wind_speed_ms': wind_speed,
                'pressure_pa': pressure,
                'ingest_time_utc': datetime.utcnow(),
                'source_timestamp': datetime.fromisoformat(doc.get('source_timestamp', '').replace('Z', '+00:00')),
                'api_request_id': doc.get('api_request_id', ''),
                'etl_batch_id': doc.get('etl_batch_id', '')
            }
        except Exception as e:
            print(f"Error parsing observation: {e}")
            return None
    
    def load_observations(self, load_mode: str = "incremental") -> int:
        """Load observations into ClickHouse"""
        print("Extracting observations from MongoDB...")
        observations = self.extract_observations_from_mongodb()
        
        if not observations:
            print("No observations to load")
            return 0
        
        print(f"Loading {len(observations)} observations into ClickHouse...")
        
        # Prepare data for insertion
        data = [
            (
                obs['observation_id'],
                obs['station_id'],
                obs['timestamp'],
                obs['temperature_c'],
                obs['rainfall_mm'],
                obs['humidity_percent'],
                obs['wind_speed_ms'],
                obs['pressure_pa'],
                obs['ingest_time_utc'],
                obs['source_timestamp'],
                obs['api_request_id'],
                obs['etl_batch_id']
            )
            for obs in observations
        ]
        
        if load_mode == "overwrite":
            # Clear existing data (for full refresh)
            self.client.execute("TRUNCATE TABLE weather_observations")
        
        # Insert data
        self.client.execute(
            "INSERT INTO weather_observations VALUES",
            data
        )
        
        print(f"Loaded {len(observations)} observations")
        return len(observations)
    
    def compute_aggregates(self, sync_interval_min: int = 60) -> Dict:
        """Compute daily and monthly aggregates"""
        load_time = datetime.utcnow()
        load_mode = "incremental"
        
        # Compute daily aggregates
        # For rainfall: aggregate by hour first (max per hour) to avoid double-counting duplicate observations
        # Then sum hourly values to get daily total
        daily_query = """
            SELECT 
                date,
                avg(avg_temperature_c) as avg_temperature_c,
                sum(max_rainfall_per_hour) as total_rainfall_mm,
                avg(avg_humidity_percent) as avg_humidity_percent,
                max(max_temperature_c) as max_temperature_c,
                min(min_temperature_c) as min_temperature_c,
                sum(observation_count) as observation_count
            FROM (
                SELECT 
                    toDate(timestamp) as date,
                    toStartOfHour(timestamp) as hour,
                    avg(temperature_c) as avg_temperature_c,
                    max(rainfall_mm) as max_rainfall_per_hour,  -- Max per hour to avoid double-counting
                    avg(humidity_percent) as avg_humidity_percent,
                    max(temperature_c) as max_temperature_c,
                    min(temperature_c) as min_temperature_c,
                    count() as observation_count
                FROM weather_observations
                WHERE temperature_c IS NOT NULL
                GROUP BY date, hour
            )
            GROUP BY date
            ORDER BY date DESC
        """
        
        daily_results = self.client.execute(daily_query)
        rows_loaded_daily = len(daily_results)
        
        if daily_results:
            # Get list of dates to delete old aggregates for
            dates_to_update = [row[0] for row in daily_results]
            
            # Delete old aggregates for these dates to prevent SummingMergeTree from summing averages
            if dates_to_update:
                dates_str = ','.join([f"'{d}'" for d in dates_to_update])
                self.client.execute(f"ALTER TABLE daily_weather_aggregates DELETE WHERE date IN ({dates_str})")
            
            daily_data = [
                (
                    row[0],  # date
                    row[1],  # avg_temperature_c
                    row[2],  # total_rainfall_mm
                    row[3],  # avg_humidity_percent
                    row[4],  # max_temperature_c
                    row[5],  # min_temperature_c
                    row[6],  # observation_count
                    load_time,
                    rows_loaded_daily,
                    sync_interval_min,
                    load_mode
                )
                for row in daily_results
            ]
            
            self.client.execute(
                "INSERT INTO daily_weather_aggregates VALUES",
                daily_data
            )
        
        # Compute monthly aggregates
        # For rainfall: aggregate by hour first (max per hour), then by day, then by month to avoid double-counting
        monthly_query = """
            SELECT 
                year,
                month,
                avg(avg_temperature_c) as avg_temperature_c,
                sum(total_rainfall_mm) as total_rainfall_mm,
                avg(avg_humidity_percent) as avg_humidity_percent,
                max(max_temperature_c) as max_temperature_c,
                min(min_temperature_c) as min_temperature_c,
                sum(observation_count) as observation_count
            FROM (
                SELECT 
                    toYear(date) as year,
                    toMonth(date) as month,
                    date,
                    avg(avg_temperature_c) as avg_temperature_c,
                    sum(max_rainfall_per_hour) as total_rainfall_mm,
                    avg(avg_humidity_percent) as avg_humidity_percent,
                    max(max_temperature_c) as max_temperature_c,
                    min(min_temperature_c) as min_temperature_c,
                    sum(observation_count) as observation_count
                FROM (
                    SELECT 
                        toDate(timestamp) as date,
                        toStartOfHour(timestamp) as hour,
                        avg(temperature_c) as avg_temperature_c,
                        max(rainfall_mm) as max_rainfall_per_hour,
                        avg(humidity_percent) as avg_humidity_percent,
                        max(temperature_c) as max_temperature_c,
                        min(temperature_c) as min_temperature_c,
                        count() as observation_count
                    FROM weather_observations
                    WHERE temperature_c IS NOT NULL
                    GROUP BY date, hour
                )
                GROUP BY date
            )
            GROUP BY year, month
            ORDER BY year DESC, month DESC
        """
        
        monthly_results = self.client.execute(monthly_query)
        rows_loaded_monthly = len(monthly_results)
        
        if monthly_results:
            # Get list of year-month combinations to delete old aggregates for
            periods_to_update = [(row[0], row[1]) for row in monthly_results]
            
            # Delete old aggregates for these periods to prevent SummingMergeTree from summing averages
            if periods_to_update:
                periods_conditions = ' OR '.join([f"(year = {y} AND month = {m})" for y, m in periods_to_update])
                self.client.execute(f"ALTER TABLE monthly_weather_aggregates DELETE WHERE {periods_conditions}")
            
            monthly_data = [
                (
                    row[0],  # year
                    row[1],  # month
                    row[2],  # avg_temperature_c
                    row[3],  # total_rainfall_mm
                    row[4],  # avg_humidity_percent
                    row[5],  # max_temperature_c
                    row[6],  # min_temperature_c
                    row[7],  # observation_count
                    load_time,
                    rows_loaded_monthly,
                    sync_interval_min,
                    load_mode
                )
                for row in monthly_results
            ]
            
            self.client.execute(
                "INSERT INTO monthly_weather_aggregates VALUES",
                monthly_data
            )
        
        print(f"Computed aggregates: {rows_loaded_daily} daily, {rows_loaded_monthly} monthly")
        
        return {
            'warehouse_load_time': load_time.isoformat(),
            'rows_loaded_daily': rows_loaded_daily,
            'rows_loaded_monthly': rows_loaded_monthly,
            'sync_interval_min': sync_interval_min,
            'load_mode': load_mode
        }
    
    def sync_from_mongodb(self, load_mode: str = "incremental") -> Dict:
        """Full sync from MongoDB to ClickHouse"""
        print("Starting ClickHouse sync from MongoDB...")
        
        # Load observations
        rows_loaded = self.load_observations(load_mode)
        
        # Compute aggregates
        aggregate_metadata = self.compute_aggregates(config.SYNC_INTERVAL_MONGODB_TO_CLICKHOUSE)
        aggregate_metadata['rows_loaded'] = rows_loaded
        
        print("ClickHouse sync completed")
        return aggregate_metadata
    
    def get_monthly_averages(self, months: int = 12) -> List[Dict]:
        """Get monthly average temperature and rainfall for the last N months"""
        # Aggregate by hour first (max per hour) to avoid double-counting duplicate observations
        # Then aggregate by day, then by month
        query = f"""
            SELECT 
                year,
                month,
                avg(avg_temperature_c) as avg_temperature_c,
                sum(total_rainfall_mm) as total_rainfall_mm,
                avg(avg_humidity_percent) as avg_humidity_percent,
                sum(observation_count) as observation_count
            FROM (
                SELECT 
                    toYear(date) as year,
                    toMonth(date) as month,
                    date,
                    avg(avg_temperature_c) as avg_temperature_c,
                    sum(max_rainfall_per_hour) as total_rainfall_mm,
                    avg(avg_humidity_percent) as avg_humidity_percent,
                    sum(observation_count) as observation_count
                FROM (
                    SELECT 
                        toDate(timestamp) as date,
                        toStartOfHour(timestamp) as hour,
                        avg(temperature_c) as avg_temperature_c,
                        max(rainfall_mm) as max_rainfall_per_hour,
                        avg(humidity_percent) as avg_humidity_percent,
                        count() as observation_count
                    FROM weather_observations
                    WHERE temperature_c IS NOT NULL
                    GROUP BY date, hour
                )
                GROUP BY date
            )
            GROUP BY year, month
            ORDER BY year DESC, month DESC
            LIMIT {months}
        """
        
        results = self.client.execute(query)
        
        return [
            {
                'year': row[0],
                'month': row[1],
                'avg_temperature_c': row[2],
                'total_rainfall_mm': row[3],
                'avg_humidity_percent': min(row[4], 100.0) if row[4] and row[4] > 0 else row[4],  # Cap humidity at 100%
                'observation_count': row[5]
            }
            for row in results
        ]
    
    def get_daily_averages(self, days: int = 90) -> List[Dict]:
        """Get daily average temperature and rainfall for the last N days"""
        # Aggregate by hour first (max per hour) to avoid double-counting duplicate observations
        query = f"""
            SELECT 
                date,
                avg(avg_temperature_c) as avg_temperature_c,
                sum(max_rainfall_per_hour) as total_rainfall_mm,
                avg(avg_humidity_percent) as avg_humidity_percent,
                max(max_temperature_c) as max_temperature_c,
                min(min_temperature_c) as min_temperature_c,
                sum(observation_count) as observation_count,
                max(latest_obs_time) as latest_obs_time
            FROM (
                SELECT 
                    toDate(timestamp) as date,
                    toStartOfHour(timestamp) as hour,
                    avg(temperature_c) as avg_temperature_c,
                    max(rainfall_mm) as max_rainfall_per_hour,
                    avg(humidity_percent) as avg_humidity_percent,
                    max(temperature_c) as max_temperature_c,
                    min(temperature_c) as min_temperature_c,
                    count() as observation_count,
                    max(timestamp) as latest_obs_time
                FROM weather_observations
                WHERE temperature_c IS NOT NULL
                GROUP BY date, hour
            )
            GROUP BY date
            ORDER BY date DESC
            LIMIT {days}
        """
        
        results = self.client.execute(query)
        
        return [
            {
                'date': row[0].isoformat() if hasattr(row[0], 'isoformat') else str(row[0]),
                'avg_temperature_c': row[1],
                'total_rainfall_mm': row[2],
                'avg_humidity_percent': min(row[3], 100.0) if row[3] and row[3] > 0 else row[3],  # Cap humidity at 100%
                'max_temperature_c': row[4],
                'min_temperature_c': row[5],
                'observation_count': row[6],
                'latest_obs_timestamp': row[7].isoformat() if row[7] and hasattr(row[7], 'isoformat') else (str(row[7]) if row[7] else None)
            }
            for row in results
        ]

