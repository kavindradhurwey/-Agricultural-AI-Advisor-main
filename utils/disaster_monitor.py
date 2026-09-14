"""
Disaster Monitoring Service for Agricultural AI Advisor
Monitors weather alerts, natural disasters, and agricultural calamities
"""

import requests
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import sqlite3

# Configure logging
logging.basicConfig(level=logging.INFO)

class DisasterMonitor:
    """Monitors and alerts for agricultural disasters and calamities"""
    
    def __init__(self, db_path: str = "data/agricultural_app.db"):
        self.db_path = db_path
        self.init_disaster_tables()
        
        # Weather API configuration
        self.weather_api_key = "your_openweather_api_key"  # Replace with actual API key
        self.weather_api_url = "http://api.openweathermap.org/data/2.5"
        
        # Disaster severity levels
        self.severity_levels = {
            'low': 1,
            'medium': 2,
            'high': 3,
            'critical': 4
        }
    
    def init_disaster_tables(self):
        """Initialize disaster monitoring tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Disaster alerts table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS disaster_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_type TEXT NOT NULL,
                    severity_level INTEGER NOT NULL,
                    location TEXT NOT NULL,
                    latitude REAL,
                    longitude REAL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    precautions TEXT,
                    start_time TIMESTAMP,
                    end_time TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    source TEXT DEFAULT 'system'
                )
            ''')
            
            # User location tracking for targeted alerts
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_locations (
                    user_id INTEGER PRIMARY KEY,
                    location_name TEXT,
                    latitude REAL,
                    longitude REAL,
                    state TEXT,
                    district TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            conn.commit()
    
    def check_weather_alerts(self, location: str, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Check for weather-related agricultural alerts"""
        alerts = []
        
        try:
            # Get current weather and forecast
            weather_data = self._get_weather_data(location)
            
            if weather_data:
                # Check for various weather threats
                alerts.extend(self._check_temperature_alerts(weather_data, location))
                alerts.extend(self._check_precipitation_alerts(weather_data, location))
                alerts.extend(self._check_wind_alerts(weather_data, location))
                alerts.extend(self._check_humidity_alerts(weather_data, location))
                
                # Save alerts to database
                for alert in alerts:
                    self._save_disaster_alert(alert)
            
        except Exception as e:
            logging.error(f"Error checking weather alerts: {e}")
        
        return alerts
    
    def check_agricultural_calamities(self, location: str, crop_type: str = "") -> List[Dict[str, Any]]:
        """Check for agricultural calamity conditions"""
        alerts = []
        
        try:
            # Check for drought conditions
            drought_alert = self._check_drought_conditions(location)
            if drought_alert:
                alerts.append(drought_alert)
            
            # Check for flood conditions
            flood_alert = self._check_flood_conditions(location)
            if flood_alert:
                alerts.append(flood_alert)
            
            # Check for pest outbreak conditions
            pest_alert = self._check_pest_outbreak_conditions(location, crop_type)
            if pest_alert:
                alerts.append(pest_alert)
            
            # Check for disease outbreak conditions
            disease_alert = self._check_disease_outbreak_conditions(location, crop_type)
            if disease_alert:
                alerts.append(disease_alert)
            
            # Save alerts to database
            for alert in alerts:
                self._save_disaster_alert(alert)
                
        except Exception as e:
            logging.error(f"Error checking agricultural calamities: {e}")
        
        return alerts
    
    def _get_weather_data(self, location: str) -> Optional[Dict[str, Any]]:
        """Get weather data from API"""
        try:
            # Current weather
            current_url = f"{self.weather_api_url}/weather"
            current_params = {
                'q': location,
                'appid': self.weather_api_key,
                'units': 'metric'
            }
            
            current_response = requests.get(current_url, params=current_params)
            
            if current_response.status_code == 200:
                current_data = current_response.json()
                
                # 5-day forecast
                forecast_url = f"{self.weather_api_url}/forecast"
                forecast_response = requests.get(forecast_url, params=current_params)
                
                forecast_data = forecast_response.json() if forecast_response.status_code == 200 else {}
                
                return {
                    'current': current_data,
                    'forecast': forecast_data
                }
            else:
                logging.warning(f"Weather API error: {current_response.status_code}")
                return None
                
        except Exception as e:
            logging.error(f"Error fetching weather data: {e}")
            return None
    
    def _check_temperature_alerts(self, weather_data: Dict[str, Any], location: str) -> List[Dict[str, Any]]:
        """Check for temperature-related alerts"""
        alerts = []
        
        try:
            current_temp = weather_data['current']['main']['temp']
            feels_like = weather_data['current']['main']['feels_like']
            
            # Extreme heat alert
            if current_temp > 45 or feels_like > 48:
                alerts.append({
                    'type': 'extreme_heat',
                    'severity': 'high',
                    'location': location,
                    'title': f'Extreme Heat Alert - {current_temp}°C',
                    'description': f'Dangerous heat conditions detected. Temperature: {current_temp}°C, Feels like: {feels_like}°C',
                    'precautions': [
                        'Provide shade and adequate water for livestock',
                        'Avoid field work during peak hours (11 AM - 4 PM)',
                        'Increase irrigation frequency for crops',
                        'Use mulching to protect soil moisture',
                        'Monitor animals for heat stress symptoms'
                    ]
                })
            
            # Cold wave alert
            elif current_temp < 5:
                alerts.append({
                    'type': 'cold_wave',
                    'severity': 'medium',
                    'location': location,
                    'title': f'Cold Wave Alert - {current_temp}°C',
                    'description': f'Severe cold conditions detected. Temperature: {current_temp}°C',
                    'precautions': [
                        'Protect sensitive crops with covers or tunnels',
                        'Provide warm shelter for livestock',
                        'Avoid irrigation during freezing hours',
                        'Use smoke or heaters in orchards if available',
                        'Harvest mature crops before frost damage'
                    ]
                })
            
            # Check forecast for sudden temperature changes
            if 'forecast' in weather_data and weather_data['forecast'].get('list'):
                forecast_temps = [item['main']['temp'] for item in weather_data['forecast']['list'][:8]]  # Next 24 hours
                temp_changes = [abs(forecast_temps[i+1] - forecast_temps[i]) for i in range(len(forecast_temps)-1)]
                
                if any(change > 15 for change in temp_changes):
                    alerts.append({
                        'type': 'temperature_fluctuation',
                        'severity': 'medium',
                        'location': location,
                        'title': 'Sudden Temperature Change Alert',
                        'description': 'Significant temperature fluctuations expected in the next 24 hours',
                        'precautions': [
                            'Monitor crops for stress symptoms',
                            'Adjust irrigation schedules accordingly',
                            'Prepare protective measures for sensitive plants',
                            'Check livestock housing adequacy'
                        ]
                    })
                    
        except Exception as e:
            logging.error(f"Error checking temperature alerts: {e}")
        
        return alerts
    
    def _check_precipitation_alerts(self, weather_data: Dict[str, Any], location: str) -> List[Dict[str, Any]]:
        """Check for precipitation-related alerts"""
        alerts = []
        
        try:
            # Check current conditions
            if 'rain' in weather_data['current']:
                current_rain = weather_data['current']['rain'].get('1h', 0)
                
                # Heavy rainfall alert
                if current_rain > 50:  # mm per hour
                    alerts.append({
                        'type': 'heavy_rainfall',
                        'severity': 'high',
                        'location': location,
                        'title': f'Heavy Rainfall Alert - {current_rain}mm/hr',
                        'description': f'Intense rainfall detected: {current_rain}mm per hour',
                        'precautions': [
                            'Ensure proper field drainage',
                            'Protect harvested crops from water damage',
                            'Avoid field operations until conditions improve',
                            'Monitor for waterlogging in low-lying areas',
                            'Secure livestock and equipment'
                        ]
                    })
            
            # Check forecast for extended dry periods
            if 'forecast' in weather_data and weather_data['forecast'].get('list'):
                rain_forecast = []
                for item in weather_data['forecast']['list'][:16]:  # Next 48 hours
                    rain_amount = item.get('rain', {}).get('3h', 0)
                    rain_forecast.append(rain_amount)
                
                total_rain = sum(rain_forecast)
                
                # Drought warning
                if total_rain < 5:  # Less than 5mm in 48 hours
                    alerts.append({
                        'type': 'drought_warning',
                        'severity': 'medium',
                        'location': location,
                        'title': 'Dry Conditions Alert',
                        'description': 'Extended dry period expected with minimal rainfall',
                        'precautions': [
                            'Increase irrigation frequency',
                            'Apply mulch to conserve soil moisture',
                            'Monitor crop water stress symptoms',
                            'Consider drought-resistant crop varieties',
                            'Implement water conservation measures'
                        ]
                    })
                
                # Flood warning
                elif total_rain > 100:  # More than 100mm in 48 hours
                    alerts.append({
                        'type': 'flood_warning',
                        'severity': 'high',
                        'location': location,
                        'title': f'Flood Warning - {total_rain}mm expected',
                        'description': f'Heavy rainfall expected: {total_rain}mm in next 48 hours',
                        'precautions': [
                            'Prepare drainage systems and channels',
                            'Move livestock to higher ground',
                            'Secure farm equipment and supplies',
                            'Harvest mature crops if possible',
                            'Avoid low-lying areas and flooded fields'
                        ]
                    })
                    
        except Exception as e:
            logging.error(f"Error checking precipitation alerts: {e}")
        
        return alerts
    
    def _check_wind_alerts(self, weather_data: Dict[str, Any], location: str) -> List[Dict[str, Any]]:
        """Check for wind-related alerts"""
        alerts = []
        
        try:
            wind_speed = weather_data['current']['wind']['speed']  # m/s
            wind_speed_kmh = wind_speed * 3.6  # Convert to km/h
            
            # High wind alert
            if wind_speed_kmh > 60:  # Strong winds
                severity = 'high' if wind_speed_kmh > 80 else 'medium'
                
                alerts.append({
                    'type': 'high_winds',
                    'severity': severity,
                    'location': location,
                    'title': f'High Wind Alert - {wind_speed_kmh:.1f} km/h',
                    'description': f'Strong winds detected: {wind_speed_kmh:.1f} km/h',
                    'precautions': [
                        'Secure loose farm equipment and structures',
                        'Avoid spraying operations',
                        'Protect young plants and seedlings',
                        'Check and reinforce greenhouse structures',
                        'Monitor tall crops for lodging risk'
                    ]
                })
                
        except Exception as e:
            logging.error(f"Error checking wind alerts: {e}")
        
        return alerts
    
    def _check_humidity_alerts(self, weather_data: Dict[str, Any], location: str) -> List[Dict[str, Any]]:
        """Check for humidity-related alerts"""
        alerts = []
        
        try:
            humidity = weather_data['current']['main']['humidity']
            
            # High humidity alert (disease risk)
            if humidity > 85:
                alerts.append({
                    'type': 'high_humidity',
                    'severity': 'medium',
                    'location': location,
                    'title': f'High Humidity Alert - {humidity}%',
                    'description': f'Very high humidity detected: {humidity}%. Increased disease risk.',
                    'precautions': [
                        'Monitor crops for fungal disease symptoms',
                        'Improve air circulation in greenhouses',
                        'Avoid overhead irrigation',
                        'Apply preventive fungicide treatments',
                        'Ensure proper plant spacing'
                    ]
                })
            
            # Low humidity alert
            elif humidity < 30:
                alerts.append({
                    'type': 'low_humidity',
                    'severity': 'low',
                    'location': location,
                    'title': f'Low Humidity Alert - {humidity}%',
                    'description': f'Very low humidity detected: {humidity}%. Increased water stress risk.',
                    'precautions': [
                        'Increase irrigation frequency',
                        'Use misting systems if available',
                        'Apply mulch to reduce evaporation',
                        'Monitor plants for water stress',
                        'Avoid transplanting during peak hours'
                    ]
                })
                
        except Exception as e:
            logging.error(f"Error checking humidity alerts: {e}")
        
        return alerts
    
    def _check_drought_conditions(self, location: str) -> Optional[Dict[str, Any]]:
        """Check for drought conditions using multiple indicators"""
        # This would integrate with drought monitoring APIs or databases
        # For now, return a mock drought alert based on conditions
        
        # Mock drought detection logic
        # In production, this would use:
        # - Rainfall data over extended periods
        # - Soil moisture indices
        # - Vegetation health indices
        # - Government drought declarations
        
        return None  # No drought detected in mock implementation
    
    def _check_flood_conditions(self, location: str) -> Optional[Dict[str, Any]]:
        """Check for flood conditions"""
        # This would integrate with flood monitoring systems
        # Mock implementation
        return None
    
    def _check_pest_outbreak_conditions(self, location: str, crop_type: str) -> Optional[Dict[str, Any]]:
        """Check for pest outbreak conditions"""
        # This would integrate with pest monitoring systems
        # Mock implementation for demonstration
        
        # Example: Locust outbreak alert
        # In production, this would use:
        # - FAO locust monitoring data
        # - Regional pest surveillance reports
        # - Weather conditions favorable for pest outbreaks
        
        return None
    
    def _check_disease_outbreak_conditions(self, location: str, crop_type: str) -> Optional[Dict[str, Any]]:
        """Check for disease outbreak conditions"""
        # This would integrate with plant disease monitoring systems
        # Mock implementation
        return None
    
    def _save_disaster_alert(self, alert: Dict[str, Any]):
        """Save disaster alert to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO disaster_alerts 
                    (alert_type, severity_level, location, title, description, precautions, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    alert['type'],
                    self.severity_levels.get(alert['severity'], 2),
                    alert['location'],
                    alert['title'],
                    alert['description'],
                    json.dumps(alert.get('precautions', [])),
                    datetime.now().isoformat()
                ))
                
                conn.commit()
                
        except Exception as e:
            logging.error(f"Error saving disaster alert: {e}")
    
    def get_active_alerts(self, location: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get active disaster alerts"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                query = '''
                    SELECT * FROM disaster_alerts 
                    WHERE is_active = 1
                '''
                params = []
                
                if location:
                    query += ' AND location LIKE ?'
                    params.append(f'%{location}%')
                
                query += ' ORDER BY severity_level DESC, created_at DESC'
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                
                alerts = []
                for row in rows:
                    alert = dict(zip(columns, row))
                    # Parse precautions JSON
                    try:
                        alert['precautions'] = json.loads(alert['precautions']) if alert['precautions'] else []
                    except:
                        alert['precautions'] = []
                    alerts.append(alert)
                
                return alerts
                
        except Exception as e:
            logging.error(f"Error getting active alerts: {e}")
            return []
    
    def create_mock_disaster_alert(self, alert_type: str = "cyclone") -> Dict[str, Any]:
        """Create a mock disaster alert for testing"""
        mock_alerts = {
            'cyclone': {
                'type': 'cyclone',
                'severity': 'high',
                'location': 'Maharashtra Coast',
                'title': '🌪️ Cyclone Alert - Severe Weather Warning',
                'description': 'A severe cyclonic storm is approaching the Maharashtra coast. Wind speeds up to 120 km/h expected with heavy rainfall.',
                'precautions': [
                    'Secure all farm equipment and structures',
                    'Harvest mature crops immediately if possible',
                    'Move livestock to safe shelters',
                    'Ensure adequate drainage in fields',
                    'Stock up on emergency supplies',
                    'Stay updated with weather bulletins'
                ]
            },
            'hailstorm': {
                'type': 'hailstorm',
                'severity': 'medium',
                'location': 'North Maharashtra',
                'title': '🧊 Hailstorm Warning - Crop Protection Alert',
                'description': 'Hailstorm conditions expected in the next 6-12 hours. Potential damage to standing crops.',
                'precautions': [
                    'Cover sensitive crops with protective nets',
                    'Move vehicles and equipment under cover',
                    'Harvest ripe fruits and vegetables',
                    'Secure greenhouse structures',
                    'Document any damage for insurance claims'
                ]
            },
            'drought': {
                'type': 'drought',
                'severity': 'high',
                'location': 'Marathwada Region',
                'title': '🏜️ Drought Alert - Water Conservation Critical',
                'description': 'Severe drought conditions declared. Rainfall deficit of 60% in the region.',
                'precautions': [
                    'Implement strict water conservation measures',
                    'Switch to drought-resistant crop varieties',
                    'Use drip irrigation systems',
                    'Apply mulching to conserve soil moisture',
                    'Consider crop insurance claims',
                    'Explore government drought relief schemes'
                ]
            }
        }
        
        return mock_alerts.get(alert_type, mock_alerts['cyclone'])
