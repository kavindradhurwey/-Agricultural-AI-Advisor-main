"""
Notification Manager for Agricultural AI Advisor
Handles WhatsApp and Email notifications for disease detection, disasters, and scheme alerts
"""

import smtplib
import logging
import requests
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
import sqlite3

# Configure logging
logging.basicConfig(level=logging.INFO)

class NotificationManager:
    """Manages WhatsApp and Email notifications for agricultural alerts"""
    
    def __init__(self, db_path: str = "data/agricultural_app.db"):
        self.db_path = db_path
        self.init_notification_tables()
        
        # Email configuration (Gmail SMTP)
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        
        # WhatsApp API configuration (using Twilio or similar service)
        self.whatsapp_api_url = "https://api.twilio.com/2010-04-01/Accounts"
        
        # Load configuration from environment variables
        self.reload_environment_variables()
    
    def reload_environment_variables(self):
        """Reload environment variables (useful after .env file changes)"""
        from dotenv import load_dotenv
        load_dotenv(override=True)  # Force reload of .env file
        
        self.email_user = os.getenv('EMAIL_USER')
        self.email_password = os.getenv('EMAIL_APP_PASSWORD')  # App-specific password
        self.twilio_account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.twilio_auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        self.twilio_whatsapp_number = os.getenv('TWILIO_WHATSAPP_NUMBER', 'whatsapp:+14155238886')
    
    def init_notification_tables(self):
        """Initialize notification-related database tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # User notification preferences
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_notification_preferences (
                    user_id INTEGER PRIMARY KEY,
                    email_notifications BOOLEAN DEFAULT 1,
                    whatsapp_notifications BOOLEAN DEFAULT 0,
                    email_address TEXT,
                    whatsapp_number TEXT,
                    disease_alerts BOOLEAN DEFAULT 1,
                    disaster_alerts BOOLEAN DEFAULT 1,
                    scheme_alerts BOOLEAN DEFAULT 1,
                    notification_frequency TEXT DEFAULT 'immediate',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # Notification history
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS notification_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    notification_type TEXT NOT NULL,
                    alert_category TEXT NOT NULL,
                    title TEXT NOT NULL,
                    message TEXT NOT NULL,
                    delivery_method TEXT NOT NULL,
                    delivery_status TEXT DEFAULT 'pending',
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    error_message TEXT,
                    metadata TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # Alert triggers and conditions
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS alert_triggers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    trigger_type TEXT NOT NULL,
                    conditions TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            conn.commit()
    
    def save_user_notification_preferences(self, user_id: int, preferences: Dict[str, Any]) -> bool:
        """Save user notification preferences"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO user_notification_preferences 
                    (user_id, email_notifications, whatsapp_notifications, email_address, 
                     whatsapp_number, disease_alerts, disaster_alerts, scheme_alerts, 
                     notification_frequency, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    user_id,
                    preferences.get('email_notifications', True),
                    preferences.get('whatsapp_notifications', False),
                    preferences.get('email_address', ''),
                    preferences.get('whatsapp_number', ''),
                    preferences.get('disease_alerts', True),
                    preferences.get('disaster_alerts', True),
                    preferences.get('scheme_alerts', True),
                    preferences.get('notification_frequency', 'immediate'),
                    datetime.now().isoformat()
                ))
                
                conn.commit()
                return True
                
        except Exception as e:
            logging.error(f"Error saving notification preferences: {e}")
            return False
    
    def get_user_notification_preferences(self, user_id: int) -> Dict[str, Any]:
        """Get user notification preferences"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM user_notification_preferences WHERE user_id = ?
                ''', (user_id,))
                
                row = cursor.fetchone()
                if row:
                    columns = [desc[0] for desc in cursor.description]
                    return dict(zip(columns, row))
                else:
                    # Return default preferences
                    return {
                        'user_id': user_id,
                        'email_notifications': True,
                        'whatsapp_notifications': False,
                        'email_address': '',
                        'whatsapp_number': '',
                        'disease_alerts': True,
                        'disaster_alerts': True,
                        'scheme_alerts': True,
                        'notification_frequency': 'immediate'
                    }
                    
        except Exception as e:
            logging.error(f"Error getting notification preferences: {e}")
            return {}
    
    def send_disease_alert(self, user_id: int, disease_info: Dict[str, Any], image_path: Optional[str] = None) -> Dict[str, bool]:
        """Send disease detection alert via email and WhatsApp"""
        preferences = self.get_user_notification_preferences(user_id)
        
        if not preferences.get('disease_alerts', True):
            return {'email': False, 'whatsapp': False, 'message': 'Disease alerts disabled'}
        
        # Prepare alert content
        disease_name = disease_info.get('disease', 'Unknown Disease')
        confidence = disease_info.get('confidence', 0)
        recommendations = disease_info.get('recommendations', [])
        
        title = f"🚨 Plant Disease Detected: {disease_name}"
        
        message = f"""
