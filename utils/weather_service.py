import requests
import os
import logging
from typing import Dict, Any, Optional, List

class WeatherService:
    """
    Weather service integration for agricultural insights
    """
    
    def __init__(self):
        self.api_key = os.getenv("WEATHER_API_KEY", "ada8ad8fda2446ceb3e185217250808")
        self.base_url = "http://api.weatherapi.com/v1"
    
    def get_weather_data(self, location: str, days: int = 3) -> Optional[Dict[str, Any]]:
        """Get current weather and forecast data for a location"""
        try:
            days = max(1, min(days, 3))  # Free tier supports up to 3-day forecast
            # Current weather endpoint
            current_url = f"{self.base_url}/current.json"
            current_params = {
                'key': self.api_key,
                'q': location,
                'aqi': 'yes'
            }
            
            # Forecast endpoint
            forecast_url = f"{self.base_url}/forecast.json"
            forecast_params = {
                'key': self.api_key,
                'q': location,
                'days': days,
                'aqi': 'yes',
                'alerts': 'yes'
            }
            
            # Make API requests
            current_response = requests.get(current_url, params=current_params, timeout=10)
            forecast_response = requests.get(forecast_url, params=forecast_params, timeout=10)

            current_ok = current_response.status_code == 200
            forecast_ok = forecast_response.status_code == 200

            if not current_ok and not forecast_ok:
                logging.error(f"Weather API error: current={current_response.status_code}, forecast={forecast_response.status_code}")
                return None

            current_data = current_response.json() if current_ok else None
            forecast_data = forecast_response.json() if forecast_ok else None

            # Combine whatever we have
            weather_data = {}
            if current_data:
                weather_data['location'] = current_data.get('location', {})
                weather_data['current'] = current_data.get('current', {})
            if forecast_data:
                # Location is also present in forecast response
                if not weather_data.get('location'):
                    weather_data['location'] = forecast_data.get('location', {})
                weather_data['forecast'] = forecast_data.get('forecast', {})
                weather_data['alerts'] = forecast_data.get('alerts', {})

            # If current is missing but forecast exists, synthesize a minimal current snapshot from first forecast day
            if not weather_data.get('current') and weather_data.get('forecast', {}).get('forecastday'):
                day0 = weather_data['forecast']['forecastday'][0]['day']
                condition = day0.get('condition', {})
                weather_data['current'] = {
                    'temp_c': day0.get('avgtemp_c', 0),
                    'feelslike_c': day0.get('avgtemp_c', 0),
                    'humidity': day0.get('avghumidity', 0),
                    'wind_kph': day0.get('maxwind_kph', 0),
                    'pressure_mb': 0,
                    'vis_km': 0,
                    'uv': day0.get('uv', 0),
                    'condition': {
                        'text': condition.get('text', 'Forecast only'),
                        'icon': condition.get('icon', '')
                    }
                }

            # Add agricultural insights if current is present
            if weather_data.get('current'):
                weather_data['agricultural_insights'] = self._generate_agricultural_insights(weather_data)

            return weather_data if weather_data else None
                
        except Exception as e:
            logging.error(f"Error fetching weather data: {str(e)}")
            return None
    
    def _generate_agricultural_insights(self, weather_data: Dict) -> Dict[str, Any]:
        """Generate agricultural insights based on weather data"""
        try:
            current = weather_data['current']
            
            insights = {
                'irrigation_advice': self._get_irrigation_advice(current),
                'crop_protection': self._get_crop_protection_advice(current),
                'field_work_conditions': self._get_field_work_advice(current),
                'pest_disease_risk': self._assess_pest_disease_risk(current)
            }
            
            return insights
            
        except Exception as e:
            logging.error(f"Error generating agricultural insights: {str(e)}")
            return {}
    
    def _get_irrigation_advice(self, current_weather: Dict) -> str:
        """Get irrigation advice based on current weather"""
        try:
            humidity = current_weather.get('humidity', 50)
            temp = current_weather.get('temp_c', 25)
            condition = current_weather.get('condition', {}).get('text', '').lower()
            
            if 'rain' in condition or humidity > 80:
                return "🌧️ High humidity/rain detected. Reduce irrigation frequency."
            elif temp > 35 and humidity < 40:
                return "🔥 Hot and dry conditions. Increase irrigation frequency."
            elif temp > 30 and humidity < 60:
                return "☀️ Warm conditions. Maintain regular irrigation schedule."
            else:
                return "🌤️ Moderate conditions. Standard irrigation schedule is sufficient."
                
        except Exception as e:
            return "❓ Unable to determine irrigation advice."
    
    def _get_crop_protection_advice(self, current_weather: Dict) -> str:
        """Get crop protection advice based on weather"""
        try:
            wind_kph = current_weather.get('wind_kph', 0)
            condition = current_weather.get('condition', {}).get('text', '').lower()
            uv = current_weather.get('uv', 5)
            
            advice = []
            
            if wind_kph > 25:
                advice.append("💨 Strong winds detected. Secure young plants and check for damage.")
            
            if 'storm' in condition or 'thunder' in condition:
                advice.append("⛈️ Storm conditions. Avoid field work and protect crops if possible.")
            
            if uv > 8:
                advice.append("☀️ High UV levels. Consider shade nets for sensitive crops.")
            
            if 'hail' in condition:
                advice.append("🧊 Hail risk. Cover sensitive crops immediately.")
            
            return " ".join(advice) if advice else "✅ Current weather conditions are favorable for crops."
            
        except Exception as e:
            return "❓ Unable to determine crop protection advice."
    
    def _get_field_work_advice(self, current_weather: Dict) -> str:
        """Get field work advice based on weather conditions"""
        try:
            condition = current_weather.get('condition', {}).get('text', '').lower()
            humidity = current_weather.get('humidity', 50)
            temp = current_weather.get('temp_c', 25)
            wind_kph = current_weather.get('wind_kph', 0)
            
            if 'rain' in condition or humidity > 85:
                return "⛔ Avoid field work. Wet conditions can damage soil structure."
            elif temp > 40:
                return "🌡️ Extreme heat. Limit field work to early morning or evening."
            elif wind_kph > 30:
                return "💨 Strong winds. Avoid spraying and be cautious with machinery."
            elif temp < 5:
                return "🥶 Very cold. Limit outdoor activities and protect workers."
            else:
                return "✅ Good conditions for field work."
                
        except Exception as e:
            return "❓ Unable to determine field work conditions."
    
    def _assess_pest_disease_risk(self, current_weather: Dict) -> str:
        """Assess pest and disease risk based on weather"""
        try:
            humidity = current_weather.get('humidity', 50)
            temp = current_weather.get('temp_c', 25)
            condition = current_weather.get('condition', {}).get('text', '').lower()
            
            risk_factors = []
            
            if humidity > 80 and temp > 20:
                risk_factors.append("🦠 High humidity + warm temp = increased fungal disease risk")
            
            if temp > 30 and humidity < 40:
                risk_factors.append("🐛 Hot, dry conditions may increase insect pest activity")
            
            if 'rain' in condition and temp > 25:
                risk_factors.append("☔ Wet, warm conditions favor bacterial diseases")
            
            if len(risk_factors) == 0:
                return "✅ Low pest and disease risk under current conditions."
            else:
                return " | ".join(risk_factors)
                
        except Exception as e:
            return "❓ Unable to assess pest and disease risk."
    
    def get_historical_weather(self, location: str, date: str) -> Optional[Dict]:
        """Get historical weather data for analysis"""
        try:
            url = f"{self.base_url}/history.json"
            params = {
                'key': self.api_key,
                'q': location,
                'dt': date
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                logging.error(f"Historical weather API error: {response.status_code}")
                return None
                
        except Exception as e:
            logging.error(f"Error fetching historical weather: {str(e)}")
            return None
    
    def get_weather_alerts(self, location: str) -> List[Dict]:
        """Get weather alerts for the location"""
        try:
            url = f"{self.base_url}/forecast.json"
            params = {
                'key': self.api_key,
                'q': location,
                'days': 3,
                'alerts': 'yes'
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return data.get('alerts', {}).get('alert', [])
            else:
                return []
                
        except Exception as e:
            logging.error(f"Error fetching weather alerts: {str(e)}")
            return []
