"""
Web Dashboard - Visualizes weather data from Redis/ClickHouse
Redesigned with glassmorphism and Team_Supra layout
"""
from flask import Flask, render_template_string, jsonify, request
import json
from datetime import datetime
import config
from redis_etl import RedisETL
from clickhouse_etl import ClickHouseETL
from mongodb_etl import MongoDBETL

app = Flask(__name__)

redis_etl = RedisETL()
clickhouse_etl = ClickHouseETL()
mongodb_etl = MongoDBETL()

# HTML Template with Glassmorphism Design
DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Stockton Weather Dashboard</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            margin: 0;
            padding: 0;
            min-height: 100vh;
            color: #ffffff;
            overflow-x: hidden;
            position: relative;
        }
        
        /* Dynamic background with scenic images */
        .weather-background {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: -1;
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            transition: background-image 1s ease-in-out;
            background-image: url('https://images.unsplash.com/photo-1504608524841-42fe6f032b4b?w=1920&q=80');
        }
        
        .weather-background::after {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.35);
        }
        
        .main-container {
            position: relative;
            z-index: 1;
            min-height: 100vh;
            padding: 30px;
            display: grid;
            grid-template-columns: 240px 1fr 280px;
            grid-template-rows: auto 1fr auto;
            gap: 20px;
            max-width: 1600px;
            margin: 0 auto;
        }
        
        @media (max-width: 968px) {
            .main-container {
                grid-template-columns: 1fr;
                grid-template-rows: auto auto auto;
            }
        }
        
        /* Header */
        .header {
            grid-column: 1 / -1;
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 20px 0;
        }
        
        .logo {
            font-size: 1.5rem;
            font-weight: 700;
            color: #ffffff;
        }
        
        .location-info {
            text-align: center;
            flex: 1;
        }
        
        .location-name {
            font-size: 1.1rem;
            font-weight: 500;
            color: #ffffff;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }
        
        .location-date {
            font-size: 0.9rem;
            color: rgba(255, 255, 255, 0.8);
            margin-top: 4px;
        }
        
        .header-actions {
            display: flex;
            gap: 12px;
            align-items: center;
        }
        
        .sync-btn {
            padding: 10px 20px;
            background: rgba(255, 255, 255, 0.15);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 12px;
            color: #ffffff;
            cursor: pointer;
            font-size: 0.9rem;
            transition: all 0.3s ease;
        }
        
        .sync-btn:hover {
            background: rgba(255, 255, 255, 0.25);
            transform: translateY(-2px);
        }
        
        /* Glassmorphism card */
        .glass-card {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 20px;
            padding: 24px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        }
        
        /* Current Weather - Center */
        .current-weather {
            grid-column: 2;
            grid-row: 2;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
        }
        
        .current-temp {
            font-size: 8rem;
            font-weight: 300;
            line-height: 1;
            color: #ffffff;
            margin: 20px 0;
            text-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        }
        
        .temp-range {
            display: flex;
            gap: 16px;
            margin: 20px 0;
            font-size: 1.2rem;
            color: rgba(255, 255, 255, 0.9);
        }
        
        .temp-high, .temp-low {
            padding: 8px 16px;
            background: rgba(255, 255, 255, 0.15);
            backdrop-filter: blur(10px);
            border-radius: 20px;
        }
        
        .weather-description {
            font-size: 1.3rem;
            color: rgba(255, 255, 255, 0.9);
            margin-top: 10px;
        }
        
        /* Left Sidebar */
        .left-sidebar {
            grid-column: 1;
            grid-row: 2;
            display: flex;
            flex-direction: column;
            gap: 20px;
        }
        
        .today-temp-card {
            background: rgba(255, 255, 255, 0.08);
            backdrop-filter: blur(25px);
            border: 1px solid rgba(255, 255, 255, 0.25);
            border-radius: 20px;
            padding: 24px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
            transition: all 0.3s ease;
        }
        
        .today-temp-card:hover {
            background: rgba(255, 255, 255, 0.12);
            border-color: rgba(255, 255, 255, 0.35);
            transform: translateY(-2px);
            box-shadow: 0 12px 40px rgba(0, 0, 0, 0.2);
        }
        
        .today-temp-label {
            font-size: 0.75rem;
            color: rgba(255, 255, 255, 0.7);
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 12px;
            font-weight: 500;
        }
        
        .today-temp-value {
            font-size: 3rem;
            font-weight: 600;
            color: #ffffff;
            margin-bottom: 8px;
            text-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
        }
        
        .today-temp-unit {
            font-size: 1.5rem;
            font-weight: 300;
            color: rgba(255, 255, 255, 0.8);
            margin-left: 4px;
        }
        
        .today-temp-details {
            display: flex;
            justify-content: space-between;
            margin-top: 16px;
            padding-top: 16px;
            border-top: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .today-temp-detail {
            text-align: center;
            flex: 1;
        }
        
        .today-temp-detail-label {
            font-size: 0.7rem;
            color: rgba(255, 255, 255, 0.6);
            margin-bottom: 4px;
        }
        
        .today-temp-detail-value {
            font-size: 1rem;
            font-weight: 600;
            color: #ffffff;
        }
        
        .status-indicator {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            display: inline-block;
            box-shadow: 0 0 10px currentColor;
        }
        
        .status-full { 
            background-color: #10b981;
            color: #10b981;
        }
        .status-partial { 
            background-color: #f59e0b;
            color: #f59e0b;
        }
        .status-out-of-sync { 
            background-color: #ef4444;
            color: #ef4444;
        }
        
        /* Right Sidebar */
        .right-sidebar {
            grid-column: 3;
            grid-row: 2;
            display: flex;
            flex-direction: column;
            gap: 20px;
        }
        
        .recent-searches {
            min-height: 200px;
        }
        
        .search-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            margin-top: 12px;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .search-item:hover {
            background: rgba(255, 255, 255, 0.1);
            transform: translateX(4px);
        }
        
        .search-location {
            font-size: 0.9rem;
            color: rgba(255, 255, 255, 0.9);
        }
        
        .search-temp {
            font-size: 1.1rem;
            font-weight: 600;
            color: #ffffff;
            transition: color 0.3s ease;
        }
        
        .search-temp.active {
            color: #10b981;
            text-shadow: 0 0 10px rgba(16, 185, 129, 0.5);
        }
        
        /* Weekly Forecast - Removed */
        .weekly-forecast {
            display: none;
        }
        
        /* Stats Grid */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 16px;
            margin: 20px 0;
        }
        
        .stat-mini {
            text-align: center;
            padding: 16px;
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 16px;
        }
        
        .stat-mini-icon {
            font-size: 1.8rem;
            margin-bottom: 8px;
            filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.2));
        }
        
        .stat-mini-label {
            font-size: 0.75rem;
            color: rgba(255, 255, 255, 0.7);
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .stat-mini-value {
            font-size: 1.5rem;
            font-weight: 600;
            color: #ffffff;
        }
        
        .stat-mini-unit {
            font-size: 0.9rem;
            color: rgba(255, 255, 255, 0.7);
            margin-left: 4px;
            font-weight: 400;
        }
        
        /* Charts */
        .chart-section {
            grid-column: 1 / -1;
            margin-top: 30px;
        }
        
        .chart-container {
            margin: 20px 0;
            background: rgba(255, 255, 255, 0.08);
            backdrop-filter: blur(25px);
            border: 1px solid rgba(255, 255, 255, 0.25);
            padding: 28px;
            border-radius: 24px;
            box-shadow: 0 12px 40px rgba(0, 0, 0, 0.15),
                        0 0 0 1px rgba(255, 255, 255, 0.1) inset;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }
        
        .chart-container::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 2px;
            background: linear-gradient(90deg, 
                transparent, 
                rgba(100, 200, 255, 0.5), 
                transparent
            );
            opacity: 0.6;
        }
        
        .chart-container:hover {
            background: rgba(255, 255, 255, 0.12);
            border-color: rgba(255, 255, 255, 0.35);
            box-shadow: 0 16px 48px rgba(0, 0, 0, 0.2),
                        0 0 0 1px rgba(255, 255, 255, 0.15) inset,
                        0 0 30px rgba(100, 200, 255, 0.1);
            transform: translateY(-2px);
        }
        
        .chart-title {
            font-size: 1.2rem;
            font-weight: 600;
            color: rgba(255, 255, 255, 0.95);
            margin-bottom: 20px;
            text-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
            letter-spacing: 0.3px;
            position: relative;
            padding-bottom: 12px;
        }
        
        .chart-title::after {
            content: '';
            position: absolute;
            bottom: 0;
            left: 0;
            width: 60px;
            height: 2px;
            background: linear-gradient(90deg, 
                rgba(100, 200, 255, 0.8), 
                transparent
            );
            border-radius: 2px;
        }
        
        /* Error Message */
        .error {
            background: rgba(239, 68, 68, 0.2);
            border: 1px solid rgba(239, 68, 68, 0.5);
            color: #fca5a5;
            padding: 16px 20px;
            border-radius: 12px;
            margin: 20px 0;
            backdrop-filter: blur(10px);
        }
        
        /* Responsive */
        @media (max-width: 1200px) {
            .main-container {
                grid-template-columns: 240px 1fr 240px;
            }
        }
        
        @media (max-width: 968px) {
            .main-container {
                grid-template-columns: 1fr;
                grid-template-rows: auto auto auto auto auto;
            }
            
            .left-sidebar, .right-sidebar {
                grid-column: 1;
            }
            
            .current-weather {
                grid-column: 1;
            }
        }
    </style>