🌱 AGRICULTURAL DISEASE ALERT 🌱

Disease Detected: {disease_name}
Confidence Level: {confidence:.1f}%
Detection Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🔍 IMMEDIATE ACTIONS REQUIRED:
"""
        
        for i, rec in enumerate(recommendations[:3], 1):
            message += f"{i}. {rec}\n"
        
        message += f"""
📞 For expert consultation, contact your local agricultural extension officer.
💡 Visit the app for detailed treatment guidelines and preventive measures.

Stay vigilant and act quickly to protect your crops!
"""
        
        results = {}
        
        # Send email notification
        if preferences.get('email_notifications') and preferences.get('email_address'):
            results['email'] = self._send_email_notification(
                preferences['email_address'], 
                title, 
                message, 
                image_path
            )
        else:
            results['email'] = False
        
        # Send WhatsApp notification
        if preferences.get('whatsapp_notifications') and preferences.get('whatsapp_number'):
            results['whatsapp'] = self._send_whatsapp_notification(
                preferences['whatsapp_number'], 
                title, 
                message
            )
        else:
            results['whatsapp'] = False
        
        # Log notification
        self._log_notification(user_id, 'disease_alert', 'disease_detection', title, message, results)
        
        return results
    
    def send_disaster_alert(self, user_id: int, disaster_info: Dict[str, Any]) -> Dict[str, bool]:
        """Send disaster/calamity alert via email and WhatsApp"""
        preferences = self.get_user_notification_preferences(user_id)
        
        if not preferences.get('disaster_alerts', True):
            return {'email': False, 'whatsapp': False, 'message': 'Disaster alerts disabled'}
        
        # Prepare alert content
        disaster_type = disaster_info.get('type', 'Weather Alert')
        severity = disaster_info.get('severity', 'Medium')
        location = disaster_info.get('location', 'Your Area')
        description = disaster_info.get('description', '')
        precautions = disaster_info.get('precautions', [])
        
        title = f"⚠️ {disaster_type} Alert - {severity} Severity"
        
        message = f"""
🌪️ AGRICULTURAL DISASTER ALERT 🌪️

Alert Type: {disaster_type}
Severity Level: {severity}
Affected Area: {location}
Alert Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📋 SITUATION:
{description}

🛡️ IMMEDIATE PRECAUTIONS:
"""
        
        for i, precaution in enumerate(precautions[:4], 1):
            message += f"{i}. {precaution}\n"
        
        message += f"""
📞 Emergency Helpline: 1962 (Kisan Call Centre)
🏥 For medical emergencies: 108

Stay safe and protect your crops and livestock!
"""
        
        results = {}
        
        # Send email notification
        if preferences.get('email_notifications') and preferences.get('email_address'):
            results['email'] = self._send_email_notification(
                preferences['email_address'], 
                title, 
                message
            )
        else:
            results['email'] = False
        
        # Send WhatsApp notification
        if preferences.get('whatsapp_notifications') and preferences.get('whatsapp_number'):
            results['whatsapp'] = self._send_whatsapp_notification(
                preferences['whatsapp_number'], 
                title, 
                message
            )
        else:
            results['whatsapp'] = False
        
        # Log notification
        self._log_notification(user_id, 'disaster_alert', 'disaster_calamity', title, message, results)
        
        return results
    
    def send_scheme_alert(self, user_id: int, schemes: List[Dict[str, Any]]) -> Dict[str, bool]:
        """Send new government scheme alert via email and WhatsApp"""
        preferences = self.get_user_notification_preferences(user_id)
        
        if not preferences.get('scheme_alerts', True):
            return {'email': False, 'whatsapp': False, 'message': 'Scheme alerts disabled'}
        
        if not schemes:
            return {'email': False, 'whatsapp': False, 'message': 'No schemes to notify'}
        
        # Prepare alert content
        scheme_count = len(schemes)
        title = f"🏛️ {scheme_count} New Government Scheme{'s' if scheme_count > 1 else ''} Available!"
        
        message = f"""
