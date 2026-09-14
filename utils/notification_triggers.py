"""
Automatic Notification Triggers
Intelligent notification system based on user profile, weather, and policy updates
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import sqlite3
import os

class NotificationType(Enum):
    WEATHER_ALERT = "weather_alert"
    POLICY_UPDATE = "policy_update"
    MARKET_PRICE = "market_price"
    SEASONAL_ADVICE = "seasonal_advice"
    DISEASE_WARNING = "disease_warning"
    IRRIGATION_REMINDER = "irrigation_reminder"
    FERTILIZER_REMINDER = "fertilizer_reminder"
    HARVEST_REMINDER = "harvest_reminder"

class NotificationPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class NotificationChannel(Enum):
    WHATSAPP = "whatsapp"
    EMAIL = "email"
    SMS = "sms"
    IN_APP = "in_app"
    PUSH = "push"

@dataclass
class NotificationRule:
    """Rule for triggering notifications"""
    rule_id: str
    notification_type: NotificationType
    priority: NotificationPriority
    channels: List[NotificationChannel]
    conditions: Dict[str, Any]
    template: str
    enabled: bool = True
    cooldown_hours: int = 24  # Minimum hours between similar notifications
    user_specific: bool = True
    created_at: str = None
    last_triggered: str = None

@dataclass
class NotificationTrigger:
    """Notification trigger event"""
    trigger_id: str
    user_id: int
    notification_type: NotificationType
    priority: NotificationPriority
    title: str
    message: str
    channels: List[NotificationChannel]
    data: Dict[str, Any]
    created_at: str
    scheduled_for: str = None
    sent: bool = False
    sent_at: str = None

class NotificationTriggerEngine:
    """Intelligent notification trigger engine"""
    
    def __init__(self, db_path: str = "data/agricultural_advisor.db"):
        self.db_path = db_path
        self.rules: Dict[str, NotificationRule] = {}
        self.pending_notifications: List[NotificationTrigger] = []
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Initialize database
        self.init_database()
        
        # Load notification rules
        self.load_default_rules()
        self.load_custom_rules()
    
    def init_database(self):
        """Initialize notification database tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Notification rules table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS notification_rules (
                        rule_id TEXT PRIMARY KEY,
                        notification_type TEXT NOT NULL,
                        priority TEXT NOT NULL,
                        channels TEXT NOT NULL,
                        conditions TEXT NOT NULL,
                        template TEXT NOT NULL,
                        enabled INTEGER DEFAULT 1,
                        cooldown_hours INTEGER DEFAULT 24,
                        user_specific INTEGER DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_triggered TIMESTAMP
                    )
                ''')
                
                # Notification triggers table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS notification_triggers (
                        trigger_id TEXT PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        notification_type TEXT NOT NULL,
                        priority TEXT NOT NULL,
                        title TEXT NOT NULL,
                        message TEXT NOT NULL,
                        channels TEXT NOT NULL,
                        data TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        scheduled_for TIMESTAMP,
                        sent INTEGER DEFAULT 0,
                        sent_at TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )
                ''')
                
                # Notification history table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS notification_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        notification_type TEXT NOT NULL,
                        title TEXT NOT NULL,
                        message TEXT NOT NULL,
                        channel TEXT NOT NULL,
                        sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        success INTEGER DEFAULT 1,
                        error_message TEXT,
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )
                ''')
                
                conn.commit()
                self.logger.info("Notification database initialized")
                
        except Exception as e:
            self.logger.error(f"Error initializing notification database: {e}")
    
    def load_default_rules(self):
        """Load default notification rules"""
        default_rules = [
            # Weather-based notifications
            NotificationRule(
                rule_id="weather_rain_alert",
                notification_type=NotificationType.WEATHER_ALERT,
                priority=NotificationPriority.HIGH,
                channels=[NotificationChannel.WHATSAPP, NotificationChannel.IN_APP],
                conditions={
                    "weather_condition": "rain",
                    "probability": ">= 70",
                    "advance_hours": 12
                },
                template="🌧️ Rain Alert: {probability}% chance of rain in next {hours} hours. Consider protecting your crops!"
            ),
            
            NotificationRule(
                rule_id="weather_extreme_temp",
                notification_type=NotificationType.WEATHER_ALERT,
                priority=NotificationPriority.CRITICAL,
                channels=[NotificationChannel.WHATSAPP, NotificationChannel.SMS, NotificationChannel.IN_APP],
                conditions={
                    "temperature": {"min": "< 5", "max": "> 45"},
                    "advance_hours": 24
                },
                template="🌡️ Extreme Temperature Alert: {temperature}°C expected. Take immediate action to protect crops!"
            ),
            
            # Policy-based notifications
            NotificationRule(
                rule_id="new_government_scheme",
                notification_type=NotificationType.POLICY_UPDATE,
                priority=NotificationPriority.MEDIUM,
                channels=[NotificationChannel.EMAIL, NotificationChannel.IN_APP],
                conditions={
                    "scheme_type": "agricultural",
                    "eligibility_match": "> 80"
                },
                template="🏛️ New Government Scheme: {scheme_name} - You may be eligible! Check details in the app."
            ),
            
            # Seasonal reminders
            NotificationRule(
                rule_id="planting_season_reminder",
                notification_type=NotificationType.SEASONAL_ADVICE,
                priority=NotificationPriority.MEDIUM,
                channels=[NotificationChannel.WHATSAPP, NotificationChannel.IN_APP],
                conditions={
                    "season": "planting",
                    "crop_type": "user_crops",
                    "location": "user_location"
                },
                template="🌱 Planting Season Alert: Optimal time to plant {crop_name} in your area. Weather conditions are favorable!"
            ),
            
            # Market price alerts
            NotificationRule(
                rule_id="price_increase_alert",
                notification_type=NotificationType.MARKET_PRICE,
                priority=NotificationPriority.HIGH,
                channels=[NotificationChannel.WHATSAPP, NotificationChannel.IN_APP],
                conditions={
                    "price_change": "> 15",
                    "crop_type": "user_crops"
                },
                template="📈 Price Alert: {crop_name} prices increased by {percentage}%! Current rate: ₹{price}/kg"
            ),
            
            # Disease warnings
            NotificationRule(
                rule_id="disease_outbreak_warning",
                notification_type=NotificationType.DISEASE_WARNING,
                priority=NotificationPriority.CRITICAL,
                channels=[NotificationChannel.WHATSAPP, NotificationChannel.SMS, NotificationChannel.IN_APP],
                conditions={
                    "disease_risk": "> 70",
                    "crop_type": "user_crops",
                    "location_radius": "50km"
                },
                template="⚠️ Disease Alert: High risk of {disease_name} in your area. Take preventive measures immediately!"
            ),
            
            # Irrigation reminders
            NotificationRule(
                rule_id="irrigation_reminder",
                notification_type=NotificationType.IRRIGATION_REMINDER,
                priority=NotificationPriority.MEDIUM,
                channels=[NotificationChannel.WHATSAPP, NotificationChannel.IN_APP],
                conditions={
                    "soil_moisture": "< 30",
                    "days_since_rain": "> 3",
                    "crop_stage": "critical"
                },
                template="💧 Irrigation Reminder: Your {crop_name} needs watering. Soil moisture is low and no rain expected."
            )
        ]
        
        for rule in default_rules:
            self.rules[rule.rule_id] = rule
    
    def load_custom_rules(self):
        """Load custom notification rules from database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM notification_rules')
                
                for row in cursor.fetchall():
                    rule = NotificationRule(
                        rule_id=row[0],
                        notification_type=NotificationType(row[1]),
                        priority=NotificationPriority(row[2]),
                        channels=[NotificationChannel(ch) for ch in json.loads(row[3])],
                        conditions=json.loads(row[4]),
                        template=row[5],
                        enabled=bool(row[6]),
                        cooldown_hours=row[7],
                        user_specific=bool(row[8]),
                        created_at=row[9],
                        last_triggered=row[10]
                    )
                    self.rules[rule.rule_id] = rule
                    
        except Exception as e:
            self.logger.error(f"Error loading custom rules: {e}")
    
    def evaluate_weather_triggers(self, weather_data: Dict, user_profile: Dict) -> List[NotificationTrigger]:
        """Evaluate weather-based notification triggers"""
        triggers = []
        
        try:
            # Rain alert
            if weather_data.get('forecast'):
                for forecast in weather_data['forecast'][:2]:  # Next 2 days
                    rain_prob = forecast.get('rain_probability', 0)
                    if rain_prob >= 70:
                        trigger = self.create_trigger(
                            user_id=user_profile['user_id'],
                            rule_id="weather_rain_alert",
                            data={
                                'probability': rain_prob,
                                'hours': 12,
                                'weather_data': forecast
                            }
                        )
                        if trigger:
                            triggers.append(trigger)
            
            # Temperature extremes
            current_temp = weather_data.get('current', {}).get('temperature')
            if current_temp:
                if current_temp < 5 or current_temp > 45:
                    trigger = self.create_trigger(
                        user_id=user_profile['user_id'],
                        rule_id="weather_extreme_temp",
                        data={
                            'temperature': current_temp,
                            'weather_data': weather_data['current']
                        }
                    )
                    if trigger:
                        triggers.append(trigger)
                        
        except Exception as e:
            self.logger.error(f"Error evaluating weather triggers: {e}")
        
        return triggers
    
    def evaluate_policy_triggers(self, new_schemes: List[Dict], user_profile: Dict) -> List[NotificationTrigger]:
        """Evaluate policy-based notification triggers"""
        triggers = []
        
        try:
            for scheme in new_schemes:
                # Check eligibility match
                eligibility_score = self.calculate_scheme_eligibility(scheme, user_profile)
                
                if eligibility_score > 80:
                    trigger = self.create_trigger(
                        user_id=user_profile['user_id'],
                        rule_id="new_government_scheme",
                        data={
                            'scheme_name': scheme.get('title', 'New Scheme'),
                            'eligibility_score': eligibility_score,
                            'scheme_data': scheme
                        }
                    )
                    if trigger:
                        triggers.append(trigger)
                        
        except Exception as e:
            self.logger.error(f"Error evaluating policy triggers: {e}")
        
        return triggers
    
    def evaluate_market_triggers(self, market_data: Dict, user_profile: Dict) -> List[NotificationTrigger]:
        """Evaluate market price notification triggers"""
        triggers = []
        
        try:
            user_crops = user_profile.get('crops', [])
            
            for crop_data in market_data.get('prices', []):
                crop_name = crop_data.get('crop')
                if crop_name in user_crops:
                    price_change = crop_data.get('price_change_percent', 0)
                    
                    if abs(price_change) > 15:
                        trigger = self.create_trigger(
                            user_id=user_profile['user_id'],
                            rule_id="price_increase_alert",
                            data={
                                'crop_name': crop_name,
                                'percentage': price_change,
                                'price': crop_data.get('current_price'),
                                'market_data': crop_data
                            }
                        )
                        if trigger:
                            triggers.append(trigger)
                            
        except Exception as e:
            self.logger.error(f"Error evaluating market triggers: {e}")
        
        return triggers
    
    def create_trigger(self, user_id: int, rule_id: str, data: Dict) -> Optional[NotificationTrigger]:
        """Create a notification trigger based on rule"""
        try:
            rule = self.rules.get(rule_id)
            if not rule or not rule.enabled:
                return None
            
            # Check cooldown period
            if self.is_in_cooldown(rule_id, user_id):
                return None
            
            # Generate trigger
            trigger_id = f"{rule_id}_{user_id}_{int(datetime.now().timestamp())}"
            
            # Format message using template
            message = rule.template.format(**data)
            title = self.generate_title(rule.notification_type, data)
            
            trigger = NotificationTrigger(
                trigger_id=trigger_id,
                user_id=user_id,
                notification_type=rule.notification_type,
                priority=rule.priority,
                title=title,
                message=message,
                channels=rule.channels,
                data=data,
                created_at=datetime.now().isoformat()
            )
            
            return trigger
            
        except Exception as e:
            self.logger.error(f"Error creating trigger: {e}")
            return None
    
    def is_in_cooldown(self, rule_id: str, user_id: int) -> bool:
        """Check if notification is in cooldown period"""
        try:
            rule = self.rules.get(rule_id)
            if not rule:
                return False
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT sent_at FROM notification_history 
                    WHERE user_id = ? AND notification_type = ?
                    ORDER BY sent_at DESC LIMIT 1
                ''', (user_id, rule.notification_type.value))
                
                result = cursor.fetchone()
                if result:
                    last_sent = datetime.fromisoformat(result[0])
                    cooldown_end = last_sent + timedelta(hours=rule.cooldown_hours)
                    return datetime.now() < cooldown_end
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking cooldown: {e}")
            return False
    
    def generate_title(self, notification_type: NotificationType, data: Dict) -> str:
        """Generate notification title based on type"""
        titles = {
            NotificationType.WEATHER_ALERT: "🌤️ Weather Alert",
            NotificationType.POLICY_UPDATE: "🏛️ Policy Update",
            NotificationType.MARKET_PRICE: "📈 Market Alert",
            NotificationType.SEASONAL_ADVICE: "🌱 Seasonal Advice",
            NotificationType.DISEASE_WARNING: "⚠️ Disease Warning",
            NotificationType.IRRIGATION_REMINDER: "💧 Irrigation Reminder",
            NotificationType.FERTILIZER_REMINDER: "🌿 Fertilizer Reminder",
            NotificationType.HARVEST_REMINDER: "🌾 Harvest Reminder"
        }
        
        return titles.get(notification_type, "📢 Agricultural Alert")
    
    def calculate_scheme_eligibility(self, scheme: Dict, user_profile: Dict) -> float:
        """Calculate eligibility score for a government scheme"""
        score = 0.0
        
        try:
            # Location match
            user_location = user_profile.get('location', '').lower()
            scheme_location = scheme.get('location', '').lower()
            if user_location in scheme_location or scheme_location in user_location:
                score += 30
            
            # Farm size match
            user_farm_size = user_profile.get('farm_size', 0)
            scheme_farm_size = scheme.get('farm_size_requirement', {})
            if scheme_farm_size:
                min_size = scheme_farm_size.get('min', 0)
                max_size = scheme_farm_size.get('max', float('inf'))
                if min_size <= user_farm_size <= max_size:
                    score += 25
            
            # Crop type match
            user_crops = set(user_profile.get('crops', []))
            scheme_crops = set(scheme.get('applicable_crops', []))
            if user_crops.intersection(scheme_crops):
                score += 25
            
            # Experience match
            user_experience = user_profile.get('experience_years', 0)
            scheme_experience = scheme.get('experience_requirement', 0)
            if user_experience >= scheme_experience:
                score += 20
            
        except Exception as e:
            self.logger.error(f"Error calculating eligibility: {e}")
        
        return min(score, 100.0)
    
    def queue_trigger(self, trigger: NotificationTrigger):
        """Queue a notification trigger for sending"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO notification_triggers 
                    (trigger_id, user_id, notification_type, priority, title, message, 
                     channels, data, created_at, scheduled_for)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    trigger.trigger_id,
                    trigger.user_id,
                    trigger.notification_type.value,
                    trigger.priority.value,
                    trigger.title,
                    trigger.message,
                    json.dumps([ch.value for ch in trigger.channels]),
                    json.dumps(trigger.data),
                    trigger.created_at,
                    trigger.scheduled_for
                ))
                conn.commit()
                
            self.pending_notifications.append(trigger)
            self.logger.info(f"Queued notification trigger: {trigger.trigger_id}")
            
        except Exception as e:
            self.logger.error(f"Error queuing trigger: {e}")
    
    def get_pending_notifications(self, user_id: Optional[int] = None) -> List[NotificationTrigger]:
        """Get pending notifications for a user or all users"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if user_id:
                    cursor.execute('''
                        SELECT * FROM notification_triggers 
                        WHERE user_id = ? AND sent = 0
                        ORDER BY priority DESC, created_at ASC
                    ''', (user_id,))
                else:
                    cursor.execute('''
                        SELECT * FROM notification_triggers 
                        WHERE sent = 0
                        ORDER BY priority DESC, created_at ASC
                    ''')
                
                notifications = []
                for row in cursor.fetchall():
                    trigger = NotificationTrigger(
                        trigger_id=row[0],
                        user_id=row[1],
                        notification_type=NotificationType(row[2]),
                        priority=NotificationPriority(row[3]),
                        title=row[4],
                        message=row[5],
                        channels=[NotificationChannel(ch) for ch in json.loads(row[6])],
                        data=json.loads(row[7]),
                        created_at=row[8],
                        scheduled_for=row[9],
                        sent=bool(row[10]),
                        sent_at=row[11]
                    )
                    notifications.append(trigger)
                
                return notifications
                
        except Exception as e:
            self.logger.error(f"Error getting pending notifications: {e}")
            return []
    
    def mark_notification_sent(self, trigger_id: str, success: bool = True, error_message: str = None):
        """Mark a notification as sent"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE notification_triggers 
                    SET sent = 1, sent_at = CURRENT_TIMESTAMP
                    WHERE trigger_id = ?
                ''', (trigger_id,))
                conn.commit()
                
            self.logger.info(f"Marked notification as sent: {trigger_id}")
            
        except Exception as e:
            self.logger.error(f"Error marking notification sent: {e}")

# Global notification engine instance
notification_engine = NotificationTriggerEngine()
