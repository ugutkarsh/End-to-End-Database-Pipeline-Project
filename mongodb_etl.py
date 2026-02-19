"""
MongoDB ETL - Stores raw and enriched weather data
"""
from pymongo import MongoClient
from datetime import datetime
from typing import Dict, Optional
import config
from nws_api_fetcher_v2 import NWSAPIFetcher

class MongoDBETL:
    def __init__(self):
        # MongoDB Atlas requires SSL/TLS, handle certificate verification
        self.client = MongoClient(
            config.MONGODB_URI,
            tlsAllowInvalidCertificates=True  # For development - allows connection despite cert issues
        )
        self.db = self.client[config.MONGODB_DB]
        self.raw_collection = self.db[config.MONGODB_COLLECTION_RAW]
        self.enriched_collection = self.db[config.MONGODB_COLLECTION_ENRICHED]
        self.api_fetcher = NWSAPIFetcher()
    
    def enrich_data(self, raw_data: Dict) -> Dict:
        """Enrich raw data with calculated fields and metadata"""
        enriched = raw_data.copy()
        
        # Extract metrics from NWS API observations
        observations = raw_data.get('observations', []) + raw_data.get('historical_observations', [])
        
        temperatures = []
        rainfall = []
        humidity = []
        
        # Extract from NWS observations
        for obs in observations:
            props = obs.get('properties', {})
            
            # Temperature (convert from Kelvin to Celsius if needed)
            temp = props.get('temperature', {}).get('value')
            if temp is not None:
                # Convert from Kelvin to Celsius (NWS uses Kelvin)
                temp_c = temp - 273.15 if temp > 100 else temp
                temperatures.append(temp_c)
            
            # Precipitation (convert from meters to mm)
            precip = props.get('precipitationLastHour', {}).get('value')
            if precip is not None:
                # Convert from meters to millimeters
                precip_mm = precip * 1000 if precip < 1 else precip
                rainfall.append(precip_mm)
            
            # Humidity
            rel_humidity = props.get('relativeHumidity', {}).get('value')
            if rel_humidity is not None:
                humidity.append(rel_humidity)
        
        # Also extract from forecast if available
        forecast = raw_data.get('forecast', {})
        if forecast:
            periods = forecast.get('properties', {}).get('periods', [])
            for period in periods[:7]:  # First 7 periods
                temp = period.get('temperature')
                if temp is not None:
                    # Forecast temps are in Fahrenheit, convert to Celsius
                    temp_c = (temp - 32) * 5/9
                    temperatures.append(temp_c)
        
        # Calculate averages
        enriched['calculated_metrics'] = {
            'avg_temperature_c': sum(temperatures) / len(temperatures) if temperatures else None,
            'total_rainfall_mm': sum(rainfall) if rainfall else None,
            'avg_rainfall_mm': sum(rainfall) / len(rainfall) if rainfall else None,
            'avg_humidity_percent': sum(humidity) / len(humidity) if humidity else None,
            'observation_count': len(observations),
            'temperature_count': len(temperatures),
            'rainfall_count': len(rainfall),
            'humidity_count': len(humidity)
        }
        
        # Add enrichment metadata
        enriched['ingest_time_utc'] = datetime.utcnow().isoformat() + "Z"
        enriched['record_source'] = "NWS_API"
        enriched['transform_status'] = "enriched"
        enriched['sync_type'] = raw_data.get('sync_type', 'full')
        
        # Add team metadata
        enriched['metadata'] = {
            'team_name': 'Team Supra',
            'ingest_time_utc': enriched['ingest_time_utc'],
            'data_source': enriched.get('source_database', 'NWS_API'),
            'sync_type': enriched['sync_type']
        }
        
        return enriched
    
    def sync_from_api(self, sync_type: str = "full") -> Optional[str]:
        """Fetch data from API and store in MongoDB"""
        etl_batch_id = f"batch_{int(datetime.utcnow().timestamp() * 1000)}"
        
        print(f"Fetching weather data from NWS API (batch: {etl_batch_id})...")
        raw_data = self.api_fetcher.fetch_stockton_weather_data(etl_batch_id)
        
        if not raw_data:
            print("Failed to fetch data from API")
            return None
        
        # Store raw data with metadata
        raw_data['sync_type'] = sync_type
        raw_data['metadata'] = {
            'team_name': 'Team Supra',
            'ingest_time_utc': datetime.utcnow().isoformat() + "Z",
            'data_source': raw_data.get('source_database', 'NWS_API'),
            'sync_type': sync_type
        }
        raw_doc_id = self.raw_collection.insert_one(raw_data).inserted_id
        print(f"Stored raw data with ID: {raw_doc_id}")
        
        # Enrich and store enriched data
        enriched_data = self.enrich_data(raw_data)
        enriched_doc_id = self.enriched_collection.insert_one(enriched_data).inserted_id
        print(f"Stored enriched data with ID: {enriched_doc_id}")
        
        return etl_batch_id
    
    def get_latest_enriched_data(self) -> Optional[Dict]:
        """Get the most recent enriched data document"""
        return self.enriched_collection.find_one(
            sort=[("ingest_time_utc", -1)]
        )
    
    def get_all_enriched_data(self) -> list:
        """Get all enriched data documents"""
        return list(self.enriched_collection.find())

