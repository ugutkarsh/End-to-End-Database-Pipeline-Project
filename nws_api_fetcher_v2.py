"""
NWS API Fetcher - Official National Weather Service API
Uses the official NWS API from https://api.weather.gov
"""
import requests
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import config

class NWSAPIFetcher:
    def __init__(self):
        self.base_url = "https://api.weather.gov"
        self.headers = {
            "User-Agent": "StocktonWeatherPipeline/1.0 (contact@example.com)",
            "Accept": "application/geo+json"
        }
        self.stockton_lat = config.STOCKTON_LAT
        self.stockton_lon = config.STOCKTON_LON
        
    def get_grid_point(self) -> Optional[Dict]:
        """Get grid point information for Stockton coordinates"""
        url = f"{self.base_url}/points/{self.stockton_lat},{self.stockton_lon}"
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching grid point: {e}")
            return None
    
    def get_forecast(self, office: str, grid_x: int, grid_y: int) -> Optional[Dict]:
        """Get 7-day forecast from grid point"""
        url = f"{self.base_url}/gridpoints/{office}/{grid_x},{grid_y}/forecast"
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching forecast: {e}")
            return None
    
    def get_hourly_forecast(self, office: str, grid_x: int, grid_y: int) -> Optional[Dict]:
        """Get hourly forecast from grid point"""
        url = f"{self.base_url}/gridpoints/{office}/{grid_x},{grid_y}/forecast/hourly"
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching hourly forecast: {e}")
            return None
    
    def get_stations(self, office: str, grid_x: int, grid_y: int) -> Optional[List[str]]:
        """Get observation stations for the grid point"""
        url = f"{self.base_url}/gridpoints/{office}/{grid_x},{grid_y}/stations"
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            return [station['properties']['stationIdentifier'] for station in data.get('features', [])]
        except Exception as e:
            print(f"Error fetching stations: {e}")
            return None
    
    def get_station_observations(self, station_id: str, limit: int = 100) -> Optional[List[Dict]]:
        """Get recent observations from a station (NWS typically provides last 7 days)"""
        url = f"{self.base_url}/stations/{station_id}/observations"
        params = {"limit": limit}
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get('features', [])
        except Exception as e:
            print(f"Error fetching observations: {e}")
            return None
    
    def get_historical_observations(self, station_id: str, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Get historical observations (NWS API typically limits to ~7 days)"""
        observations = []
        
        # NWS API observations endpoint typically only supports last 7 days
        # Request in daily chunks
        current_date = start_date
        max_days = min((end_date - start_date).days, 7)  # Limit to 7 days
        
        while current_date <= end_date and (current_date - start_date).days < max_days:
            day_end = min(current_date + timedelta(days=1), end_date)
            
            url = f"{self.base_url}/stations/{station_id}/observations"
            params = {
                "start": current_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "end": day_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "limit": 1000
            }
            try:
                response = requests.get(url, headers=self.headers, params=params, timeout=15)
                response.raise_for_status()
                data = response.json()
                chunk_obs = data.get('features', [])
                observations.extend(chunk_obs)
                if len(chunk_obs) > 0:
                    print(f"  Fetched {len(chunk_obs)} observations for {current_date.strftime('%Y-%m-%d')}")
                time.sleep(0.3)  # Rate limiting
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 400:
                    pass  # Silently skip unsupported date ranges
                else:
                    print(f"  Warning: Could not fetch data for {current_date.strftime('%Y-%m-%d')}: {e}")
            except Exception as e:
                if "400" not in str(e):
                    print(f"  Warning: Could not fetch data for {current_date.strftime('%Y-%m-%d')}: {e}")
            
            current_date = day_end
        
        if len(observations) > 0:
            print(f"  Total observations fetched: {len(observations)}")
        return observations
    
    def fetch_stockton_weather_data(self, etl_batch_id: str) -> Dict:
        """Main method to fetch all weather data for Stockton with metadata"""
        api_request_id = f"req_{int(time.time() * 1000)}"
        source_timestamp = datetime.utcnow().isoformat() + "Z"
        
        print("Fetching grid point from NWS API...")
        grid_point = self.get_grid_point()
        if not grid_point:
            return None
        
        properties = grid_point.get('properties', {})
        office = properties.get('gridId')
        grid_x = properties.get('gridX')
        grid_y = properties.get('gridY')
        
        print(f"  Grid point: {office} ({grid_x}, {grid_y})")
        
        # Get forecast data
        print("Fetching forecast from NWS API...")
        forecast = self.get_forecast(office, grid_x, grid_y)
        hourly_forecast = self.get_hourly_forecast(office, grid_x, grid_y)
        
        # Get stations and observations
        print("Fetching observation stations...")
        stations = self.get_stations(office, grid_x, grid_y)
        observations = []
        
        if stations:
            print(f"  Found {len(stations)} stations")
            # Get observations from available stations
            for station_id in stations[:3]:  # Try up to 3 stations
                print(f"  Fetching observations from station {station_id}...")
                station_obs = self.get_station_observations(station_id, limit=100)
                if station_obs:
                    observations.extend(station_obs)
                    print(f"  Got {len(station_obs)} observations from {station_id}")
                    break
        
        # Get historical observations (last 7 days - NWS limitation)
        historical_obs = []
        if stations:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=7)  # NWS typically provides last 7 days
            for station_id in stations[:1]:  # Use first station for historical
                print(f"  Fetching historical observations (last 7 days) from {station_id}...")
                hist = self.get_historical_observations(station_id, start_date, end_date)
                historical_obs.extend(hist)
                break
        
        # Build raw data document
        raw_data = {
            "source_timestamp": source_timestamp,
            "source_database": "NWS_API",
            "data_quality": "raw",
            "api_request_id": api_request_id,
            "etl_batch_id": etl_batch_id,
            "location": {
                "city": "Stockton",
                "state": "CA",
                "latitude": self.stockton_lat,
                "longitude": self.stockton_lon,
                "grid_point": {
                    "office": office,
                    "grid_x": grid_x,
                    "grid_y": grid_y
                }
            },
            "forecast": forecast,
            "hourly_forecast": hourly_forecast,
            "observations": observations,
            "historical_observations": historical_obs,
            "stations": stations
        }
        
        return raw_data