</head>
<body>
    <div class="weather-background" id="weatherBackground"></div>
    
    <div class="main-container">
        <!-- Header -->
        <div class="header">
            <div class="logo">🌤️ Team_Supra</div>
            <div class="location-info">
                <div class="location-name">
                    📍 Stockton, CA, USA
                </div>
                <div class="location-date" id="currentDate"></div>
            </div>
            <div class="header-actions">
                <div class="sync-status glass-card" style="padding: 8px 16px; display: flex; align-items: center; gap: 8px;">
                    <span class="status-indicator" id="syncStatus"></span>
                    <span id="syncStatusText" style="font-size: 0.85rem;">Syncing...</span>
                </div>
                <button class="sync-btn" onclick="syncNow()">🔄 Sync</button>
            </div>
        </div>
        
        <!-- Left Sidebar - Today's Temperature -->
        <div class="left-sidebar">
            <div class="today-temp-card">
                <div class="today-temp-label" id="dataTimestamp">Loading...</div>
                <div class="today-temp-value" id="todayTemp">--<span class="today-temp-unit">°F</span></div>
                <div class="today-temp-details" style="justify-content: center; flex-direction: column; gap: 8px;">
                    <div class="today-temp-detail">
                        <div class="today-temp-detail-label">Today's Average</div>
                        <div class="today-temp-detail-value" id="todayAvg">--°F</div>
                    </div>
                    <div class="today-temp-detail" style="margin-top: 8px;">
                        <div class="today-temp-detail-label" style="font-size: 0.65rem;">Data Timestamp</div>
                        <div class="today-temp-detail-value" id="dataTimestampDetail" style="font-size: 0.85rem;">--</div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Current Weather - Center -->
        <div class="current-weather">
            <div class="glass-card" style="width: 100%; max-width: 500px;">
                <div style="text-align: center; margin-bottom: 10px;">
                    <div style="font-size: 0.9rem; color: rgba(255, 255, 255, 0.8); text-transform: uppercase; letter-spacing: 1px; font-weight: 500;">Avg Temp (Monthly)</div>
                    <div id="periodLabel" style="font-size: 0.75rem; color: rgba(255, 255, 255, 0.6); margin-top: 4px;">Last <span id="periodMonths">--</span> months</div>
                </div>
                <div class="current-temp" id="currentTemp">--<span style="font-size: 4rem; font-weight: 300;">°F</span></div>
                <div class="temp-range">
                    <div class="temp-high">H: <span id="tempHigh">--</span>°F</div>
                    <div class="temp-low">L: <span id="tempLow">--</span>°F</div>
                </div>
                <div class="weather-description" id="weatherDesc">Loading weather data...</div>
                
                <div class="stats-grid" style="margin-top: 30px;">
                    <div class="stat-mini">
                        <div class="stat-mini-icon">🌧️</div>
                        <div class="stat-mini-label">Rainfall</div>
                        <div class="stat-mini-value" id="totalRainfall">--<span class="stat-mini-unit">mm</span></div>
                    </div>
                    <div class="stat-mini">
                        <div class="stat-mini-icon">💧</div>
                        <div class="stat-mini-label">Humidity</div>
                        <div class="stat-mini-value" id="avgHumidity">--<span class="stat-mini-unit">%</span></div>
                    </div>
                    <div class="stat-mini">
                        <div class="stat-mini-icon">🌡️</div>
                        <div class="stat-mini-label">Avg Temp</div>
                        <div class="stat-mini-value" id="avgTemp">--<span class="stat-mini-unit">°F</span></div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Right Sidebar -->
        <div class="right-sidebar">
            <div class="glass-card recent-searches">
                <div class="section-title">Data Sources</div>
                <div class="search-item">
                    <div class="search-location">MongoDB</div>
                    <div class="search-temp" id="mongoStatus">✓</div>
                </div>
                <div class="search-item">
                    <div class="search-location">ClickHouse</div>
                    <div class="search-temp" id="clickhouseStatus">✓</div>
                </div>
                <div class="search-item">
                    <div class="search-location">Redis Cache</div>
                    <div class="search-temp" id="redisStatus">✓</div>
                </div>
            </div>
        </div>
        
        
        <!-- Charts Section -->
        <div class="chart-section">
            <div class="chart-container">
                <div class="chart-title">Daily Temperature Trend (°F)</div>
                <div id="temperatureChart" style="height: 400px;"></div>
            </div>
            
            <div class="chart-container">
                <div class="chart-title">Monthly Rainfall (mm)</div>
                <div id="rainfallChart" style="height: 400px;"></div>
            </div>
        </div>
        
        <div id="errorMessage"></div>
    </div>
    
    <script>
        // Set current date
        const now = new Date();
        const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
        document.getElementById('currentDate').textContent = now.toLocaleDateString('en-US', options);
        
        function updateSyncStatus(status) {
            const indicator = document.getElementById('syncStatus');
            const text = document.getElementById('syncStatusText');
            
            indicator.className = 'status-indicator';
            if (status === 'full') {
                indicator.classList.add('status-full');
                text.textContent = 'Sync: Full';
            } else if (status === 'partial') {
                indicator.classList.add('status-partial');
                text.textContent = 'Sync: Partial';
            } else {
                indicator.classList.add('status-out-of-sync');
                text.textContent = 'Sync: Out of Sync';
            }
        }
        
        function showError(message) {
            const errorDiv = document.getElementById('errorMessage');
            errorDiv.className = 'error';
            errorDiv.textContent = message;
            errorDiv.style.display = 'block';
        }
        
        function clearError() {
            document.getElementById('errorMessage').style.display = 'none';
        }
        
        async function loadDashboard() {
            clearError();
            resetAllDatabaseStatuses();
            
            try {
                // Show Redis and ClickHouse being accessed (for data loading)
                setDatabaseStatus('redisStatus', true);
                setDatabaseStatus('clickhouseStatus', true);
                
                const response = await fetch('/api/data');
                const data = await response.json();
                
                // Reset after a brief moment
                setTimeout(() => {
                    resetAllDatabaseStatuses();
                }, 500);
                
                if (data.error) {
                    showError(data.error);
                    return;
                }
                
                // Update current weather
                if (data.overall_averages) {
                    const tempF = data.overall_averages.avg_temperature_f || 
                        (data.overall_averages.avg_temperature_c ? (data.overall_averages.avg_temperature_c * 9/5) + 32 : null);
                    
                    // Update main temperature with unit
                    const tempDisplay = document.getElementById('currentTemp');
                    if (tempF) {
                        tempDisplay.innerHTML = Math.round(tempF) + '<span style="font-size: 4rem; font-weight: 300;">°F</span>';
                    } else {
                        tempDisplay.innerHTML = '--<span style="font-size: 4rem; font-weight: 300;">°F</span>';
                    }
                    // Update period label
                    const periodMonths = data.overall_averages.period_months || data.monthly_data?.length || '--';
                    document.getElementById('periodMonths').textContent = periodMonths;
                    
                    // Estimate high/low (could be improved with actual min/max)
                    const high = tempF ? Math.round(tempF + 8) : '--';
                    const low = tempF ? Math.round(tempF - 8) : '--';
                    document.getElementById('tempHigh').textContent = high;
                    document.getElementById('tempLow').textContent = low;
                    
                    // Update rainfall with unit preserved
                    const rainfallEl = document.getElementById('totalRainfall');
                    const rainfallValue = data.overall_averages.total_rainfall_mm ? Math.round(data.overall_averages.total_rainfall_mm) : '--';
                    rainfallEl.innerHTML = rainfallValue + '<span class="stat-mini-unit">mm</span>';
                    
                    // Update humidity with unit preserved
                    const humidityEl = document.getElementById('avgHumidity');
                    const humidityValue = data.overall_averages.avg_humidity_percent ? Math.round(data.overall_averages.avg_humidity_percent) : '--';
                    humidityEl.innerHTML = humidityValue + '<span class="stat-mini-unit">%</span>';
                    
                    // Update avg temp with unit preserved
                    const avgTempEl = document.getElementById('avgTemp');
                    const avgTempValue = tempF ? Math.round(tempF) : '--';
                    avgTempEl.innerHTML = avgTempValue + '<span class="stat-mini-unit">°F</span>';
                    
                    // Weather description
                    const desc = tempF > 75 ? 'Sunny' : tempF > 60 ? 'Partly Cloudy' : tempF > 45 ? 'Cloudy' : 'Cool';
                    document.getElementById('weatherDesc').textContent = desc;
                    
                    // Update background based on weather
                    updateBackground(desc);
                }
                
                // Update sync status
                updateSyncStatus(data.sync_status || 'out-of-sync');
                
                // Update today's temperature - show the date of the weather data itself
                if (data.daily_data && data.daily_data.length > 0) {
                    // Get the most recent data point (first in array as it's sorted DESC)
                    const todayData = data.daily_data[0];
                    
                    if (todayData && todayData.date) {
                        // Format the date of the weather observation (not fetch date)
                        const dataDate = new Date(todayData.date + 'T00:00:00');
                        const dateOptions = { weekday: 'short', year: 'numeric', month: 'short', day: 'numeric' };
                        const formattedDate = dataDate.toLocaleDateString('en-US', dateOptions);
                        document.getElementById('dataTimestamp').textContent = formattedDate;
                        
                        // Format timestamp - use latest observation time if available, otherwise use date
                        let timestampDate = dataDate;
                        if (todayData.latest_obs_timestamp) {
                            timestampDate = new Date(todayData.latest_obs_timestamp);
                        }
                        const timestampOptions = { 
                            weekday: 'short', 
                            year: 'numeric', 
                            month: 'short', 
                            day: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit',
                            hour12: true
                        };
                        const timestampStr = timestampDate.toLocaleString('en-US', timestampOptions) + ' UTC';
                        document.getElementById('dataTimestampDetail').textContent = timestampStr;
                        
                        const todayTempC = todayData.avg_temperature_c;
                        const todayTempF = todayTempC ? (todayTempC * 9/5) + 32 : null;
                        
                        if (todayTempF) {
                            document.getElementById('todayTemp').innerHTML = Math.round(todayTempF) + '<span class="today-temp-unit">°F</span>';
                            document.getElementById('todayAvg').textContent = Math.round(todayTempF) + '°F';
                        } else {
                            document.getElementById('todayTemp').innerHTML = '--<span class="today-temp-unit">°F</span>';
                            document.getElementById('todayAvg').textContent = '--°F';
                        }
                    } else {
                        document.getElementById('dataTimestamp').textContent = 'No data available';
                        document.getElementById('dataTimestampDetail').textContent = '--';
                        document.getElementById('todayAvg').textContent = '--°F';
                    }
                } else {
                    document.getElementById('dataTimestamp').textContent = 'No data available';
                    document.getElementById('dataTimestampDetail').textContent = '--';
                    document.getElementById('todayAvg').textContent = '--°F';
                }
                
                // Update charts
                if (data.daily_data && data.daily_data.length > 0) {
                    updateCharts(data.daily_data, data.monthly_data);
                } else if (data.monthly_data && data.monthly_data.length > 0) {
                    updateCharts(null, data.monthly_data);
                }
            } catch (error) {
                showError('Error loading dashboard: ' + error.message);
                updateSyncStatus('out-of-sync');
            }
        }
        
        function updateBackground(weatherDesc) {
            const bg = document.getElementById('weatherBackground');
            // Use scenic background images based on weather
            if (weatherDesc.includes('Sunny')) {
                bg.style.backgroundImage = "url('https://images.unsplash.com/photo-1504608524841-42fe6f032b4b?w=1920&q=80')";
            } else if (weatherDesc.includes('Cloudy')) {
                bg.style.backgroundImage = "url('https://images.unsplash.com/photo-1518837695005-2083093ee35b?w=1920&q=80')";
            } else if (weatherDesc.includes('Rain') || weatherDesc.includes('Storm')) {
                bg.style.backgroundImage = "url('https://images.unsplash.com/photo-1433863448220-78aaa064b47c?w=1920&q=80')";
            } else {
                bg.style.backgroundImage = "url('https://images.unsplash.com/photo-1518837695005-2083093ee35b?w=1920&q=80')";
            }
        }
        
        function updateCharts(dailyData, monthlyData) {
            if (dailyData && dailyData.length > 0) {
                const sortedDaily = [...dailyData].sort((a, b) => new Date(a.date) - new Date(b.date));
                const dates = sortedDaily.map(d => {
                    const date = new Date(d.date);
                    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
                });
                const temps = sortedDaily.map(d => d.avg_temperature_c ? (d.avg_temperature_c * 9/5) + 32 : null);
                
                Plotly.newPlot('temperatureChart', [{
                    x: dates,
                    y: temps,
                    type: 'scatter',
                    mode: 'lines+markers',
                    name: 'Temperature',
                    line: { color: '#ffffff', width: 3, shape: 'spline' },
                    marker: { size: 8, color: '#ffffff' },
                    fill: 'tozeroy',
                    fillcolor: 'rgba(255, 255, 255, 0.1)'
                }], {
                    paper_bgcolor: 'rgba(0,0,0,0)',
                    plot_bgcolor: 'rgba(0,0,0,0)',
                    font: { color: '#ffffff', family: 'Inter' },
                    xaxis: { showgrid: false, linecolor: 'rgba(255,255,255,0.3)' },
                    yaxis: { showgrid: true, gridcolor: 'rgba(255,255,255,0.1)', linecolor: 'rgba(255,255,255,0.3)' },
                    margin: { l: 50, r: 30, t: 20, b: 50 },
                    showlegend: false
                }, { responsive: true });
            }
            
            if (monthlyData && monthlyData.length > 0) {
                const sorted = [...monthlyData].sort((a, b) => {
                    if (a.year !== b.year) return a.year - b.year;
                    return a.month - b.month;
                });
                
                // Format months nicely
                const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
                const months = sorted.map(d => `${monthNames[d.month - 1]} ${d.year}`);
                const rainfall = sorted.map(d => d.total_rainfall_mm || 0);
                
                // Create warm-to-cool gradient color scheme matching the reference image
                // Progression: Reddish-pink → Orange → Yellow-orange → Olive green → Bright green → Teal → Medium blue → Sky blue
                const maxRainfall = Math.max(...rainfall, 1);
                
                function getGradientColor(intensity) {
                    // Normalize intensity to 0-1
                    const t = Math.min(Math.max(intensity, 0), 1);
                    
                    // Define color stops for warm-to-cool gradient
                    // 0.0: Reddish-pink (255, 100, 150)
                    // 0.15: Orange (255, 165, 0)
                    // 0.3: Yellow-orange (255, 200, 50)
                    // 0.45: Olive green (180, 200, 80)
                    // 0.6: Bright green (100, 220, 100)
                    // 0.75: Teal (50, 200, 180)
                    // 0.9: Medium blue (50, 150, 255)
                    // 1.0: Sky blue (100, 200, 255)
                    
                    let r, g, b;
                    if (t < 0.15) {
                        // Reddish-pink to Orange
                        const localT = t / 0.15;
                        r = 255;
                        g = 100 + (165 - 100) * localT;
                        b = 150 - 150 * localT;
                    } else if (t < 0.3) {
                        // Orange to Yellow-orange
                        const localT = (t - 0.15) / 0.15;
                        r = 255;
                        g = 165 + (200 - 165) * localT;
                        b = 0 + 50 * localT;
                    } else if (t < 0.45) {
                        // Yellow-orange to Olive green
                        const localT = (t - 0.3) / 0.15;
                        r = 255 - (255 - 180) * localT;
                        g = 200;
                        b = 50 + (80 - 50) * localT;
                    } else if (t < 0.6) {
                        // Olive green to Bright green
                        const localT = (t - 0.45) / 0.15;
                        r = 180 - (180 - 100) * localT;
                        g = 200 + (220 - 200) * localT;
                        b = 80 + (100 - 80) * localT;
                    } else if (t < 0.75) {
                        // Bright green to Teal
                        const localT = (t - 0.6) / 0.15;
                        r = 100 - (100 - 50) * localT;
                        g = 220 - (220 - 200) * localT;
                        b = 100 + (180 - 100) * localT;
                    } else if (t < 0.9) {
                        // Teal to Medium blue
                        const localT = (t - 0.75) / 0.15;
                        r = 50;
                        g = 200 - (200 - 150) * localT;
                        b = 180 + (255 - 180) * localT;
                    } else {
                        // Medium blue to Sky blue
                        const localT = (t - 0.9) / 0.1;
                        r = 50 + (100 - 50) * localT;
                        g = 150 + (200 - 150) * localT;
                        b = 255;
                    }
                    
                    return { r: Math.round(r), g: Math.round(g), b: Math.round(b) };
                }
                
                const barColors = rainfall.map(r => {
                    if (r === 0) return 'rgba(255, 255, 255, 0.15)';
                    const intensity = Math.min(r / maxRainfall, 1);
                    const color = getGradientColor(intensity);
                    const alpha = 0.5 + intensity * 0.25; // 0.5 to 0.75 (more transparent)
                    return `rgba(${color.r}, ${color.g}, ${color.b}, ${alpha})`;
                });
                
                // Create border colors with slight glow effect (more transparent)
                const borderColors = rainfall.map(r => {
                    if (r === 0) return 'rgba(255, 255, 255, 0.25)';
                    const intensity = Math.min(r / maxRainfall, 1);
                    const color = getGradientColor(intensity);
                    return `rgba(${Math.min(color.r + 30, 255)}, ${Math.min(color.g + 30, 255)}, ${Math.min(color.b + 30, 255)}, 0.6)`;
                });
                
                Plotly.newPlot('rainfallChart', [{
                    x: months,
                    y: rainfall,
                    type: 'bar',
                    name: 'Rainfall',
                    marker: { 
                        color: barColors,
                        line: { 
                            color: borderColors,
                            width: 2 
                        },
                        opacity: 1,
                        cornerradius: 16  // Rounded bars (increased for more rounded appearance)
                    },
                    text: rainfall.map(r => r > 0 ? r.toFixed(1) + ' mm' : ''),
                    textposition: 'outside',
                    textfont: {
                        color: '#ffffff',
                        size: 12,
                        family: 'Inter',
                        weight: '600'
                    },
                    hovertemplate: '<b>%{x}</b><br>Rainfall: %{y:.1f} mm<extra></extra>',
                    hoverlabel: {
                        bgcolor: 'rgba(0, 0, 0, 0.8)',
                        bordercolor: 'rgba(255, 255, 255, 0.3)',
                        font: { color: '#ffffff', family: 'Inter', size: 13 }
                    }
                }], {
                    paper_bgcolor: 'rgba(0,0,0,0)',
                    plot_bgcolor: 'rgba(0,0,0,0)',
                    font: { color: '#ffffff', family: 'Inter', size: 13 },
                    xaxis: { 
                        showgrid: false, 
                        linecolor: 'rgba(255,255,255,0.3)',
                        tickfont: { color: 'rgba(255,255,255,0.85)', size: 12, family: 'Inter' },
                        tickangle: -45,
                        showline: true,
                        linewidth: 1.5,
                        mirror: false
                    },
                    yaxis: { 
                        showgrid: true, 
                        gridcolor: 'rgba(255,255,255,0.12)', 
                        gridwidth: 1,
                        linecolor: 'rgba(255,255,255,0.3)',
                        linewidth: 1.5,
                        tickfont: { color: 'rgba(255,255,255,0.85)', size: 12, family: 'Inter' },
                        title: { 
                            text: 'Rainfall (mm)', 
                            font: { color: 'rgba(255,255,255,0.9)', size: 13, family: 'Inter' },
                            standoff: 15
                        },
                        zeroline: false
                    },
                    margin: { l: 70, r: 40, t: 50, b: 80 },
                    showlegend: false,
                    bargap: 0.4,
                    bargroupgap: 0.1,
                    hovermode: 'closest',
                    transition: {
                        duration: 600,
                        easing: 'cubic-in-out'
                    }
                }, { 
                    responsive: true,
                    displayModeBar: true,
                    displaylogo: false,
                    modeBarButtonsToRemove: ['pan2d', 'lasso2d', 'select2d'],
                    toImageButtonOptions: {
                        format: 'png',
                        filename: 'rainfall_chart',
                        height: 600,
                        width: 1200,
                        scale: 2
                    }
                });
                
                // Add custom CSS for rounded bars and enhanced effects
                setTimeout(() => {
                    const chartElement = document.getElementById('rainfallChart');
                    if (chartElement) {
                        const style = document.createElement('style');
                        style.textContent = `
                            #rainfallChart .js-plotly-plot .plotly .bar {
                                transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1) !important;
                                filter: drop-shadow(0 3px 10px rgba(0, 0, 0, 0.2));
                                border-radius: 8px !important;
                            }
                            #rainfallChart .js-plotly-plot .plotly .bar:hover {
                                filter: drop-shadow(0 6px 20px rgba(255, 255, 255, 0.3)) !important;
                                transform: translateY(-2px) !important;
                                opacity: 1 !important;
                            }
                            #rainfallChart .js-plotly-plot .plotly .xtick text,
                            #rainfallChart .js-plotly-plot .plotly .ytick text {
                                text-shadow: 0 1px 3px rgba(0, 0, 0, 0.4);
                            }
                            #rainfallChart .js-plotly-plot .plotly .text {
                                text-shadow: 0 2px 4px rgba(0, 0, 0, 0.5);
                            }
                        `;
                        document.head.appendChild(style);
                    }
                }, 100);
            }
        }
        
        function setDatabaseStatus(dbId, active) {
            const dbElement = document.getElementById(dbId);
            if (active) {
                dbElement.classList.add('active');
            } else {
                dbElement.classList.remove('active');
            }
        }
        
        function resetAllDatabaseStatuses() {
            setDatabaseStatus('mongoStatus', false);
            setDatabaseStatus('clickhouseStatus', false);
            setDatabaseStatus('redisStatus', false);
        }
        
        async function syncNow() {
            clearError();
            updateSyncStatus('partial');
            resetAllDatabaseStatuses();
            
            try {
                // Step 1: MongoDB (API → MongoDB)
                setDatabaseStatus('mongoStatus', true);
                await new Promise(resolve => setTimeout(resolve, 800));
                
                // Step 2: ClickHouse (MongoDB → ClickHouse)
                setDatabaseStatus('clickhouseStatus', true);
                await new Promise(resolve => setTimeout(resolve, 800));
                
                // Step 3: Redis (ClickHouse → Redis)
                setDatabaseStatus('redisStatus', true);
                
                const response = await fetch('/api/sync', { method: 'POST' });
                const data = await response.json();
                
                if (data.error) {
                    showError(data.error);
                    resetAllDatabaseStatuses();
                } else {
                    // Keep green for a moment, then refresh
                    await new Promise(resolve => setTimeout(resolve, 1000));
                    resetAllDatabaseStatuses();
                    setTimeout(loadDashboard, 1000);
                }
            } catch (error) {
                showError('Error during sync: ' + error.message);
                resetAllDatabaseStatuses();
            }
        }
        
        // Load dashboard on page load
        loadDashboard();
        
        // Auto-refresh every 5 minutes
        setInterval(loadDashboard, 300000);
    </script>
