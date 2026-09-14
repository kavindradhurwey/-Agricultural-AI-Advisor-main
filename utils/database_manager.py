"""
Database Manager for Persistent Storage
Handles user authentication, profile storage, and chat history persistence
"""

import sqlite3
import hashlib
import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import uuid

class DatabaseManager:
    """Manages SQLite database for persistent user data and chat history"""
    
    def __init__(self, db_path: str = "data/agricultural_app.db"):
        self.db_path = db_path
        self.ensure_data_directory()
        self.init_database()
    
    def ensure_data_directory(self):
        """Ensure the data directory exists"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
    
    def init_database(self):
        """Initialize database tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1
                )
            ''')
            
            # User profiles table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    name TEXT,
                    location TEXT,
                    farm_size REAL,
                    primary_crops TEXT,  -- JSON array
                    farming_type TEXT,
                    experience INTEGER,
                    preferred_language TEXT DEFAULT 'English',
                    notification_preferences TEXT,  -- JSON array
                    interests TEXT,  -- JSON array
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            ''')
            
            # Chat history table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS chat_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    session_id TEXT,
                    user_message TEXT NOT NULL,
                    assistant_response TEXT NOT NULL,
                    message_type TEXT DEFAULT 'chat',  -- chat, financial, disease, weather
                    metadata TEXT,  -- JSON for additional context
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            ''')
            
            # User sessions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    session_token TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            ''')
            
            conn.commit()
    
    def hash_password(self, password: str) -> str:
        """Hash password using SHA-256"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def create_user(self, username: str, password: str) -> Tuple[bool, str]:
        """Create a new user account"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if username already exists
                cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
                if cursor.fetchone():
                    return False, "Username already exists"
                
                # Create new user
                password_hash = self.hash_password(password)
                cursor.execute('''
                    INSERT INTO users (username, password_hash)
                    VALUES (?, ?)
                ''', (username, password_hash))
                
                user_id = cursor.lastrowid
                
                # Create empty profile
                cursor.execute('''
                    INSERT INTO user_profiles (user_id, name, preferred_language)
                    VALUES (?, ?, ?)
                ''', (user_id, username, 'English'))
                
                conn.commit()
                return True, "User created successfully"
                
        except Exception as e:
            return False, f"Error creating user: {str(e)}"
    
    def authenticate_user(self, username: str, password: str) -> Tuple[bool, Optional[int]]:
        """Authenticate user and return user_id if successful"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get user data including stored password hash
                cursor.execute('''
                    SELECT id, password_hash FROM users 
                    WHERE username = ? AND is_active = 1
                ''', (username,))
                
                result = cursor.fetchone()
                if result:
                    user_id, stored_hash = result
                    
                    # Use backward-compatible password verification
                    if self.verify_password(password, stored_hash):
                        # Update last login
                        cursor.execute('''
                            UPDATE users SET last_login = CURRENT_TIMESTAMP 
                            WHERE id = ?
                        ''', (user_id,))
                        conn.commit()
                        return True, user_id
                
                return False, None
                
        except Exception as e:
            print(f"Authentication error: {e}")
            return False, None
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash (supports both bcrypt and SHA-256)"""
        try:
            # Try bcrypt first (new format)
            if hashed.startswith('$2b$') or hashed.startswith('$2a$'):
                import bcrypt
                return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
            else:
                # Fall back to SHA-256 (old format for compatibility)
                sha256_hash = self.hash_password(password)
                return sha256_hash == hashed
        except Exception as e:
            print(f"Password verification error: {e}")
            return False
    
    def create_session(self, user_id: int) -> str:
        """Create a new session token for user"""
        try:
            session_token = str(uuid.uuid4())
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO user_sessions (user_id, session_token, expires_at)
                    VALUES (?, ?, datetime('now', '+30 days'))
                ''', (user_id, session_token))
                conn.commit()
                return session_token
        except Exception as e:
            print(f"Session creation error: {e}")
            return ""
    
    def validate_session(self, session_token: str) -> Optional[int]:
        """Validate session token and return user_id"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT user_id FROM user_sessions 
                    WHERE session_token = ? AND is_active = 1 
                    AND expires_at > CURRENT_TIMESTAMP
                ''', (session_token,))
                
                result = cursor.fetchone()
                return result[0] if result else None
                
        except Exception as e:
            print(f"Session validation error: {e}")
            return None
    
    def save_user_profile(self, user_id: int, profile_data: Dict[str, Any]) -> bool:
        """Save or update user profile"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Convert lists to JSON strings
                primary_crops = json.dumps(profile_data.get('primary_crops', []))
                notification_preferences = json.dumps(profile_data.get('notification_preferences', []))
                interests = json.dumps(profile_data.get('interests', []))
                
                cursor.execute('''
                    INSERT OR REPLACE INTO user_profiles 
                    (user_id, name, location, farm_size, primary_crops, farming_type, 
                     experience, preferred_language, notification_preferences, interests, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (
                    user_id,
                    profile_data.get('name', ''),
                    profile_data.get('location', ''),
                    profile_data.get('farm_size', 0.0),
                    primary_crops,
                    profile_data.get('farming_type', 'Traditional'),
                    profile_data.get('experience', 0),
                    profile_data.get('preferred_language', 'English'),
                    notification_preferences,
                    interests
                ))
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"Profile save error: {e}")
            return False
    
    def get_user_profile(self, user_id: int) -> Dict[str, Any]:
        """Get user profile data"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT name, location, farm_size, primary_crops, farming_type,
                           experience, preferred_language, notification_preferences, interests
                    FROM user_profiles WHERE user_id = ?
                ''', (user_id,))
                
                result = cursor.fetchone()
                if result:
                    return {
                        'name': result[0] or '',
                        'location': result[1] or '',
                        'farm_size': result[2] or 0.0,
                        'primary_crops': json.loads(result[3] or '[]'),
                        'farming_type': result[4] or 'Traditional',
                        'experience': result[5] or 0,
                        'preferred_language': result[6] or 'English',
                        'notification_preferences': json.loads(result[7] or '[]'),
                        'interests': json.loads(result[8] or '[]')
                    }
                
                return {}
                
        except Exception as e:
            print(f"Profile fetch error: {e}")
            return {}
    
    def save_chat_message(self, user_id: int, user_message: str, assistant_response: str, 
                         message_type: str = 'chat', metadata: Dict[str, Any] = None) -> bool:
        """Save chat message to history"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                session_id = str(uuid.uuid4())
                metadata_json = json.dumps(metadata or {})
                
                cursor.execute('''
                    INSERT INTO chat_history 
                    (user_id, session_id, user_message, assistant_response, message_type, metadata)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (user_id, session_id, user_message, assistant_response, message_type, metadata_json))
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"Chat save error: {e}")
            return False
    
    def get_chat_history(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent chat history for user"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT user_message, assistant_response, message_type, created_at, metadata
                    FROM chat_history 
                    WHERE user_id = ? 
                    ORDER BY created_at DESC 
                    LIMIT ?
                ''', (user_id, limit))
                
                results = cursor.fetchall()
                chat_history = []
                
                for result in results:
                    chat_history.append({
                        'user': result[0],
                        'assistant': result[1],
                        'type': result[2],
                        'timestamp': result[3],
                        'metadata': json.loads(result[4] or '{}')
                    })
                
                return list(reversed(chat_history))  # Return in chronological order
                
        except Exception as e:
            print(f"Chat history fetch error: {e}")
            return []
    
    def get_username(self, user_id: int) -> str:
        """Get username by user_id"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT username FROM users WHERE id = ?", (user_id,))
                result = cursor.fetchone()
                return result[0] if result else ""
        except Exception as e:
            print(f"Username fetch error: {e}")
            return ""
    
    def cleanup_expired_sessions(self):
        """Remove expired sessions"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE user_sessions SET is_active = 0 
                    WHERE expires_at < CURRENT_TIMESTAMP
                ''')
                conn.commit()
        except Exception as e:
            print(f"Session cleanup error: {e}")
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user information by user ID"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, username, password_hash, created_at, last_login, is_active
                    FROM users WHERE id = ?
                ''', (user_id,))
                
                result = cursor.fetchone()
                if result:
                    return {
                        'id': result[0],
                        'username': result[1],
                        'password': result[2],  # password_hash
                        'created_at': result[3],
                        'last_login': result[4],
                        'is_active': result[5]
                    }
                return None
                
        except Exception as e:
            print(f"Get user by ID error: {e}")
            return None
    
    def update_user_password(self, user_id: int, new_password_hash: str) -> bool:
        """Update user password with new hash"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE users SET password_hash = ? WHERE id = ?
                ''', (new_password_hash, user_id))
                
                conn.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            print(f"Update password error: {e}")
            return False

    def clear_all_chat_history(self) -> int:
        """Delete all chat history records across all users. Returns rows deleted."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM chat_history')
                deleted = cursor.rowcount if cursor.rowcount is not None else 0
                conn.commit()
                return deleted
        except Exception as e:
            print(f"Clear all chat history error: {e}")
            return 0

    def clear_chat_history_for_user(self, user_id: int) -> int:
        """Delete all chat history for a specific user. Returns rows deleted."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM chat_history WHERE user_id = ?', (user_id,))
                deleted = cursor.rowcount if cursor.rowcount is not None else 0
                conn.commit()
                return deleted
        except Exception as e:
            print(f"Clear chat history for user error: {e}")
            return 0

    def prune_chat_history_keep_last_n_per_user(self, n: int = 50) -> int:
        """
        For each user, keep only the last N chat messages (by created_at) and delete older ones.
        Returns total rows deleted across all users.
        """
        if n < 0:
            return 0
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # Find users who have more than N messages
                cursor.execute('''
                    SELECT user_id FROM (
                        SELECT user_id, COUNT(*) AS cnt
                        FROM chat_history
                        GROUP BY user_id
                    ) WHERE cnt > ?
                ''', (n,))
                users = [row[0] for row in cursor.fetchall()]

                total_deleted = 0
                for uid in users:
                    # Delete messages older than the newest N for this user
                    cursor.execute('''
                        DELETE FROM chat_history
                        WHERE user_id = ? AND id NOT IN (
                            SELECT id FROM chat_history
                            WHERE user_id = ?
                            ORDER BY created_at DESC, id DESC
                            LIMIT ?
                        )
                    ''', (uid, uid, n))
                    total_deleted += cursor.rowcount if cursor.rowcount is not None else 0

                conn.commit()
                return total_deleted
        except Exception as e:
            print(f"Prune chat history error: {e}")
            return 0
