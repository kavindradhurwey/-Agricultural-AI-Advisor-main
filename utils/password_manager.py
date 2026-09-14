"""
Password Manager for Agricultural AI Advisor
Handles password updates, API key management, and security features
"""

import streamlit as st
import hashlib
import secrets
import os
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import json
import bcrypt
from utils.database_manager import DatabaseManager

class PasswordManager:
    """Manages user passwords and API keys with security best practices"""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.api_keys_file = "config/api_keys.json"
        self.ensure_api_keys_file()
    
    def ensure_api_keys_file(self):
        """Ensure API keys configuration file exists"""
        os.makedirs("config", exist_ok=True)
        if not os.path.exists(self.api_keys_file):
            default_keys = {
                "weather": {
                    "primary": "YOUR_WEATHER_API_KEY",
                    "backup": "YOUR_BACKUP_WEATHER_API_KEY"
                },
                "groq": {
                    "primary": "YOUR_GROQ_API_KEY",
                    "backup": "YOUR_BACKUP_GROQ_API_KEY"
                },
                "twilio": {
                    "account_sid": "AC_placeholder",
                    "auth_token": "placeholder_token"
                },
                "google_translate": {
                    "api_key": "placeholder_google_key"
                },
                "last_updated": datetime.now().isoformat()
            }
            with open(self.api_keys_file, 'w') as f:
                json.dump(default_keys, f, indent=2)
    
    def get_api_keys(self) -> Dict[str, Any]:
        """Get all API keys"""
        try:
            with open(self.api_keys_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            st.error(f"Error loading API keys: {e}")
            return {}
    
    def update_api_key(self, user_id: int, service: str, new_key: str) -> bool:
        """Update specific API key for user"""
        try:
            keys = self.get_api_keys()
            if "users" not in keys:
                keys["users"] = {}
            if str(user_id) not in keys["users"]:
                keys["users"][str(user_id)] = {}
            
            keys["users"][str(user_id)][service] = {
                "key": new_key,
                "updated_at": datetime.now().isoformat()
            }
            keys["last_updated"] = datetime.now().isoformat()
            
            with open(self.api_keys_file, 'w') as f:
                json.dump(keys, f, indent=2)
            return True
        except Exception as e:
            st.error(f"Error updating API key: {e}")
            return False
    
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash (supports both bcrypt and SHA-256)"""
        try:
            # Try bcrypt first (new format)
            if hashed.startswith('$2b$') or hashed.startswith('$2a$'):
                return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
            else:
                # Fall back to SHA-256 (old format for compatibility)
                import hashlib
                sha256_hash = hashlib.sha256(password.encode()).hexdigest()
                return sha256_hash == hashed
        except Exception as e:
            print(f"Password verification error: {e}")
            return False
    
    def update_user_password(self, user_id: int, current_password: str, new_password: str) -> tuple[bool, str]:
        """Update user password with validation"""
        try:
            # Get current user data
            user_data = self.db_manager.get_user_by_id(user_id)
            if not user_data:
                return False, "User not found"
            
            # Verify current password
            if not self.verify_password(current_password, user_data['password']):
                return False, "Current password is incorrect"
            
            # Validate new password
            if len(new_password) < 8:
                return False, "Password must be at least 8 characters long"
            
            # Hash new password
            new_hash = self.hash_password(new_password)
            
            # Update in database
            success = self.db_manager.update_user_password(user_id, new_hash)
            if success:
                return True, "Password updated successfully"
            else:
                return False, "Failed to update password"
                
        except Exception as e:
            return False, str(e)
    
    def get_password_strength_score(self, password: str) -> Dict[str, Any]:
        """Calculate password strength score"""
        score = 0
        feedback = []
        
        # Length check
        if len(password) >= 8:
            score += 20
        else:
            feedback.append("Use at least 8 characters")
        
        # Uppercase check
        if any(c.isupper() for c in password):
            score += 20
        else:
            feedback.append("Include uppercase letters")
        
        # Lowercase check
        if any(c.islower() for c in password):
            score += 20
        else:
            feedback.append("Include lowercase letters")
        
        # Numbers check
        if any(c.isdigit() for c in password):
            score += 20
        else:
            feedback.append("Include numbers")
        
        # Special characters check
        if any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            score += 20
        else:
            feedback.append("Include special characters")
        
        # Common patterns check
        common_patterns = ["123", "abc", "password", "admin", "user"]
        if any(pattern in password.lower() for pattern in common_patterns):
            score -= 30
            feedback.append("Avoid common patterns")
        
        strength = "Very Weak"
        if score >= 80:
            strength = "Very Strong"
        elif score >= 60:
            strength = "Strong"
        elif score >= 40:
            strength = "Medium"
        elif score >= 20:
            strength = "Weak"
        
        return {
            "score": max(0, min(100, score)),
            "strength": strength,
            "feedback": feedback
        }
    
    def generate_secure_password(self, length: int = 12) -> str:
        """Generate a secure random password"""
        import string
        
        chars = string.ascii_letters + string.digits + "!@#$%^&*()"
        password = ''.join(secrets.choice(chars) for _ in range(length))
        return password
    
    def mask_api_key(self, key: str) -> str:
        """Mask API key for display (show only first 4 and last 4 characters)"""
        if len(key) <= 8:
            return "*" * len(key)
        return key[:4] + "*" * (len(key) - 8) + key[-4:]
    
    def validate_api_key(self, service: str, key: str) -> bool:
        """Basic validation for API key format"""
        service_patterns = {
            "weather": r"^[a-zA-Z0-9]{32}$",
            "groq": r"^gsk_[a-zA-Z0-9]+$",
            "twilio": {
                "account_sid": r"^AC[a-zA-Z0-9]{32}$",
                "auth_token": r"^[a-zA-Z0-9]{32}$"
            }
        }
        
        # Basic length checks
        if len(key) < 10:
            return False
        
        return True
    
    def get_security_audit(self, user_id: int) -> Dict[str, Any]:
        """Get security audit information for user"""
        try:
            user_data = self.db_manager.get_user_by_id(user_id)
            if not user_data:
                return {"error": "User not found"}
            
            # Check password age
            created_date = user_data.get('created_at', datetime.now())
            days_since_creation = (datetime.now() - created_date).days
            
            # Check if password needs update (older than 90 days)
            password_needs_update = days_since_creation > 90
            
            return {
                "user_id": user_id,
                "username": user_data.get('username', 'Unknown'),
                "account_age_days": days_since_creation,
                "password_needs_update": password_needs_update,
                "last_login": user_data.get('last_login', 'Never'),
                "api_keys_configured": len(self.get_api_keys()) > 0
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def get_user_api_keys(self, user_id: int) -> Dict[str, Any]:
        """Get API keys for specific user"""
        try:
            keys = self.get_api_keys()
            user_keys = keys.get("users", {}).get(str(user_id), {})
            return user_keys
        except Exception as e:
            st.error(f"Error getting user API keys: {e}")
            return {}
    
    def get_backup_api_keys(self, user_id: int) -> Dict[str, Any]:
        """Get backup API keys for user"""
        try:
            keys = self.get_api_keys()
            backup_keys = keys.get("backup_keys", {}).get(str(user_id), {})
            return backup_keys
        except Exception as e:
            st.error(f"Error getting backup API keys: {e}")
            return {}
    
    def generate_backup_api_keys(self) -> Dict[str, Any]:
        """Generate backup API keys"""
        backup_keys = {}
        services = ["weather_backup", "ai_backup", "sms_backup", "email_backup", "storage_backup"]
        
        for service in services:
            backup_keys[service] = {
                "key": self.generate_api_key(),
                "created_at": datetime.now().isoformat()
            }
        
        return backup_keys
    
    def save_backup_api_keys(self, user_id: int, backup_keys: Dict[str, Any]) -> bool:
        """Save backup API keys for user"""
        try:
            keys = self.get_api_keys()
            if "backup_keys" not in keys:
                keys["backup_keys"] = {}
            
            keys["backup_keys"][str(user_id)] = backup_keys
            keys["last_updated"] = datetime.now().isoformat()
            
            with open(self.api_keys_file, 'w') as f:
                json.dump(keys, f, indent=2)
            return True
        except Exception as e:
            st.error(f"Error saving backup API keys: {e}")
            return False
    
    def generate_api_key(self, length: int = 32) -> str:
        """Generate a random API key"""
        import string
        chars = string.ascii_letters + string.digits
        return ''.join(secrets.choice(chars) for _ in range(length))
    
    def check_password_strength(self, password: str) -> int:
        """Check password strength and return score (0-4)"""
        score = 0
        
        # Length check
        if len(password) >= 8:
            score += 1
        
        # Uppercase check
        if any(c.isupper() for c in password):
            score += 1
        
        # Lowercase check
        if any(c.islower() for c in password):
            score += 1
        
        # Numbers check
        if any(c.isdigit() for c in password):
            score += 1
        
        # Special characters check
        if any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            score += 1
        
        return min(score, 4)
    
    def get_security_audit_info(self, user_id: int) -> Dict[str, Any]:
        """Get security audit information for user"""
        try:
            user_data = self.db_manager.get_user_by_id(user_id)
            if not user_data:
                return {"error": "User not found"}
            
            # Check password age
            created_date = user_data.get('created_at', datetime.now())
            if isinstance(created_date, str):
                try:
                    created_date = datetime.fromisoformat(created_date)
                except:
                    created_date = datetime.now()
            
            days_since_creation = (datetime.now() - created_date).days
            
            # Get API keys count
            user_keys = self.get_user_api_keys(user_id)
            backup_keys = self.get_backup_api_keys(user_id)
            
            return {
                "password_age_days": days_since_creation,
                "last_login": user_data.get('last_login', 'Never'),
                "api_keys_count": len(user_keys),
                "backup_keys": len(backup_keys) > 0
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def export_security_report(self, user_id: int) -> str:
        """Export security report as JSON"""
        try:
            security_info = self.get_security_audit_info(user_id)
            user_keys = self.get_user_api_keys(user_id)
            backup_keys = self.get_backup_api_keys(user_id)
            
            report = {
                "user_id": user_id,
                "report_date": datetime.now().isoformat(),
                "security_info": security_info,
                "api_keys_configured": list(user_keys.keys()),
                "backup_keys_configured": list(backup_keys.keys()),
                "recommendations": []
            }
            
            # Add recommendations
            if security_info.get('password_age_days', 0) > 90:
                report["recommendations"].append("Consider changing password (older than 90 days)")
            if len(user_keys) == 0:
                report["recommendations"].append("Add API keys for enhanced functionality")
            if len(backup_keys) == 0:
                report["recommendations"].append("Generate backup API keys for redundancy")
            
            return json.dumps(report, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)