</body>
</html>
"""

@app.route('/')
def dashboard():
    return render_template_string(DASHBOARD_HTML)

@app.route('/api/data')
def get_dashboard_data():
    """Get dashboard data from Redis or ClickHouse"""
    try:
        cached_data = redis_etl.get_cached_data("weather:stockton:monthly_averages")
        
        if cached_data:
            cache_status = redis_etl.check_cache_status()
            sync_status = 'full' if cache_status['monthly_cache']['fresh'] else 'partial'
            
            overall_avg = cached_data.get('overall_averages', {})
            if overall_avg.get('avg_temperature_c') and not overall_avg.get('avg_temperature_f'):
                overall_avg['avg_temperature_f'] = (overall_avg['avg_temperature_c'] * 9/5) + 32
            
            daily_data = clickhouse_etl.get_daily_averages(400)
            
            return jsonify({
                'overall_averages': overall_avg,
                'monthly_data': cached_data.get('monthly_data', []),
                'daily_data': daily_data,
                'sync_status': sync_status,
                'data_source': 'redis',
                'cache_timestamp': cached_data.get('cache_timestamp')
            })
        else:
            monthly_data = clickhouse_etl.get_monthly_averages(13)
            daily_data = clickhouse_etl.get_daily_averages(400)
            
            if monthly_data:
                total_temp = sum(d['avg_temperature_c'] for d in monthly_data if d['avg_temperature_c'])
                total_rainfall = sum(d['total_rainfall_mm'] for d in monthly_data if d['total_rainfall_mm'])
                humidity_values = [d['avg_humidity_percent'] for d in monthly_data if d.get('avg_humidity_percent') is not None]
                total_humidity = sum(humidity_values)
                count = len(monthly_data)
                humidity_count = len(humidity_values)
                
                avg_temp_c = total_temp / count if count > 0 else None
                avg_temp_f = (avg_temp_c * 9/5 + 32) if avg_temp_c else None
                
                return jsonify({
                    'overall_averages': {
                        'avg_temperature_c': avg_temp_c,
                        'avg_temperature_f': avg_temp_f,
                        'total_rainfall_mm': total_rainfall,
                        'avg_humidity_percent': total_humidity / humidity_count if humidity_count > 0 else None,
                        'period_months': count
                    },
                    'monthly_data': monthly_data,
                    'daily_data': daily_data,
                    'sync_status': 'partial',
                    'data_source': 'clickhouse'
                })
            else:
                return jsonify({
                    'error': 'No data available. Please run sync first.',
                    'sync_status': 'out-of-sync'
                })
    except Exception as e:
        return jsonify({
            'error': str(e),
            'sync_status': 'out-of-sync'
        })

@app.route('/api/sync', methods=['POST'])
def trigger_sync():
    """Trigger a full sync across all layers"""
    try:
        batch_id = mongodb_etl.sync_from_api("full")
        clickhouse_etl.sync_from_mongodb("incremental")
        redis_etl.sync_from_clickhouse()
        
        return jsonify({
            'success': True,
            'message': 'Sync completed successfully',
            'batch_id': batch_id
        })
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500

if __name__ == '__main__':
    print(f"Starting dashboard on http://{config.DASHBOARD_HOST}:{config.DASHBOARD_PORT}")
    app.run(host=config.DASHBOARD_HOST, port=config.DASHBOARD_PORT, debug=True)

