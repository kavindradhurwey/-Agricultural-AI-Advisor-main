"""
Authentication Manager for Streamlit Integration
Handles user login/signup with seamless integration to existing app
"""

import streamlit as st
from typing import Optional, Tuple
from utils.database_manager import DatabaseManager

class AuthManager:
    """Manages authentication flow in Streamlit app"""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.init_session_state()
    
    def init_session_state(self):
        """Initialize authentication-related session state"""
        if 'authenticated' not in st.session_state:
            st.session_state.authenticated = False
        if 'user_id' not in st.session_state:
            st.session_state.user_id = None
        if 'username' not in st.session_state:
            st.session_state.username = None
        if 'session_token' not in st.session_state:
            st.session_state.session_token = None
    
    def show_auth_form(self) -> bool:
        """Show login/signup form and handle authentication"""
        # Check if there's a valid session token first
        if st.session_state.get('session_token'):
            if self.validate_session():
                return True
        
        st.markdown("""
        <div style="max-width: 400px; margin: 0 auto; padding: 2rem; 
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.3);">
        <h2 style="color: white; text-align: center; margin-bottom: 2rem;">
        🌾 Agricultural AI Advisor
        </h2>
        <p style="color: white; text-align: center; margin-bottom: 2rem;">
        Sign in to save your farm profile and chat history
        </p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Add guest mode option
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🚀 Continue as Guest", use_container_width=True):
                st.session_state.authenticated = False
                st.session_state.guest_mode = True
                st.info("💡 **Guest Mode**: Your data will be saved for this session only. Sign up to save permanently!")
                return True
        
        st.markdown("---")
        
        # Create tabs for login and signup
        tab1, tab2 = st.tabs(["🔑 Login", "📝 Sign Up"])
        
        with tab1:
            return self._show_login_form()
        
        with tab2:
            return self._show_signup_form()
    
    def _show_login_form(self) -> bool:
        """Show login form"""
        with st.form("login_form"):
            st.markdown("### Welcome Back! 👋")
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                login_button = st.form_submit_button("🚀 Login", use_container_width=True)
            
            if login_button:
                if username and password:
                    success, user_id = self.db_manager.authenticate_user(username, password)
                    if success:
                        # Set session state
                        st.session_state.authenticated = True
                        st.session_state.user_id = user_id
                        st.session_state.username = username
                        st.session_state.session_token = self.db_manager.create_session(user_id)
                        
                        # Load user profile into session state
                        self._load_user_data()
                        
                        st.success("✅ Login successful! Welcome back!")
                        st.rerun()
                        return True
                    else:
                        st.error("❌ Invalid username or password")
                else:
                    st.warning("⚠️ Please enter both username and password")
        
        return False
    
    def _show_signup_form(self) -> bool:
        """Show signup form"""
        with st.form("signup_form"):
            st.markdown("### Create New Account 🌱")
            new_username = st.text_input("Choose Username", placeholder="Enter a unique username")
            new_password = st.text_input("Create Password", type="password", placeholder="Create a secure password")
            confirm_password = st.text_input("Confirm Password", type="password", placeholder="Confirm your password")
            
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                signup_button = st.form_submit_button("🌾 Create Account", use_container_width=True)
            
            if signup_button:
                if new_username and new_password and confirm_password:
                    if new_password == confirm_password:
                        if len(new_password) >= 6:
                            success, message = self.db_manager.create_user(new_username, new_password)
                            if success:
                                st.success("✅ Account created successfully! Please login.")
                                return True
                            else:
                                st.error(f"❌ {message}")
                        else:
                            st.warning("⚠️ Password must be at least 6 characters long")
                    else:
                        st.error("❌ Passwords do not match")
                else:
                    st.warning("⚠️ Please fill in all fields")
        
        return False
    
    def _load_user_data(self):
        """Load user profile and chat history from database into session state"""
        if st.session_state.user_id:
            # Load user profile
            profile_data = self.db_manager.get_user_profile(st.session_state.user_id)
            if profile_data:
                st.session_state.user_profile = profile_data
                # Set language preference
                st.session_state.language = profile_data.get('preferred_language', 'English')
            
            # Load chat history
            chat_history = self.db_manager.get_chat_history(st.session_state.user_id, limit=10)
            if chat_history:
                st.session_state.chat_history = chat_history
    
    def save_user_profile(self):
        """Save current session user profile to database"""
        if st.session_state.authenticated and st.session_state.user_id:
            return self.db_manager.save_user_profile(
                st.session_state.user_id, 
                st.session_state.user_profile
            )
        return False
    
    def save_chat_message(self, user_message: str, assistant_response: str, 
                         message_type: str = 'chat', metadata: dict = None):
        """Save chat message to database and session state"""
        if st.session_state.authenticated and st.session_state.user_id:
            # Save to database
            self.db_manager.save_chat_message(
                st.session_state.user_id,
                user_message,
                assistant_response,
                message_type,
                metadata
            )
        
        # Always save to session state for immediate display
        chat_entry = {
            'user': user_message,
            'assistant': assistant_response,
            'type': message_type,
            'metadata': metadata or {}
        }
        
        if 'chat_history' not in st.session_state:
            st.session_state.chat_history = []
        
        st.session_state.chat_history.append(chat_entry)
    
    def logout(self):
        """Logout user and clear session"""
        # Save current profile before logout
        if st.session_state.authenticated:
            self.save_user_profile()
        
        # Clear authentication session state
        st.session_state.authenticated = False
        st.session_state.user_id = None
        st.session_state.username = None
        st.session_state.session_token = None
        
        # Keep user_profile and chat_history for guest mode
        # but they won't be persisted
        
        st.rerun()
    
    def show_user_info(self):
        """Show user info in sidebar"""
        if st.session_state.authenticated:
            st.sidebar.markdown("---")
            st.sidebar.markdown(f"### 👤 Welcome, {st.session_state.username}!")
            st.sidebar.success("🔐 **Authenticated** - Data saved permanently")
            
            if st.sidebar.button("🚪 Logout", use_container_width=True):
                self.logout()
            
            # Show profile summary
            if st.session_state.user_profile:
                profile = st.session_state.user_profile
                if profile.get('name'):
                    st.sidebar.markdown(f"**Name:** {profile['name']}")
                if profile.get('location'):
                    st.sidebar.markdown(f"**Location:** {profile['location']}")
                if profile.get('farm_size'):
                    st.sidebar.markdown(f"**Farm Size:** {profile['farm_size']} acres")
        elif st.session_state.get('guest_mode', False):
            st.sidebar.markdown("---")
            st.sidebar.markdown("### 👋 Guest Mode")
            st.sidebar.warning("⚠️ **Session Only** - Data not saved permanently")
            
            if st.sidebar.button("🔑 Sign In to Save Data", use_container_width=True):
                # Reset guest mode to show auth form
                st.session_state.guest_mode = False
                st.rerun()
            
            st.sidebar.info("💡 **Sign in to save your profile and chat history permanently!**")
    
    def is_authenticated(self) -> bool:
        """Check if user is authenticated"""
        return st.session_state.get('authenticated', False)
    
    def get_user_id(self) -> Optional[int]:
        """Get current user ID"""
        return st.session_state.get('user_id')
    
    def get_username(self) -> Optional[str]:
        """Get current username"""
        return st.session_state.get('username')
    
    def validate_session(self) -> bool:
        """Validate current session token"""
        if st.session_state.get('session_token'):
            user_id = self.db_manager.validate_session(st.session_state.session_token)
            if user_id:
                return True
            else:
                # Session expired, logout
                self.logout()
                return False
        return False
