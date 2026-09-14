import requests
import os
import json

class WeatherAgent:
    def __init__(self):
        self.api_key = os.getenv("OPENWEATHER_API_KEY")
        self.base_url = "http://api.weatherapi.com/v1"
    
    def get_weather(self, location):
        """Get current weather data for a location"""
        try:
            # Current weather
            current_url = f"{self.base_url}/current.json"
            params = {
                'key': self.api_key,
                'q': location,
                'aqi': 'yes'
            }
            
            response = requests.get(current_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Extract relevant weather data
            current = data['current']
            location_info = data['location']
            
            weather_data = {
                'location': f"{location_info['name']}, {location_info['region']}, {location_info['country']}",
                'temperature': current['temp_c'],
                'feels_like': current['feelslike_c'],
                'humidity': current['humidity'],
                'wind_speed': current['wind_kph'],
                'wind_direction': current['wind_dir'],
                'pressure': current['pressure_mb'],
                'visibility': current['vis_km'],
                'uv_index': current['uv'],
                'condition': current['condition']['text'],
                'icon': current['condition']['icon']
            }
            
            # Add agricultural advice based on weather
            weather_data['agricultural_advice'] = self.get_agricultural_advice(weather_data)
            
            return weather_data
            
        except requests.exceptions.RequestException as e:
            return {
                'error': f"Failed to fetch weather data: {str(e)}",
                'location': location,
                'temperature': 'N/A',
                'humidity': 'N/A',
                'wind_speed': 'N/A',
                'condition': 'Data unavailable',
                'agricultural_advice': 'Please check your internet connection and try again.'
            }
        except Exception as e:
            return {
                'error': f"Weather service error: {str(e)}",
                'location': location,
                'temperature': 'N/A',
                'humidity': 'N/A',
                'wind_speed': 'N/A',
                'condition': 'Service unavailable',
                'agricultural_advice': 'Weather service is temporarily unavailable.'
            }
    
    def get_forecast(self, location, days=7):
        """Get weather forecast for specified days"""
        try:
            forecast_url = f"{self.base_url}/forecast.json"
            params = {
                'key': self.api_key,
                'q': location,
                'days': min(days, 10),  # API limits to 10 days
                'aqi': 'yes',
                'alerts': 'yes'
            }
            
            response = requests.get(forecast_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            forecast_data = []
            for day in data['forecast']['forecastday']:
                day_data = {
                    'date': day['date'],
                    'max_temp': day['day']['maxtemp_c'],
                    'min_temp': day['day']['mintemp_c'],
                    'humidity': day['day']['avghumidity'],
                    'condition': day['day']['condition']['text'],
                    'chance_of_rain': day['day']['daily_chance_of_rain'],
                    'rainfall': day['day']['totalprecip_mm']
                }
                forecast_data.append(day_data)
            
            return forecast_data
            
        except Exception as e:
            return [{'error': f"Failed to fetch forecast: {str(e)}"}]
    
    def get_agricultural_advice(self, weather_data):
        """Generate agricultural advice based on weather conditions"""
        try:
            temp = weather_data.get('temperature', 0)
            humidity = weather_data.get('humidity', 0)
            condition = weather_data.get('condition', '').lower()
            
            advice = []
            
            # Temperature-based advice
            if temp > 35:
                advice.append("🌡️ High temperature alert: Increase irrigation frequency and provide shade for sensitive crops.")
            elif temp < 10:
                advice.append("❄️ Low temperature warning: Protect crops from frost damage, use protective covers.")
            
            # Humidity-based advice
            if humidity > 80:
                advice.append("💧 High humidity: Monitor for fungal diseases, ensure good air circulation.")
            elif humidity < 30:
                advice.append("🏜️ Low humidity: Increase watering and consider mulching to retain soil moisture.")
            
            # Condition-based advice
            if any(word in condition for word in ['rain', 'shower', 'storm']):
                advice.append("🌧️ Rainy conditions: Ensure proper drainage and avoid field operations.")
            elif 'sunny' in condition or 'clear' in condition:
                advice.append("☀️ Clear weather: Good time for field operations and harvest activities.")
            elif 'cloudy' in condition:
                advice.append("☁️ Cloudy conditions: Moderate temperature - suitable for planting and field work.")
            
            return " ".join(advice) if advice else "Weather conditions are suitable for normal agricultural activities."
            
        except Exception as e:
            return "Agricultural advice is currently unavailable due to a technical issue."
    
    def get_response(self, query):
        """Handle weather-related queries"""
        # Extract location from query (simple approach)
        words = query.split()
        # Look for location indicators
        location_keywords = ['in', 'at', 'for', 'near']
        location = "Mumbai"  # Default location
        
        for i, word in enumerate(words):
            if word.lower() in location_keywords and i + 1 < len(words):
                location = " ".join(words[i+1:])
                break
        
        weather_data = self.get_weather(location)
        
        # Format response
        if 'error' not in weather_data:
            response = f"""
            **Weather Information for {weather_data['location']}:**
            
            🌡️ **Temperature:** {weather_data['temperature']}°C (feels like {weather_data['feels_like']}°C)
            💧 **Humidity:** {weather_data['humidity']}%
            🌬️ **Wind:** {weather_data['wind_speed']} km/h {weather_data['wind_direction']}
            🔍 **Visibility:** {weather_data['visibility']} km
            ☀️ **UV Index:** {weather_data['uv_index']}
            📊 **Pressure:** {weather_data['pressure']} mb
            🌤️ **Condition:** {weather_data['condition']}
            
            **Agricultural Recommendations:**
            {weather_data['agricultural_advice']}
            """
            
            return response
        else:
            return f"Sorry, I couldn't fetch weather data: {weather_data['error']}"
