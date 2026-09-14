import os
import json
from groq import Groq
from typing import Dict, List, Any, Optional
from datetime import datetime
import requests
try:
    from ddgs import DDGS  # new package name
except Exception:
    from duckduckgo_search import DDGS  # fallback for older installs
import yfinance as yf
from agents.policy_agent import PolicyAgent
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.notification_manager import NotificationManager
from utils.disaster_monitor import DisasterMonitor
from utils.weather_service import WeatherService
from utils.disease_detector import DiseaseDetector
from utils.context_manager import context_manager, ContextData
from utils.notification_triggers import notification_engine
from utils.policy_scheduler import policy_scheduler

class AgricultureAgentTeam:
    """
    Multi-agent system for agricultural assistance using Groq API
    """
    
    def __init__(self):
        self.groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.ddgs = DDGS()
        self.weather_api_key = os.getenv("OPENWEATHER_API_KEY")
        self.policy_agent = PolicyAgent()
        
        # Initialize Weather Service
        self.weather_service = WeatherService()
        
        # Initialize Disease Detector
        self.disease_detector = DiseaseDetector()
        
        # Initialize Notification Manager
        self.notification_manager = NotificationManager()
        
        # Initialize Disaster Monitor
        self.disaster_monitor = DisasterMonitor()
        
        # Initialize advanced features
        self.context_manager = context_manager
        self.notification_engine = notification_engine
        self.policy_scheduler = policy_scheduler
        
        # Setup scheduler callbacks
        self.setup_scheduler_callbacks()
        
        # Start scheduler if not already running
        if not self.policy_scheduler.running:
            self.policy_scheduler.start()
        
    def setup_scheduler_callbacks(self):
        """Setup callbacks for scheduled tasks"""
        # Policy scraping callback
        self.policy_scheduler.register_callback(
            "policy_scraping_daily",
            self.scheduled_policy_scraping
        )
        
        # Weather alerts callback
        self.policy_scheduler.register_callback(
            "weather_alerts_check",
            self.scheduled_weather_alerts
        )
        
        # Market price update callback
        self.policy_scheduler.register_callback(
            "market_price_update",
            self.scheduled_market_updates
        )
        
        # User notification digest callback
        self.policy_scheduler.register_callback(
            "user_notification_digest",
            self.scheduled_notification_digest
        )
    
    def scheduled_policy_scraping(self) -> bool:
        """Scheduled policy scraping task"""
        try:
            print("🏛️ Running scheduled policy scraping...")
            # Force update government schemes
            self.policy_agent.force_update_schemes()
            
            # Check for new schemes and trigger notifications
            # This would compare with previous data and trigger notifications for new schemes
            return True
        except Exception as e:
            print(f"Error in scheduled policy scraping: {e}")
            return False
    
    def scheduled_weather_alerts(self) -> bool:
        """Scheduled weather alerts check"""
        try:
            print("🌤️ Running scheduled weather alerts check...")
            # This would check weather for all users and trigger alerts
            # Implementation would iterate through active users and check weather conditions
            return True
        except Exception as e:
            print(f"Error in scheduled weather alerts: {e}")
            return False
    
    def scheduled_market_updates(self) -> bool:
        """Scheduled market price updates"""
        try:
            print("📈 Running scheduled market price updates...")
            # This would fetch latest market prices and trigger price alerts
            return True
        except Exception as e:
            print(f"Error in scheduled market updates: {e}")
            return False
    
    def scheduled_notification_digest(self) -> bool:
        """Scheduled notification digest"""
        try:
            print("📢 Running scheduled notification digest...")
            # This would compile and send daily digest notifications
            return True
        except Exception as e:
            print(f"Error in scheduled notification digest: {e}")
            return False
    
    def search_web(self, query: str, max_results: int = 5) -> List[Dict]:
        """Enhanced web search with DuckDuckGo integration"""
        try:
            # Ensure query is valid
            if not query or not str(query).strip():
                return []
                
            query = str(query).strip()
            
            # Use the comprehensive context manager's web search
            search_results = self.context_manager.web_search.comprehensive_search(
                query, include_agricultural=True
            )
            
            # Ensure search_results is a list
            search_results = search_results or []
            
            # Convert to expected format with defensive checks
            formatted_results = []
            for result in search_results[:max_results]:
                if isinstance(result, dict):
                    formatted_results.append({
                        'title': str(result.get('title', '')).strip(),
                        'body': str(result.get('snippet', '')).strip(),
                        'href': str(result.get('url', '')).strip(),
                        'source': str(result.get('source', 'web')).strip()
                    })
            
            return formatted_results
            
        except Exception as e:
            print(f"Enhanced web search error: {e}")
            # Fallback to original method
            try:
                results = list(self.ddgs.text(f"agriculture {query} India farming", max_results=max_results))
                unique_results = []
                for result in results:
                    if isinstance(result, dict):
                        unique_results.append(dict(result))
                return unique_results[:max_results]
            except Exception as fallback_e:
                print(f"Fallback web search error: {fallback_e}")
                return []
    
    def get_scheduler_status(self) -> Dict[str, Any]:
        """Get status of the policy scheduler"""
        return self.policy_scheduler.get_status()
    
    def force_run_scheduled_task(self, task_id: str) -> bool:
        """Force run a scheduled task immediately"""
        return self.policy_scheduler.force_run_task(task_id)
    
    def get_pending_notifications(self, user_id: Optional[int] = None) -> List[Dict]:
        """Get pending notifications for user or all users"""
        notifications = self.notification_engine.get_pending_notifications(user_id)
        return [{
            'trigger_id': n.trigger_id,
            'user_id': n.user_id,
            'type': n.notification_type.value,
            'priority': n.priority.value,
            'title': n.title,
            'message': n.message,
            'channels': [ch.value for ch in n.channels],
            'created_at': n.created_at
        } for n in notifications]
    
    def get_commodity_prices(self, commodity: str) -> Dict:
        """Get commodity price information"""
        try:
            # This would integrate with actual commodity price APIs
            # For now, return mock data structure
            return {
                "commodity": commodity,
                "current_price": 2500,  # Mock price
                "price_change_percent": 5.2,
                "currency": "INR",
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        except Exception as e:
            print(f"Price fetch error: {e}")
            return {"error": f"Could not fetch price for {commodity}"}
    
    def get_agricultural_advice(self, query: str, context: str = "", target_language: str = "") -> str:
        """Get general agricultural advice using Groq with weather context integration"""
        try:
            system_prompt = """You are an expert agricultural advisor specializing in Indian farming practices. 
            Provide practical, actionable advice that considers:
            - Indian climate and soil conditions
            - Traditional and modern farming techniques
            - Cost-effective solutions for small and marginal farmers
            - Government schemes and subsidies
            - Sustainable farming practices
            - Local market conditions
            - Current weather conditions and their impact on farming activities
            
            IMPORTANT: When weather context is provided, always incorporate current weather conditions into your advice.
            Consider how temperature, humidity, rainfall, wind, and UV index affect:
            - Crop selection and planting timing
            - Irrigation needs and water management
            - Pest and disease risk
            - Harvesting decisions
            - Field operations and labor planning
            - Fertilizer and pesticide application timing
            
            Always provide specific, implementable recommendations tailored to current conditions."""
            if target_language:
                system_prompt += f"\nRespond in {target_language}."
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Context: {context}\n\nQuery: {query}"}
            ]
            
            response = self.groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=messages,
                max_tokens=1500,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"Error getting agricultural advice: {str(e)}"
    
    def get_financial_advice(
        self,
        query: str,
        category: str = "",
        location: Optional[str] = None,
        language: str = "English",
        context: str = "",
    ) -> Dict[str, Any]:
        """Get agricultural financial advice. Returns structured result with sources."""
        try:
            # Ensure query is not empty
            if not query or not query.strip():
                return {
                    "advice": "Please provide a valid financial question to get advice.",
                    "sources": []
                }

            # Web context to enrich financial answers
            search_results: List[Dict[str, Any]] = []
            try:
                search_query = f"{category} {query} India government scheme agriculture"
                search_results = self.search_web(search_query, max_results=5)
            except Exception as e:
                print(f"Web search error in financial advice: {e}")
                search_results = []

            # Ensure search_results is a list and not None
            search_results = search_results or []

            system_prompt = (
                "You are an agricultural finance expert specializing in Indian farming economics.\n"
                "Provide practical financial advice considering:\n"
                "- Government schemes and subsidies\n"
                "- Market trends and crop prices\n"
                "- Investment planning and ROI calculations\n"
                "- Risk assessment and insurance\n"
                "- Seasonal cash flow management\n"
                "- Technology adoption costs and benefits\n"
            )

            # Build search context with defensive checks
            search_context_parts = []
            for r in search_results[:3]:
                if isinstance(r, dict):
                    title = str(r.get('title', '')).strip()
                    href = str(r.get('href', '')).strip()
                    body = str(r.get('body', '')).strip()
                    if title or href or body:
                        search_context_parts.append(
                            f"Title: {title}\nUrl: {href}\nSnippet: {body}"
                        )
            
            search_context = "\n\n".join(search_context_parts)

            user_context = (
                f"Category: {category}\n"
                f"Location: {location or 'Unknown'}\n"
                f"Language: {language}\n"
                f"Extra Context: {context}\n"
            )

            messages = [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": f"Context:\n{user_context}\n\nMarket Information:\n{search_context}\n\nQuery: {query}",
                },
            ]

            completion = self.groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=messages,
                max_tokens=1500,
                temperature=0.7,
            )

            # Ensure completion has valid choices
            if not completion.choices or not completion.choices[0].message:
                return {
                    "advice": "Unable to generate financial advice. Please try again.",
                    "sources": []
                }

            advice_text = completion.choices[0].message.content or "No advice generated."
            
            # Build sources with defensive checks
            sources = []
            for r in search_results[:5]:
                if isinstance(r, dict):
                    href = str(r.get("href", "")).strip()
                    title = str(r.get("title", "")).strip()
                    if href and href.startswith('http'):
                        sources.append({
                            "title": title or "Source",
                            "url": href
                        })

            return {"advice": advice_text, "sources": sources}

        except Exception as e:
            return {
                "advice": f"Error getting financial advice: {str(e)}", 
                "sources": []
            }
    
    def process_query(
        self,
        text: str = "",
        image: Any = None,
        location: Optional[str] = None,
        language: str = "English",
        user_profile: Optional[Dict[str, Any]] = None,
        query_type: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Process queries from the AI Chat Assistant with weather context integration."""
        try:
            user_profile = user_profile or {}
            context = context or {}

            # Fetch current weather context if location is provided
            weather_context = ""
            if location:
                try:
                    weather_data = self.weather_service.get_weather_data(location)
                    if weather_data and not weather_data.get('error'):
                        weather_context = self._format_weather_context(weather_data)
                        print(f"INFO: Weather context added for {location}: {weather_data.get('current', {}).get('condition', {}).get('text', 'N/A')}")
                except Exception as e:
                    print(f"WARNING: Could not fetch weather context: {e}")

            # Enhanced context with weather information
            enhanced_context = {
                "language": language,
                "location": location,
                "user_profile": user_profile,
                "weather_context": weather_context
            }

            # Determine query intent
            financial_keywords = ['loan', 'money', 'cost', 'price', 'profit', 'investment', 'subsidy', 'scheme', 'financial', 'budget', 'income', 'expense', 'roi', 'return']
            is_financial = any(keyword in text.lower() for keyword in financial_keywords) if text else False

            # Process the query based on intent
            if is_financial:
                # Get financial advice with weather context
                financial_advice = self.get_financial_advice(
                    text or "",
                    category="",
                    location=location,
                    language=language,
                    context=str(enhanced_context),
                )
                response = financial_advice.get("advice", "")
            else:
                # Get general agricultural advice with weather context
                response = self.get_agricultural_advice(
                    text or "",
                    context=str(enhanced_context),
                    target_language=language,
                )

            # Inform if image was provided (chat mode). Disease analysis is on dedicated page.
            if image:
                response += "\n\n📷 **Image Detected**: For detailed disease analysis, please use the Disease Detection page in the sidebar."
            
            return {"text": response}
            
        except Exception as e:
            return {"text": f"Error processing query: {str(e)}"}
    
    def _format_weather_context(self, weather_data: Dict[str, Any]) -> str:
        """Format weather data into context string for AI responses"""
        try:
            context_parts = []
            
            # Extract current weather data
            current = weather_data.get('current', {})
            location = weather_data.get('location', {})
            
            # Location info
            if location.get('name'):
                context_parts.append(f"Location: {location['name']}, {location.get('region', '')}")
            
            # Basic weather info
            if current.get('temp_c'):
                context_parts.append(f"Current temperature: {current['temp_c']}°C")
            
            if current.get('condition', {}).get('text'):
                context_parts.append(f"Weather condition: {current['condition']['text']}")
            
            if current.get('humidity'):
                context_parts.append(f"Humidity: {current['humidity']}%")
            
            # Agricultural relevant data
            if current.get('wind_kph'):
                context_parts.append(f"Wind speed: {current['wind_kph']} km/h")
            
            if current.get('uv'):
                context_parts.append(f"UV index: {current['uv']}")
            
            if current.get('feelslike_c'):
                context_parts.append(f"Feels like: {current['feelslike_c']}°C")
            
            # Agricultural insights from weather service
            agricultural_insights = weather_data.get('agricultural_insights', {})
            if agricultural_insights:
                if agricultural_insights.get('irrigation_advice'):
                    context_parts.append(f"Irrigation advice: {agricultural_insights['irrigation_advice']}")
                if agricultural_insights.get('field_work_conditions'):
                    context_parts.append(f"Field work conditions: {agricultural_insights['field_work_conditions']}")
                if agricultural_insights.get('pest_disease_risk'):
                    context_parts.append(f"Pest/disease risk: {agricultural_insights['pest_disease_risk']}")
            
            return "; ".join(context_parts) if context_parts else ""
            
        except Exception as e:
            print(f"WARNING: Error formatting weather context: {e}")
            return ""
    
    def get_comprehensive_agricultural_advice(self, query: str, context: ContextData, language: str) -> str:
        """Get comprehensive agricultural advice with full context"""
        try:
            # Format comprehensive context
            context_str = self.context_manager.format_context_for_ai(context)
            
            # Enhanced prompt with full context
            prompt = f"""
You are an expert agricultural advisor with access to comprehensive context about the user and current conditions.

USER QUERY: {query}

COMPREHENSIVE CONTEXT:
{context_str}

Provide detailed, personalized agricultural advice considering:
1. User's specific farming situation and crops
2. Current weather conditions and forecasts
3. Seasonal timing and activities
4. Recent web information and best practices
5. User's chat history and previous concerns
6. Market conditions and financial considerations

Respond in {language} language. Be specific, actionable, and consider the user's context.
"""
            
            response = self.groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=1000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"Error in comprehensive agricultural advice: {e}")
            return "I apologize, but I'm having trouble accessing comprehensive information right now. Please try again."
    
    def get_comprehensive_financial_advice(self, query: str, context: ContextData, language: str) -> str:
        """Get comprehensive financial advice with full context"""
        try:
            context_str = self.context_manager.format_context_for_ai(context)
            
            prompt = f"""
You are an expert agricultural financial advisor with access to comprehensive user context.

USER QUERY: {query}

COMPREHENSIVE CONTEXT:
{context_str}

Provide detailed financial advice considering:
1. User's farm size, crops, and financial situation
2. Current market prices and trends
3. Available government schemes and subsidies
4. Weather impact on financial planning
5. Seasonal cash flow considerations
6. Recent policy updates and opportunities

Include specific numbers, schemes, and actionable financial steps. Respond in {language} language.
"""
            
            response = self.groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=1000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"Error in comprehensive financial advice: {e}")
            return "I apologize, but I'm having trouble accessing financial information right now. Please try again."
    
    def get_comprehensive_disease_advice(self, query: str, context: ContextData, language: str, image=None) -> str:
        """Get comprehensive disease advice with full context"""
        try:
            context_str = self.context_manager.format_context_for_ai(context)
            
            prompt = f"""
You are an expert plant pathologist with access to comprehensive context.

USER QUERY: {query}

COMPREHENSIVE CONTEXT:
{context_str}

Provide detailed disease management advice considering:
1. User's specific crops and farming conditions
2. Current weather conditions affecting disease pressure
3. Seasonal disease patterns
4. Recent web information on disease outbreaks
5. Integrated pest management approaches
6. Weather-based disease risk assessment

{"Note: Image analysis available on Disease Detection page." if image else ""}

Respond in {language} language with specific treatment and prevention strategies.
"""
            
            response = self.groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=1000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"Error in comprehensive disease advice: {e}")
            return "I apologize, but I'm having trouble accessing disease information right now. Please try again."
    
    def get_comprehensive_weather_advice(self, query: str, context: ContextData, language: str) -> str:
        """Get comprehensive weather advice with full context"""
        try:
            context_str = self.context_manager.format_context_for_ai(context)
            
            prompt = f"""
You are an expert agricultural meteorologist with access to comprehensive context.

USER QUERY: {query}

COMPREHENSIVE CONTEXT:
{context_str}

Provide detailed weather-based agricultural advice considering:
1. Current weather conditions and forecasts
2. User's crops and their weather sensitivity
3. Seasonal weather patterns and timing
4. Weather-based farming operations planning
5. Risk management for weather extremes
6. Irrigation and field work scheduling

Respond in {language} language with specific, actionable weather-based recommendations.
"""
            
            response = self.groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=1000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"Error in comprehensive weather advice: {e}")
            return "I apologize, but I'm having trouble accessing weather information right now. Please try again."
    
    def get_comprehensive_policy_advice(self, query: str, context: ContextData, language: str) -> str:
        """Get comprehensive policy advice with full context"""
        try:
            context_str = self.context_manager.format_context_for_ai(context)
            
            prompt = f"""
You are an expert agricultural policy advisor with access to comprehensive context.

USER QUERY: {query}

COMPREHENSIVE CONTEXT:
{context_str}

Provide detailed policy and scheme advice considering:
1. User's eligibility for government schemes
2. Recent policy updates and new schemes
3. Application processes and requirements
4. Timing and deadlines for applications
5. Financial benefits and subsidies available
6. Documentation and compliance requirements

Respond in {language} language with specific scheme recommendations and application guidance.
"""
            
            response = self.groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=1000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"Error in comprehensive policy advice: {e}")
            return "I apologize, but I'm having trouble accessing policy information right now. Please try again."
    
    def evaluate_notification_triggers(self, user_id: int, query: str, context: ContextData):
        """Evaluate and queue notification triggers based on conversation context"""
        try:
            # Extract user profile from context
            user_profile = context.user_profile
            
            # Evaluate weather-based triggers
            if context.weather_context:
                weather_triggers = self.notification_engine.evaluate_weather_triggers(
                    context.weather_context, user_profile
                )
                for trigger in weather_triggers:
                    self.notification_engine.queue_trigger(trigger)
            
            # Evaluate market-based triggers
            if context.market_context:
                market_triggers = self.notification_engine.evaluate_market_triggers(
                    context.market_context, user_profile
                )
                for trigger in market_triggers:
                    self.notification_engine.queue_trigger(trigger)
            
            # Check for urgent keywords in query
            urgent_keywords = ['urgent', 'emergency', 'help', 'dying', 'critical', 'immediate']
            if any(keyword in query.lower() for keyword in urgent_keywords):
                # Could trigger immediate notification to agricultural experts
                print(f"🚨 Urgent query detected from user {user_id}: {query[:50]}...")
            
        except Exception as e:
            print(f"Error evaluating notification triggers: {e}")
    
    def get_government_schemes(self, user_profile: Dict[str, Any], query: str = "") -> Dict[str, Any]:
        """Get government schemes based on user profile and query"""
        try:
            if query:
                # Search schemes based on query
                schemes = self.policy_agent.search_schemes_by_query(query, user_profile)
                analysis = self.policy_agent.get_scheme_analysis(schemes, user_profile)
                
                return {
                    "schemes": schemes,
                    "analysis": analysis,
                    "search_type": "query",
                    "query": query,
                    "total_found": len(schemes)
                }
            else:
                # Get profile-based schemes
                schemes = self.policy_agent.get_profile_based_schemes(user_profile)
                analysis = self.policy_agent.get_scheme_analysis(schemes, user_profile)
                
                return {
                    "schemes": schemes,
                    "analysis": analysis,
                    "search_type": "profile",
                    "total_found": len(schemes)
                }
                
        except Exception as e:
            return {
                "schemes": [],
                "analysis": f"Error retrieving government schemes: {str(e)}",
                "search_type": "error",
                "total_found": 0
            }
    
    def get_scheme_updates_info(self) -> Dict[str, Any]:
        """Get information about scheme cache status and updates"""
        try:
            return self.policy_agent.get_scheme_updates()
        except Exception as e:
            return {
                "error": f"Error getting scheme updates: {str(e)}",
                "last_update": None,
                "total_schemes_cached": 0,
                "cache_valid": False
            }
    
    def cleanup_old_schemes(self, days_old: int = 90) -> int:
        """Clean up old schemes from storage"""
        return self.policy_agent.cleanup_old_schemes(days_old)
    
    # Notification System Methods
    def send_disease_notification(self, user_id: int, disease_info: Dict[str, Any], image_path: Optional[str] = None) -> Dict[str, bool]:
        """Send disease detection notification"""
        return self.notification_manager.send_disease_alert(user_id, disease_info, image_path)
    
    def send_disaster_notification(self, user_id: int, disaster_info: Dict[str, Any]) -> Dict[str, bool]:
        """Send disaster/calamity notification"""
        return self.notification_manager.send_disaster_alert(user_id, disaster_info)
    
    def send_scheme_notification(self, user_id: int, schemes: List[Dict[str, Any]]) -> Dict[str, bool]:
        """Send new government scheme notification"""
        return self.notification_manager.send_scheme_alert(user_id, schemes)
    
    def get_notification_preferences(self, user_id: int) -> Dict[str, Any]:
        """Get user notification preferences"""
        return self.notification_manager.get_user_notification_preferences(user_id)
    
    def save_notification_preferences(self, user_id: int, preferences: Dict[str, Any]) -> bool:
        """Save user notification preferences"""
        return self.notification_manager.save_user_notification_preferences(user_id, preferences)
    
    def get_notification_history(self, user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        """Get user notification history"""
        return self.notification_manager.get_notification_history(user_id, limit)
    
    def get_notification_statistics(self, user_id: int) -> Dict[str, Any]:
        """Get user notification statistics"""
        return self.notification_manager.get_notification_statistics(user_id)
    
    def test_notification_setup(self, user_id: int) -> Dict[str, Any]:
        """Test notification setup"""
        return self.notification_manager.test_notification_setup(user_id)
    
    def reload_notification_config(self) -> bool:
        """Reload notification configuration from environment variables"""
        try:
            self.notification_manager.reload_environment_variables()
            return True
        except Exception as e:
            logging.error(f"Error reloading notification config: {e}")
            return False
    
    # Disaster Monitoring Methods
    def check_weather_alerts(self, location: str, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Check for weather-related alerts"""
        return self.disaster_monitor.check_weather_alerts(location, user_id)
    
    def check_agricultural_calamities(self, location: str, crop_type: str = "") -> List[Dict[str, Any]]:
        """Check for agricultural calamity conditions"""
        return self.disaster_monitor.check_agricultural_calamities(location, crop_type)
    
    def get_active_disaster_alerts(self, location: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get active disaster alerts"""
        return self.disaster_monitor.get_active_alerts(location)
    
    def create_test_disaster_alert(self, alert_type: str = "cyclone") -> Dict[str, Any]:
        """Create a test disaster alert"""
        return self.disaster_monitor.create_mock_disaster_alert(alert_type)
    
    def monitor_and_notify_disasters(self, user_id: int, location: str, crop_type: str = "") -> Dict[str, Any]:
        """Monitor disasters and send notifications if needed"""
        try:
            # Check for weather alerts
            weather_alerts = self.check_weather_alerts(location, user_id)
            
            # Check for agricultural calamities
            calamity_alerts = self.check_agricultural_calamities(location, crop_type)
            
            # Combine all alerts
            all_alerts = weather_alerts + calamity_alerts
            
            notification_results = []
            
            # Send notifications for high-priority alerts
            for alert in all_alerts:
                if alert.get('severity') in ['high', 'critical']:
                    result = self.send_disaster_notification(user_id, alert)
                    notification_results.append({
                        'alert': alert['title'],
                        'notification_sent': result
                    })
            
            return {
                'alerts_found': len(all_alerts),
                'notifications_sent': len(notification_results),
                'alerts': all_alerts,
                'notification_results': notification_results
            }
            
        except Exception as e:
            logging.error(f"Error in disaster monitoring: {e}")
            return {
                'alerts_found': 0,
                'notifications_sent': 0,
                'error': str(e)
            }
    
    def get_weather_advice(self, weather_data: Dict[str, Any], language: str = "English") -> str:
        """Get agricultural advice based on current weather conditions"""
        try:
            if not weather_data or 'current' not in weather_data:
                return "Weather data not available for agricultural recommendations."
            
            current = weather_data['current']
            temp = current.get('temp_c', 0)
            humidity = current.get('humidity', 0)
            wind_speed = current.get('wind_kph', 0)
            condition = current.get('condition', {}).get('text', 'Unknown')
            uv_index = current.get('uv', 0)
            
            # Create weather-based agricultural advice prompt
            prompt = f"""
You are an expert agricultural advisor. Based on the current weather conditions, provide specific agricultural recommendations.

Current Weather:
- Temperature: {temp}°C
- Humidity: {humidity}%
- Wind Speed: {wind_speed} km/h
- Condition: {condition}
- UV Index: {uv_index}

Provide practical advice covering:
1. Irrigation recommendations
2. Crop protection measures
3. Pest and disease alerts
4. Field work suitability
5. Harvesting considerations

Keep recommendations concise and actionable. Respond in {language} language.
"""

            response = self.groq_client.chat.completions.create(
                model="llama3-8b-8192",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"Error generating weather advice: {e}")
            return f"Unable to generate weather-based agricultural advice at this time. Current conditions: {condition}, {temp}°C, {humidity}% humidity."
    
    def get_treatment_advice(self, disease_name: str, language: str = "English") -> str:
        """Get treatment recommendations for a detected plant disease"""
        try:
            # Create disease treatment advice prompt
            prompt = f"""
You are an expert plant pathologist and agricultural advisor. Provide comprehensive treatment recommendations for the following plant disease:

Disease: {disease_name}

Please provide detailed advice covering:

1. **Immediate Treatment Steps:**
   - Emergency actions to take right away
   - Isolation and containment measures

2. **Chemical Treatment Options:**
   - Recommended fungicides/bactericides/pesticides
   - Application methods and timing
   - Safety precautions

3. **Organic/Natural Treatment Methods:**
   - Bio-friendly alternatives
   - Home remedies and organic solutions
   - Beneficial microorganisms

4. **Prevention Strategies:**
   - Cultural practices to prevent recurrence
   - Environmental modifications
   - Crop rotation recommendations

5. **Monitoring and Follow-up:**
   - Signs of recovery to watch for
   - When to reapply treatments
   - Long-term plant care

Keep recommendations practical, safe, and suitable for small-scale farmers. Include specific product names where helpful. Respond in {language} language.
"""

            response = self.groq_client.chat.completions.create(
                model="llama3-8b-8192",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=800,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"Error generating treatment advice: {e}")
            return f"""
## Treatment for {disease_name}

**Immediate Actions:**
- Remove affected plant parts immediately
- Isolate infected plants from healthy ones
- Improve air circulation around plants

**General Treatment:**
- Apply appropriate fungicide or bactericide
- Ensure proper drainage and avoid overwatering
- Monitor plant regularly for signs of improvement

**Prevention:**
- Practice crop rotation
- Maintain proper plant spacing
- Use disease-resistant varieties when possible

*Note: Consult with local agricultural extension services for specific product recommendations in your area.*
"""