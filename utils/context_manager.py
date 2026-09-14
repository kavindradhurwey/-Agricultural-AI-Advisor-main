"""
Comprehensive AI Context Manager
Ensures every AI conversation has full context: web, weather, history, profile, query, and agent state
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import sqlite3
import os
from dataclasses import dataclass, asdict
from urllib.parse import quote_plus
import requests
from bs4 import BeautifulSoup
import time

@dataclass
class ContextData:
    """Complete context data for AI conversations"""
    user_profile: Dict[str, Any]
    chat_history: List[Dict[str, Any]]
    weather_context: Dict[str, Any]
    web_search_results: List[Dict[str, Any]]
    agent_state: Dict[str, Any]
    query_analysis: Dict[str, Any]
    timestamp: str
    location_context: Dict[str, Any]
    seasonal_context: Dict[str, Any]
    market_context: Dict[str, Any]

class WebSearchEngine:
    """DuckDuckGo and fallback web search engine"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def search_duckduckgo(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Search using DuckDuckGo"""
        try:
            # DuckDuckGo Instant Answer API
            ddg_url = f"https://api.duckduckgo.com/?q={quote_plus(query)}&format=json&no_html=1&skip_disambig=1"
            
            response = self.session.get(ddg_url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                results = []
                
                # Abstract (main answer)
                if data.get('Abstract'):
                    results.append({
                        'title': data.get('Heading', 'DuckDuckGo Answer'),
                        'snippet': data.get('Abstract'),
                        'url': data.get('AbstractURL', ''),
                        'source': 'duckduckgo_instant'
                    })
                
                # Related topics
                for topic in data.get('RelatedTopics', [])[:3]:
                    if isinstance(topic, dict) and topic.get('Text'):
                        results.append({
                            'title': topic.get('FirstURL', '').split('/')[-1].replace('_', ' '),
                            'snippet': topic.get('Text'),
                            'url': topic.get('FirstURL', ''),
                            'source': 'duckduckgo_related'
                        })
                
                return results[:max_results]
                
        except Exception as e:
            self.logger.error(f"DuckDuckGo search error: {e}")
        
        return []
    
    def search_web_scraping(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Fallback web scraping search"""
        try:
            # Use DuckDuckGo HTML search as fallback
            search_url = f"https://duckduckgo.com/html/?q={quote_plus(query)}"
            
            response = self.session.get(search_url, timeout=15)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                results = []
                result_divs = soup.find_all('div', class_='result')
                
                for div in result_divs[:max_results]:
                    try:
                        title_elem = div.find('a', class_='result__a')
                        snippet_elem = div.find('a', class_='result__snippet')
                        
                        if title_elem and snippet_elem:
                            title = title_elem.get_text(strip=True)
                            snippet = snippet_elem.get_text(strip=True)
                            url = title_elem.get('href', '')
                            
                            results.append({
                                'title': title,
                                'snippet': snippet,
                                'url': url,
                                'source': 'duckduckgo_scraping'
                            })
                    except Exception as e:
                        continue
                
                return results
                
        except Exception as e:
            self.logger.error(f"Web scraping search error: {e}")
        
        return []
    
    def search_agricultural_sources(self, query: str) -> List[Dict[str, Any]]:
        """Search specific agricultural sources"""
        agricultural_sources = [
            {
                'name': 'ICAR',
                'base_url': 'https://icar.org.in',
                'search_pattern': '/search?q={}'
            },
            {
                'name': 'Krishi Jagran',
                'base_url': 'https://krishijagran.com',
                'search_pattern': '/search?q={}'
            },
            {
                'name': 'Agriculture.com',
                'base_url': 'https://agriculture.com',
                'search_pattern': '/search?q={}'
            }
        ]
        
        results = []
        
        for source in agricultural_sources:
            try:
                # Simple search implementation
                search_query = f"site:{source['base_url']} {query}"
                ddg_results = self.search_duckduckgo(search_query, max_results=2)
                
                for result in ddg_results:
                    result['source'] = f"agricultural_{source['name'].lower()}"
                    results.append(result)
                    
            except Exception as e:
                self.logger.error(f"Error searching {source['name']}: {e}")
        
        return results
    
    def comprehensive_search(self, query: str, include_agricultural: bool = True) -> List[Dict[str, Any]]:
        """Perform comprehensive web search"""
        all_results = []
        
        # DuckDuckGo instant answers
        ddg_results = self.search_duckduckgo(query, max_results=3)
        all_results.extend(ddg_results)
        
        # Agricultural sources if relevant
        if include_agricultural and any(keyword in query.lower() for keyword in 
                                      ['crop', 'farm', 'agriculture', 'plant', 'soil', 'fertilizer', 'pest', 'disease']):
            agri_results = self.search_agricultural_sources(query)
            all_results.extend(agri_results[:2])
        
        # Fallback web scraping if needed
        if len(all_results) < 3:
            scraping_results = self.search_web_scraping(query, max_results=5-len(all_results))
            all_results.extend(scraping_results)
        
        # Remove duplicates and limit results
        seen_urls = set()
        unique_results = []
        
        for result in all_results:
            url = result.get('url', '')
            if url not in seen_urls:
                seen_urls.add(url)
                unique_results.append(result)
                
                if len(unique_results) >= 5:
                    break
        
        return unique_results

class ComprehensiveContextManager:
    """Manages comprehensive context for AI conversations"""
    
    def __init__(self, db_path: str = "data/agricultural_advisor.db"):
        self.db_path = db_path
        self.web_search = WebSearchEngine()
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Context cache
        self.context_cache = {}
        self.cache_duration = 300  # 5 minutes
    
    def get_user_profile_context(self, user_id: int) -> Dict[str, Any]:
        """Get comprehensive user profile context"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # User basic info
                cursor.execute('''
                    SELECT username, email, location, phone, created_at, last_login
                    FROM users WHERE id = ?
                ''', (user_id,))
                user_data = cursor.fetchone()
                
                if not user_data:
                    return {}
                
                # User profile details
                cursor.execute('''
                    SELECT * FROM user_profiles WHERE user_id = ?
                ''', (user_id,))
                profile_data = cursor.fetchone()
                
                profile_context = {
                    'user_id': user_id,
                    'username': user_data[0],
                    'email': user_data[1],
                    'location': user_data[2],
                    'phone': user_data[3],
                    'member_since': user_data[4],
                    'last_active': user_data[5]
                }
                
                if profile_data:
                    profile_context.update({
                        'farm_size': profile_data[2],
                        'crops': json.loads(profile_data[3]) if profile_data[3] else [],
                        'farming_type': profile_data[4],
                        'experience_years': profile_data[5],
                        'preferred_language': profile_data[6],
                        'soil_type': profile_data[7],
                        'irrigation_type': profile_data[8],
                        'annual_income': profile_data[9],
                        'education_level': profile_data[10],
                        'technology_adoption': profile_data[11]
                    })
                
                return profile_context
                
        except Exception as e:
            self.logger.error(f"Error getting user profile context: {e}")
            return {}
    
    def get_chat_history_context(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent chat history for context"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT user_message, ai_response, timestamp, agent_used
                    FROM chat_history 
                    WHERE user_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                ''', (user_id, limit))
                
                history = []
                for row in cursor.fetchall():
                    history.append({
                        'user_message': row[0],
                        'ai_response': row[1],
                        'timestamp': row[2],
                        'agent_used': row[3]
                    })
                
                return list(reversed(history))  # Chronological order
                
        except Exception as e:
            self.logger.error(f"Error getting chat history: {e}")
            return []
    
    def get_weather_context(self, location: str) -> Dict[str, Any]:
        """Get comprehensive weather context"""
        try:
            # Import weather service
            from .weather_service import WeatherService
            
            weather_service = WeatherService()
            weather_data = weather_service.get_weather_data(location)
            
            if weather_data:
                # Add agricultural insights
                agricultural_insights = weather_service.get_agricultural_insights(weather_data)
                
                return {
                    'current_weather': weather_data.get('current', {}),
                    'forecast': weather_data.get('forecast', [])[:5],  # 5-day forecast
                    'agricultural_insights': agricultural_insights,
                    'alerts': weather_data.get('alerts', []),
                    'last_updated': datetime.now().isoformat()
                }
            
        except Exception as e:
            self.logger.error(f"Error getting weather context: {e}")
        
        return {}
    
    def get_web_search_context(self, query: str, user_profile: Dict) -> List[Dict[str, Any]]:
        """Get web search context for the query"""
        try:
            # Check cache first
            cache_key = f"web_search_{hash(query)}"
            if cache_key in self.context_cache:
                cached_data, timestamp = self.context_cache[cache_key]
                if time.time() - timestamp < self.cache_duration:
                    return cached_data
            
            # Enhance query with user context
            enhanced_query = self.enhance_query_with_context(query, user_profile)
            
            # Perform comprehensive search
            search_results = self.web_search.comprehensive_search(enhanced_query)
            
            # Cache results
            self.context_cache[cache_key] = (search_results, time.time())
            
            return search_results
            
        except Exception as e:
            self.logger.error(f"Error getting web search context: {e}")
            return []
    
    def enhance_query_with_context(self, query: str, user_profile: Dict) -> str:
        """Enhance search query with user context"""
        try:
            enhanced_parts = [query]
            
            # Add location context
            if user_profile.get('location'):
                enhanced_parts.append(f"in {user_profile['location']}")
            
            # Add crop context if relevant
            crops = user_profile.get('crops', [])
            if crops and any(keyword in query.lower() for keyword in ['crop', 'plant', 'farming', 'agriculture']):
                enhanced_parts.append(f"for {' '.join(crops[:2])}")
            
            # Add farming type context
            farming_type = user_profile.get('farming_type')
            if farming_type:
                enhanced_parts.append(f"{farming_type} farming")
            
            return ' '.join(enhanced_parts)
            
        except Exception as e:
            self.logger.error(f"Error enhancing query: {e}")
            return query
    
    def analyze_query_intent(self, query: str, user_profile: Dict) -> Dict[str, Any]:
        """Analyze query intent and context"""
        try:
            analysis = {
                'original_query': query,
                'query_length': len(query.split()),
                'query_type': 'general',
                'confidence': 0.5,
                'suggested_agents': [],
                'keywords': [],
                'entities': [],
                'urgency': 'normal'
            }
            
            query_lower = query.lower()
            
            # Detect query type and suggested agents
            if any(word in query_lower for word in ['weather', 'rain', 'temperature', 'climate']):
                analysis['query_type'] = 'weather'
                analysis['suggested_agents'] = ['weather_agent']
                analysis['confidence'] = 0.9
            
            elif any(word in query_lower for word in ['disease', 'pest', 'infection', 'spots', 'leaves']):
                analysis['query_type'] = 'disease'
                analysis['suggested_agents'] = ['disease_agent']
                analysis['confidence'] = 0.9
            
            elif any(word in query_lower for word in ['price', 'market', 'sell', 'buy', 'cost']):
                analysis['query_type'] = 'market'
                analysis['suggested_agents'] = ['financial_agent']
                analysis['confidence'] = 0.8
            
            elif any(word in query_lower for word in ['loan', 'subsidy', 'scheme', 'government', 'policy']):
                analysis['query_type'] = 'financial'
                analysis['suggested_agents'] = ['financial_agent', 'policy_agent']
                analysis['confidence'] = 0.9
            
            elif any(word in query_lower for word in ['plant', 'seed', 'fertilizer', 'irrigation']):
                analysis['query_type'] = 'crop_management'
                analysis['suggested_agents'] = ['crop_agent']
                analysis['confidence'] = 0.8
            
            # Detect urgency
            if any(word in query_lower for word in ['urgent', 'emergency', 'help', 'immediate', 'critical']):
                analysis['urgency'] = 'high'
            elif any(word in query_lower for word in ['soon', 'quickly', 'fast']):
                analysis['urgency'] = 'medium'
            
            # Extract keywords
            agricultural_keywords = [
                'crop', 'plant', 'seed', 'fertilizer', 'pesticide', 'irrigation', 'harvest',
                'soil', 'weather', 'rain', 'drought', 'disease', 'pest', 'market', 'price',
                'loan', 'subsidy', 'scheme', 'government', 'organic', 'farming'
            ]
            
            analysis['keywords'] = [word for word in agricultural_keywords if word in query_lower]
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing query: {e}")
            return {'original_query': query, 'query_type': 'general'}
    
    def get_seasonal_context(self, location: str, user_profile: Dict) -> Dict[str, Any]:
        """Get seasonal farming context"""
        try:
            current_month = datetime.now().month
            
            # Define seasonal activities (simplified for India)
            seasonal_activities = {
                'kharif': {
                    'months': [6, 7, 8, 9, 10],
                    'activities': ['sowing', 'monsoon_farming', 'pest_management'],
                    'crops': ['rice', 'cotton', 'sugarcane', 'maize']
                },
                'rabi': {
                    'months': [11, 12, 1, 2, 3],
                    'activities': ['winter_sowing', 'irrigation_management', 'harvesting'],
                    'crops': ['wheat', 'barley', 'peas', 'mustard']
                },
                'zaid': {
                    'months': [4, 5],
                    'activities': ['summer_crops', 'water_management'],
                    'crops': ['watermelon', 'cucumber', 'fodder']
                }
            }
            
            current_season = None
            for season, data in seasonal_activities.items():
                if current_month in data['months']:
                    current_season = season
                    break
            
            if current_season:
                season_data = seasonal_activities[current_season]
                user_crops = user_profile.get('crops', [])
                
                # Find relevant activities for user's crops
                relevant_activities = []
                for crop in user_crops:
                    if crop.lower() in [c.lower() for c in season_data['crops']]:
                        relevant_activities.extend(season_data['activities'])
                
                return {
                    'current_season': current_season,
                    'month': current_month,
                    'seasonal_activities': list(set(relevant_activities)),
                    'recommended_crops': season_data['crops'],
                    'user_relevant_crops': [c for c in user_crops if c.lower() in [cr.lower() for cr in season_data['crops']]]
                }
            
        except Exception as e:
            self.logger.error(f"Error getting seasonal context: {e}")
        
        return {}
    
    def get_market_context(self, user_profile: Dict) -> Dict[str, Any]:
        """Get market price context for user's crops"""
        try:
            # This would integrate with market price APIs
            # For now, return mock data structure
            user_crops = user_profile.get('crops', [])
            location = user_profile.get('location', '')
            
            market_context = {
                'location': location,
                'last_updated': datetime.now().isoformat(),
                'crop_prices': [],
                'market_trends': [],
                'price_alerts': []
            }
            
            # Mock price data for user's crops
            for crop in user_crops[:3]:  # Limit to 3 crops
                market_context['crop_prices'].append({
                    'crop': crop,
                    'current_price': 2500,  # Mock price
                    'price_change': 5.2,
                    'market': 'Local Mandi',
                    'quality': 'Grade A'
                })
            
            return market_context
            
        except Exception as e:
            self.logger.error(f"Error getting market context: {e}")
            return {}
    
    def build_comprehensive_context(self, user_id: int, query: str, agent_state: Dict = None) -> ContextData:
        """Build comprehensive context for AI conversation"""
        try:
            # Get user profile
            user_profile = self.get_user_profile_context(user_id)
            
            # Get chat history
            chat_history = self.get_chat_history_context(user_id)
            
            # Get weather context
            weather_context = {}
            if user_profile.get('location'):
                weather_context = self.get_weather_context(user_profile['location'])
            
            # Get web search context
            web_search_results = self.get_web_search_context(query, user_profile)
            
            # Analyze query
            query_analysis = self.analyze_query_intent(query, user_profile)
            
            # Get seasonal context
            seasonal_context = self.get_seasonal_context(user_profile.get('location', ''), user_profile)
            
            # Get market context
            market_context = self.get_market_context(user_profile)
            
            # Build location context
            location_context = {
                'primary_location': user_profile.get('location', ''),
                'coordinates': {},  # Would be populated from geocoding
                'timezone': 'Asia/Kolkata',  # Default for India
                'region_type': 'agricultural'  # Could be detected
            }
            
            return ContextData(
                user_profile=user_profile,
                chat_history=chat_history,
                weather_context=weather_context,
                web_search_results=web_search_results,
                agent_state=agent_state or {},
                query_analysis=query_analysis,
                timestamp=datetime.now().isoformat(),
                location_context=location_context,
                seasonal_context=seasonal_context,
                market_context=market_context
            )
            
        except Exception as e:
            self.logger.error(f"Error building comprehensive context: {e}")
            return ContextData(
                user_profile={},
                chat_history=[],
                weather_context={},
                web_search_results=[],
                agent_state={},
                query_analysis={'original_query': query},
                timestamp=datetime.now().isoformat(),
                location_context={},
                seasonal_context={},
                market_context={}
            )
    
    def format_context_for_ai(self, context: ContextData) -> str:
        """Format comprehensive context for AI consumption"""
        try:
            context_parts = []
            
            # User profile context
            if context.user_profile:
                profile_summary = f"""
USER PROFILE:
- Location: {context.user_profile.get('location', 'Not specified')}
- Farm Size: {context.user_profile.get('farm_size', 'Not specified')} acres
- Crops: {', '.join(context.user_profile.get('crops', []))}
- Experience: {context.user_profile.get('experience_years', 'Not specified')} years
- Farming Type: {context.user_profile.get('farming_type', 'Not specified')}
- Language: {context.user_profile.get('preferred_language', 'English')}
"""
                context_parts.append(profile_summary)
            
            # Weather context
            if context.weather_context:
                weather_summary = f"""
CURRENT WEATHER:
- Temperature: {context.weather_context.get('current_weather', {}).get('temperature', 'N/A')}°C
- Conditions: {context.weather_context.get('current_weather', {}).get('description', 'N/A')}
- Humidity: {context.weather_context.get('current_weather', {}).get('humidity', 'N/A')}%
- Agricultural Insights: {context.weather_context.get('agricultural_insights', 'No specific insights')}
"""
                context_parts.append(weather_summary)
            
            # Seasonal context
            if context.seasonal_context:
                seasonal_summary = f"""
SEASONAL CONTEXT:
- Current Season: {context.seasonal_context.get('current_season', 'N/A')}
- Seasonal Activities: {', '.join(context.seasonal_context.get('seasonal_activities', []))}
- Relevant Crops: {', '.join(context.seasonal_context.get('user_relevant_crops', []))}
"""
                context_parts.append(seasonal_summary)
            
            # Recent web search results
            if context.web_search_results:
                web_summary = "RECENT WEB INFORMATION:\n"
                for i, result in enumerate(context.web_search_results[:3], 1):
                    web_summary += f"{i}. {result.get('title', 'No title')}: {result.get('snippet', 'No description')[:100]}...\n"
                context_parts.append(web_summary)
            
            # Query analysis
            if context.query_analysis:
                query_summary = f"""
QUERY ANALYSIS:
- Type: {context.query_analysis.get('query_type', 'general')}
- Urgency: {context.query_analysis.get('urgency', 'normal')}
- Suggested Agents: {', '.join(context.query_analysis.get('suggested_agents', []))}
- Keywords: {', '.join(context.query_analysis.get('keywords', []))}
"""
                context_parts.append(query_summary)
            
            # Recent chat history
            if context.chat_history:
                history_summary = "RECENT CONVERSATION:\n"
                for msg in context.chat_history[-3:]:  # Last 3 exchanges
                    history_summary += f"User: {msg.get('user_message', '')[:100]}...\n"
                    history_summary += f"AI: {msg.get('ai_response', '')[:100]}...\n\n"
                context_parts.append(history_summary)
            
            return "\n".join(context_parts)
            
        except Exception as e:
            self.logger.error(f"Error formatting context for AI: {e}")
            return f"Context available for user query: {context.query_analysis.get('original_query', 'Unknown query')}"

# Global context manager instance
context_manager = ComprehensiveContextManager()