🏛️ NEW GOVERNMENT SCHEMES ALERT 🏛️

{scheme_count} new scheme{'s' if scheme_count > 1 else ''} matching your profile:

"""
        
        for i, scheme in enumerate(schemes[:3], 1):
            scheme_title = scheme.get('title', 'Untitled Scheme')[:50]
            message += f"{i}. {scheme_title}\n"
            if scheme.get('description'):
                message += f"   {scheme['description'][:80]}...\n"
            message += "\n"
        
        if len(schemes) > 3:
            message += f"...and {len(schemes) - 3} more schemes available!\n\n"
        
        message += f"""
💰 BENEFITS AVAILABLE:
- Financial assistance and subsidies
- Technical support and training
- Equipment and infrastructure support
- Insurance and risk coverage

🔗 Visit the app's Government Schemes section for complete details and application procedures.

Don't miss out on these opportunities!
"""
        
        results = {}
        
        # Send email notification
        if preferences.get('email_notifications') and preferences.get('email_address'):
            results['email'] = self._send_email_notification(
                preferences['email_address'], 
                title, 
                message
            )
        else:
            results['email'] = False
        
        # Send WhatsApp notification
        if preferences.get('whatsapp_notifications') and preferences.get('whatsapp_number'):
            results['whatsapp'] = self._send_whatsapp_notification(
                preferences['whatsapp_number'], 
                title, 
                message
            )
        else:
            results['whatsapp'] = False
        
        # Log notification
        self._log_notification(user_id, 'scheme_alert', 'government_schemes', title, message, results)
        
        return results
    
    def _send_email_notification(self, email_address: str, title: str, message: str, image_path: Optional[str] = None) -> bool:
        """Send email notification"""
        try:
            if not self.email_user or not self.email_password:
                logging.warning("Email credentials not configured")
                return False
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.email_user
            msg['To'] = email_address
            msg['Subject'] = title
            
            # Add text content
            msg.attach(MIMEText(message, 'plain'))
            
            # Add image if provided
            if image_path and os.path.exists(image_path):
                with open(image_path, 'rb') as f:
                    img_data = f.read()
                    image = MIMEImage(img_data)
                    image.add_header('Content-Disposition', 'attachment', filename=os.path.basename(image_path))
                    msg.attach(image)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email_user, self.email_password)
                server.send_message(msg)
            
            logging.info(f"Email sent successfully to {email_address}")
            return True
            
        except Exception as e:
            logging.error(f"Error sending email: {e}")
            return False
    
    def _send_whatsapp_notification(self, phone_number: str, title: str, message: str) -> bool:
        """Send WhatsApp notification via Twilio API"""
        try:
            if not self.twilio_account_sid or not self.twilio_auth_token:
                logging.warning("Twilio credentials not configured")
                return False
            
            # Format phone number for WhatsApp (E164 format required)
            original_number = phone_number
            
            # Clean the phone number first (remove spaces, dashes, etc.)
            phone_number = phone_number.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
            
            # Ensure proper E164 format
            if not phone_number.startswith('whatsapp:'):
                if not phone_number.startswith('+'):
                    # If no country code, assume India (+91)
                    if phone_number.startswith('91') and len(phone_number) == 12:
                        phone_number = '+' + phone_number
                    elif len(phone_number) == 10:
                        phone_number = '+91' + phone_number
                    else:
                        phone_number = '+91' + phone_number
                
                # Validate E164 format: should be +[country code][number]
                if not phone_number.startswith('+'):
                    phone_number = '+' + phone_number
                
                # Add whatsapp: prefix
                phone_number = 'whatsapp:' + phone_number
            
            logging.info(f"Sending WhatsApp from {self.twilio_whatsapp_number} to {phone_number}")
            
            # Prepare API request
            url = f"{self.whatsapp_api_url}/{self.twilio_account_sid}/Messages.json"
            
            data = {
                'From': self.twilio_whatsapp_number,
                'To': phone_number,
                'Body': f"{title}\n\n{message}"
            }
            
            # Send WhatsApp message
            response = requests.post(
                url,
                data=data,
                auth=(self.twilio_account_sid, self.twilio_auth_token)
            )
            
            logging.info(f"Twilio API Response: {response.status_code}")
            logging.info(f"Response body: {response.text}")
            
            if response.status_code == 201:
                logging.info(f"WhatsApp message sent successfully to {phone_number}")
                return True
            else:
                logging.error(f"WhatsApp API error: {response.status_code} - {response.text}")
                # Try to parse error details
                try:
                    error_data = response.json()
                    error_message = error_data.get('message', 'Unknown error')
                    error_code = error_data.get('code', 'Unknown code')
                    logging.error(f"Twilio Error Code: {error_code}, Message: {error_message}")
                except:
                    pass
                return False
                
        except Exception as e:
            logging.error(f"Error sending WhatsApp message: {e}")
            return False
    
    def _log_notification(self, user_id: int, notification_type: str, alert_category: str, 
                         title: str, message: str, results: Dict[str, bool]):
        """Log notification to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Log each delivery method separately
                for method, success in results.items():
                    if method in ['email', 'whatsapp']:
                        cursor.execute('''
                            INSERT INTO notification_history 
                            (user_id, notification_type, alert_category, title, message, 
                             delivery_method, delivery_status, sent_at, metadata)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            user_id,
                            notification_type,
                            alert_category,
                            title,
                            message[:500],  # Truncate long messages
                            method,
                            'sent' if success else 'failed',
                            datetime.now().isoformat(),
                            json.dumps({'success': success})
                        ))
                
                conn.commit()
                
        except Exception as e:
            logging.error(f"Error logging notification: {e}")
    
    def get_notification_history(self, user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        """Get user's notification history"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM notification_history 
                    WHERE user_id = ? 
                    ORDER BY sent_at DESC 
                    LIMIT ?
                ''', (user_id, limit))
                
                rows = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                
                return [dict(zip(columns, row)) for row in rows]
                
        except Exception as e:
            logging.error(f"Error getting notification history: {e}")
            return []
    
    def get_notification_statistics(self, user_id: int) -> Dict[str, Any]:
        """Get notification statistics for user"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Total notifications
                cursor.execute('''
                    SELECT COUNT(*) FROM notification_history WHERE user_id = ?
                ''', (user_id,))
                total_notifications = cursor.fetchone()[0]
                
                # Successful notifications
                cursor.execute('''
                    SELECT COUNT(*) FROM notification_history 
                    WHERE user_id = ? AND delivery_status = 'sent'
                ''', (user_id,))
                successful_notifications = cursor.fetchone()[0]
                
                # Notifications by type
                cursor.execute('''
                    SELECT alert_category, COUNT(*) 
                    FROM notification_history 
                    WHERE user_id = ? 
                    GROUP BY alert_category
                ''', (user_id,))
                notifications_by_type = dict(cursor.fetchall())
                
                # Recent activity (last 30 days)
                thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()
                cursor.execute('''
                    SELECT COUNT(*) FROM notification_history 
                    WHERE user_id = ? AND sent_at > ?
                ''', (user_id, thirty_days_ago))
                recent_notifications = cursor.fetchone()[0]
                
                return {
                    'total_notifications': total_notifications,
                    'successful_notifications': successful_notifications,
                    'success_rate': (successful_notifications / total_notifications * 100) if total_notifications > 0 else 0,
                    'notifications_by_type': notifications_by_type,
                    'recent_notifications': recent_notifications
                }
                
        except Exception as e:
            logging.error(f"Error getting notification statistics: {e}")
            return {}
    
    def test_notification_setup(self, user_id: int) -> Dict[str, Any]:
        """Test notification setup and configuration"""
        preferences = self.get_user_notification_preferences(user_id)
        results = {
            'email_configured': bool(self.email_user and self.email_password),
            'whatsapp_configured': bool(self.twilio_account_sid and self.twilio_auth_token),
            'user_email_set': bool(preferences.get('email_address')),
            'user_whatsapp_set': bool(preferences.get('whatsapp_number')),
            'email_enabled': preferences.get('email_notifications', False),
            'whatsapp_enabled': preferences.get('whatsapp_notifications', False)
        }
        
        # Test email if configured
        if results['email_configured'] and results['user_email_set'] and results['email_enabled']:
            test_email = self._send_email_notification(
                preferences['email_address'],
                "🧪 Agricultural AI Advisor - Test Notification",
                "This is a test notification to verify your email setup is working correctly.\n\nIf you receive this message, your email notifications are configured properly!"
            )
            results['email_test'] = test_email
        
        return results
