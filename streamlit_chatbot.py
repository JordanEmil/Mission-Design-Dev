#!/usr/bin/env python3
"""
Space Mission RAG Chatbot - Streamlit Interface
Web-based interface for querying space mission knowledge base
"""

# SQLite compatibility fix for Streamlit Cloud
import sqlite_fix

import os
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
import hashlib

import streamlit as st
from query_pipeline import SpaceMissionQueryEngine
from llama_index.core.response_synthesizers import ResponseMode
from database_manager import get_database_manager
from auth_manager import AuthManager


class StreamlitSpaceMissionChatbot:
    """Streamlit-based chatbot for space mission queries"""
    
    def __init__(self, log_dir: str = "./chat_logs"):
        """
        Initialize the Streamlit chatbot interface
        
        Args:
            log_dir: Directory to store chat logs
        """
        self.log_dir = Path(log_dir)
        self.db_manager = get_database_manager()
        self.auth_manager = AuthManager()
        
        # Create log directory if it doesn't exist
        self.log_dir.mkdir(exist_ok=True)
        
        # Initialize session state
        if 'initialized' not in st.session_state:
            st.session_state.initialized = False
            st.session_state.messages = []
            st.session_state.session_id = self._generate_session_id()
            st.session_state.session_start = datetime.now()
            st.session_state.show_sources = True
            st.session_state.query_count = 0
            st.session_state.query_engine = None
            st.session_state.authenticated = False
            st.session_state.current_user = None
            st.session_state.show_login = True
    
    def _generate_session_id(self) -> str:
        """Generate a unique session ID"""
        timestamp = datetime.now().isoformat()
        return hashlib.md5(timestamp.encode()).hexdigest()[:8]
    
    def _save_message_to_db(self, role: str, content: str, sources: List[Dict] = None):
        """Save a single message to database for logged in users"""
        if st.session_state.current_user:
            self.db_manager.save_chat_message(
                session_id=st.session_state.session_id,
                message_type=role,
                message=content,
                sources=sources,
                user_id=st.session_state.current_user['id']
            )
    
    def _load_user_history(self):
        """Load chat history for logged in users"""
        if st.session_state.current_user and len(st.session_state.messages) == 0:
            # Load recent messages from current session
            history = self.db_manager.get_session_chat_history(st.session_state.session_id)
            for msg in history:
                st.session_state.messages.append({
                    "role": msg["message_type"],
                    "content": msg["message"],
                    "timestamp": msg["created_at"],
                    "sources": msg.get("sources", [])
                })
    
    def _format_sources(self, sources: List[Dict]) -> str:
        """Format source documents for display with deduplication"""
        if not sources:
            return ""
            
        # Deduplicate sources based on mission_id
        seen_missions = {}
        unique_sources = []
        
        for source in sources:
            metadata = source.get('metadata', {})
            mission_id = metadata.get('mission_id', '')
            
            if mission_id:
                if mission_id not in seen_missions:
                    seen_missions[mission_id] = source
                    unique_sources.append(source)
                elif source.get('score', 0) > seen_missions[mission_id].get('score', 0):
                    idx = unique_sources.index(seen_missions[mission_id])
                    unique_sources[idx] = source
                    seen_missions[mission_id] = source
            else:
                unique_sources.append(source)
            
            if len(unique_sources) >= 20:
                break
        
        # Sort by score descending
        unique_sources.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        formatted = "\n\n**Sources:**"
        for i, source in enumerate(unique_sources, 1):
            metadata = source.get('metadata', {})
            title = metadata.get('title', 'Unknown Mission')
            url = metadata.get('url', '')
            score = source.get('score', 0)
            
            # Clean up title if needed
            if title and ' - eoPortal' in title:
                title = title.replace(' - eoPortal', '')
            
            # Format with URL if available
            if url:
                if not url.startswith('http'):
                    url = f"https://{url}"
                formatted += f"\n{i}. [{title}]({url}) (relevance: {score:.3f})"
            else:
                formatted += f"\n{i}. **{title}** (relevance: {score:.3f})"
        
        return formatted
    
    def _process_query(self, query: str) -> Dict[str, Any]:
        """Process a user query and return the result"""
        try:
            result = st.session_state.query_engine.query(
                query,
                response_mode=ResponseMode.COMPACT,
                return_sources=True,
                verbose=False
            )
            
            # Increment query count
            st.session_state.query_count += 1
            
            return result
            
        except Exception as e:
            return {
                'response': f"Error processing query: {str(e)}",
                'sources': [],
                'metadata': {'response_time': 0}
            }
    
    def render_login_page(self):
        """Render login/signup page"""
        st.title("Space Mission Design Assistant - Authored by Emil Ares")
        st.markdown("Welcome! Please login or create an account to begin.")
        
        tab1, tab2 = st.tabs(["Login", "Sign Up"])
        
        with tab1:
            with st.form("login_form"):
                username = st.text_input("Username or Email")
                password = st.text_input("Password", type="password")
                col1, col2 = st.columns(2)
                
                with col1:
                    login_button = st.form_submit_button("Login")
                with col2:
                    guest_button = st.form_submit_button("Continue as Guest")
                
                if login_button:
                    user = self.db_manager.authenticate_user(username, password)
                    if user:
                        st.session_state.current_user = user
                        st.session_state.authenticated = True
                        st.session_state.show_login = False
                        st.success(f"Welcome back, {user['username']}!")
                        st.rerun()
                    else:
                        st.error("Invalid username or password")
                
                if guest_button:
                    st.session_state.authenticated = True
                    st.session_state.show_login = False
                    st.rerun()
        
        with tab2:
            with st.form("signup_form"):
                new_username = st.text_input("Username")
                new_email = st.text_input("Email")
                new_password = st.text_input("Password", type="password")
                confirm_password = st.text_input("Confirm Password", type="password")
                
                if st.form_submit_button("Sign Up"):
                    if new_password != confirm_password:
                        st.error("Passwords do not match")
                    elif len(new_password) < 6:
                        st.error("Password must be at least 6 characters")
                    else:
                        user = self.db_manager.create_user(new_username, new_email, new_password)
                        if user:
                            st.session_state.current_user = user
                            st.session_state.authenticated = True
                            st.session_state.show_login = False
                            st.success("Account created successfully!")
                            st.rerun()
                        else:
                            st.error("Username or email already exists")
    
    def render_sidebar(self):
        """Render the sidebar with settings and information"""
        with st.sidebar:
            st.header("Space Mission Chatbot")
            
            # User info
            if st.session_state.current_user:
                st.subheader("Session Info")
                st.text(f"User: {st.session_state.current_user['username']}")
                st.text(f"Session ID: {st.session_state.session_id}")
                st.text(f"Queries: {st.session_state.query_count}")
            else:
                st.subheader("Session Info")
                st.text("Guest User")
                st.text(f"Session ID: {st.session_state.session_id}")
                st.text(f"Queries: {st.session_state.query_count}")
            
            # Settings
            st.subheader("Settings")
            st.session_state.show_sources = st.checkbox(
                "Show source documents",
                value=st.session_state.show_sources
            )
            
            # Actions
            st.subheader("Actions")
            
            if st.button("Clear Chat"):
                st.session_state.messages = []
                st.session_state.query_count = 0
                st.rerun()
            
            if st.button("Logout"):
                st.session_state.authenticated = False
                st.session_state.current_user = None
                st.session_state.show_login = True
                st.session_state.messages = []
                st.rerun()
            
            # Examples
            st.subheader("Example Questions")
            examples = [
                "What orbit regimes have been used for SAR imaging satellites?",
                "What are typical power requirements for Earth observation CubeSats?",
                "Which missions have used optical imaging payloads?",
                "What are common failure modes in small satellite missions?",
                "Compare antenna designs used in different SAR missions"
            ]
            
            for example in examples:
                if st.button(example, key=f"example_{hash(example)}"):
                    st.session_state.example_query = example
                    st.rerun()
            
            # Stats
            if st.checkbox("Show Engine Stats"):
                if st.session_state.query_engine:
                    stats = st.session_state.query_engine.get_engine_stats()
                    st.json(stats)
    
    def render_chat_interface(self):
        """Render the main chat interface"""
        # Load user history if logged in and messages are empty
        if st.session_state.current_user and len(st.session_state.messages) == 0:
            self._load_user_history()
        
        # Display chat messages
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.write(message["content"])
                
                # Show metadata if available
                if "metadata" in message and message["role"] == "assistant":
                    st.caption(f"Response time: {message['metadata']['response_time']:.2f}s")
        
        # Handle example query if set
        if hasattr(st.session_state, 'example_query'):
            query = st.session_state.example_query
            del st.session_state.example_query
        else:
            # Chat input
            query = st.chat_input(
                "Ask about space missions, orbits, payloads, etc..."
            )
        
        if query:
            # Add user message to chat
            st.session_state.messages.append({
                "role": "user",
                "content": query,
                "timestamp": datetime.now().isoformat()
            })
            
            # Save user message to DB if logged in
            self._save_message_to_db("user", query)
            
            # Display user message
            with st.chat_message("user"):
                st.write(query)
            
            # Process query with loading indicator
            with st.chat_message("assistant"):
                with st.spinner("Searching knowledge base..."):
                    result = self._process_query(query)
                
                # Display response
                response_text = result['response']
                
                # Add sources if enabled
                sources_data = []
                if st.session_state.show_sources and result.get('sources'):
                    response_text += self._format_sources(result['sources'])
                    sources_data = result['sources']
                
                st.write(response_text)
                
                # Show metadata
                query_time = result['metadata'].get('response_time', 0)
                st.caption(f"Response time: {query_time:.2f}s")
                
                # Add assistant message to chat
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response_text,
                    "timestamp": datetime.now().isoformat(),
                    "metadata": result['metadata'],
                    "sources": sources_data
                })
                
                # Save assistant message to DB if logged in
                self._save_message_to_db("assistant", response_text, sources_data)
    
    def run(self):
        """Run the Streamlit application"""
        st.set_page_config(
            page_title="Space Mission Chatbot - Authored by Emil Ares",
            page_icon="🚀",
            layout="wide"
        )
        
        # Apply custom CSS for better styling
        st.markdown("""
        <style>
        .stChatMessage {
            padding: 1rem;
            margin-bottom: 1rem;
            border-radius: 0.5rem;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Check if login page should be shown
        if st.session_state.show_login:
            self.render_login_page()
            return
        
        # Initialize query engine after authentication
        if not st.session_state.initialized and st.session_state.authenticated:
            try:
                # Get API key from secrets
                api_key = st.secrets.get("OPENAI_API_KEY")
                if not api_key:
                    st.error("OpenAI API key not found in Streamlit secrets!")
                    st.stop()
                
                # Set the API key in environment
                os.environ["OPENAI_API_KEY"] = api_key
                
                with st.spinner("Initializing Space Mission Assistant..."):
                    st.session_state.query_engine = SpaceMissionQueryEngine(
                        use_cloud=True,  # Use ChromaDB cloud
                        top_k=5, # Retrieve top 5 documents
                        similarity_threshold=0.35, # Optimal result
                        temperature=0.1, # Optimal result
                        llm_model="o3"
                    )
                    st.session_state.initialized = True
                    st.success("Successfully initialized!")
                    st.rerun()
            except Exception as e:
                st.error(f"Error initializing query engine: {e}")
                st.stop()
        
        # Render sidebar
        self.render_sidebar()
        
        # Main content area
        st.title("Space Mission Design Assistant - Authored by Emil Ares")
        st.markdown("Ask questions about historical space missions, orbits, payloads, and mission designs.")
        
        # Render chat interface
        self.render_chat_interface()


def main():
    """Main function to run the Streamlit chatbot"""
    # Create and run chatbot
    chatbot = StreamlitSpaceMissionChatbot()
    chatbot.run()


if __name__ == "__main__":
    main()