#!/usr/bin/env python3
"""
Authentication manager for user login/signup
"""

import streamlit as st
import re
from typing import Optional, Dict, Any
from database_manager import get_database_manager
import hashlib
from datetime import datetime


class AuthManager:
    """Manages user authentication and session state"""
    
    def __init__(self):
        self.db_manager = get_database_manager()
        self._init_session_state()
    
    def _init_session_state(self):
        """Initialize session state variables"""
        if 'authenticated' not in st.session_state:
            st.session_state.authenticated = False
        if 'user' not in st.session_state:
            st.session_state.user = None
        if 'auth_mode' not in st.session_state:
            st.session_state.auth_mode = 'login'
    
    def validate_email(self, email: str) -> bool:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def validate_password(self, password: str) -> tuple[bool, str]:
        """Validate password strength"""
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"
        if not re.search(r'[A-Z]', password):
            return False, "Password must contain at least one uppercase letter"
        if not re.search(r'[a-z]', password):
            return False, "Password must contain at least one lowercase letter"
        if not re.search(r'\d', password):
            return False, "Password must contain at least one number"
        return True, "Password is valid"
    
    def render_auth_page(self):
        """Render the authentication page"""
        st.markdown("""
        <style>
        .auth-container {
            max-width: 400px;
            margin: auto;
            padding: 2rem;
            background-color: #f0f2f6;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Title and description
        st.title("🚀 Space Mission Design Assistant")
        st.markdown("### Welcome! Please login or create an account")
        
        # Guest access option
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("Continue as Guest", use_container_width=True, type="secondary"):
                st.session_state.authenticated = 'guest'
                st.session_state.user = {
                    'id': None,
                    'username': 'Guest',
                    'email': None
                }
                st.rerun()
        
        st.divider()
        
        # Auth mode toggle
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Login", use_container_width=True, 
                        type="primary" if st.session_state.auth_mode == 'login' else 'secondary'):
                st.session_state.auth_mode = 'login'
                st.rerun()
        with col2:
            if st.button("Sign Up", use_container_width=True,
                        type="primary" if st.session_state.auth_mode == 'signup' else 'secondary'):
                st.session_state.auth_mode = 'signup'
                st.rerun()
        
        # Render appropriate form
        if st.session_state.auth_mode == 'login':
            self._render_login_form()
        else:
            self._render_signup_form()
    
    def _render_login_form(self):
        """Render login form"""
        with st.form("login_form"):
            st.subheader("Login")
            
            username_or_email = st.text_input(
                "Username or Email",
                placeholder="Enter your username or email"
            )
            
            password = st.text_input(
                "Password",
                type="password",
                placeholder="Enter your password"
            )
            
            col1, col2 = st.columns(2)
            with col1:
                remember_me = st.checkbox("Remember me")
            
            submit = st.form_submit_button("Login", use_container_width=True, type="primary")
            
            if submit:
                if not username_or_email or not password:
                    st.error("Please fill in all fields")
                else:
                    user = self.db_manager.authenticate_user(username_or_email, password)
                    if user:
                        st.session_state.authenticated = True
                        st.session_state.user = user
                        st.success(f"Welcome back, {user['username']}!")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("Invalid credentials. Please try again.")
    
    def _render_signup_form(self):
        """Render signup form"""
        with st.form("signup_form"):
            st.subheader("Create Account")
            
            username = st.text_input(
                "Username",
                placeholder="Choose a username",
                help="Username must be unique"
            )
            
            email = st.text_input(
                "Email",
                placeholder="Enter your email address"
            )
            
            password = st.text_input(
                "Password",
                type="password",
                placeholder="Create a strong password",
                help="Must be at least 8 characters with uppercase, lowercase, and numbers"
            )
            
            confirm_password = st.text_input(
                "Confirm Password",
                type="password",
                placeholder="Re-enter your password"
            )
            
            terms = st.checkbox("I agree to the Terms of Service and Privacy Policy")
            
            submit = st.form_submit_button("Create Account", use_container_width=True, type="primary")
            
            if submit:
                # Validation
                errors = []
                
                if not all([username, email, password, confirm_password]):
                    errors.append("Please fill in all fields")
                
                if username and len(username) < 3:
                    errors.append("Username must be at least 3 characters")
                
                if email and not self.validate_email(email):
                    errors.append("Please enter a valid email address")
                
                if password:
                    valid, msg = self.validate_password(password)
                    if not valid:
                        errors.append(msg)
                
                if password != confirm_password:
                    errors.append("Passwords do not match")
                
                if not terms:
                    errors.append("You must agree to the Terms of Service")
                
                if errors:
                    for error in errors:
                        st.error(error)
                else:
                    # Create user
                    user = self.db_manager.create_user(username, email, password)
                    if user:
                        st.session_state.authenticated = True
                        st.session_state.user = user
                        st.success(f"Welcome, {user['username']}! Your account has been created.")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("Username or email already exists. Please try different ones.")
    
    def render_user_menu(self):
        """Render user menu in sidebar"""
        if st.session_state.authenticated:
            st.sidebar.markdown("---")
            st.sidebar.markdown(f"### 👤 {st.session_state.user['username']}")
            
            if st.session_state.user['id']:  # Not guest
                # Show user stats
                stats = self.db_manager.get_user_stats(st.session_state.user['id'])
                st.sidebar.text(f"Total messages: {stats['total_messages']}")
                st.sidebar.text(f"Chat sessions: {stats['unique_sessions']}")
            
            if st.sidebar.button("Logout", use_container_width=True):
                self.logout()
    
    def logout(self):
        """Logout user"""
        st.session_state.authenticated = False
        st.session_state.user = None
        st.session_state.messages = []
        st.session_state.initialized = False
        st.rerun()
    
    def is_authenticated(self) -> bool:
        """Check if user is authenticated"""
        return st.session_state.authenticated in [True, 'guest']
    
    def is_registered_user(self) -> bool:
        """Check if user is registered (not guest)"""
        return st.session_state.authenticated == True and st.session_state.user['id'] is not None
    
    def get_current_user_id(self) -> Optional[int]:
        """Get current user ID (None for guests)"""
        if self.is_registered_user():
            return st.session_state.user['id']
        return None