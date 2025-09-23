#!/usr/bin/env python3
"""
Space Mission RAG Chatbot - Professional Streamlit Interface
Author: Emil Ares
"""

# SQLite compatibility fix for Streamlit Cloud
import sqlite_fix

import os
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
import hashlib
import time

import streamlit as st
from streamlit_lottie import st_lottie
from streamlit_extras.stylable_container import stylable_container
from streamlit_extras.add_vertical_space import add_vertical_space

from query_pipeline import SpaceMissionQueryEngine
from llama_index.core.response_synthesizers import ResponseMode
from database_manager import get_database_manager
from auth_manager import AuthManager


# Page configuration
st.set_page_config(
    page_title="Space Mission Design Assistant",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com/JordanEmil/Mission-Design',
        'Report a bug': 'https://github.com/JordanEmil/Mission-Design/issues',
        'About': 'Space Mission Design Assistant - Powered by RAG and LLMs'
    }
)


class SpaceMissionChatbot:
    """Professional Space Mission Chatbot with Authentication and History"""
    
    def __init__(self):
        """Initialize the chatbot"""
        self.db_manager = get_database_manager()
        self.auth_manager = AuthManager()
        self._init_session_state()
        self._load_custom_css()
    
    def _init_session_state(self):
        """Initialize session state variables"""
        if 'messages' not in st.session_state:
            st.session_state.messages = []
        if 'session_id' not in st.session_state:
            st.session_state.session_id = self._generate_session_id()
        if 'query_engine' not in st.session_state:
            st.session_state.query_engine = None
        if 'initialized' not in st.session_state:
            st.session_state.initialized = False
        if 'rate_limit_count' not in st.session_state:
            st.session_state.rate_limit_count = 0
        if 'rate_limit_reset' not in st.session_state:
            st.session_state.rate_limit_reset = time.time()
    
    def _generate_session_id(self) -> str:
        """Generate a unique session ID"""
        timestamp = datetime.now().isoformat()
        return hashlib.md5(timestamp.encode()).hexdigest()
    
    def _load_custom_css(self):
        """Load custom CSS for professional styling"""
        st.markdown("""
        <style>
        /* Main container styling */
        .main {
            background-color: #f8f9fa;
        }
        
        /* Chat message styling */
        .user-message {
            background-color: #e3f2fd;
            padding: 15px;
            border-radius: 15px;
            margin: 10px 0;
            max-width: 80%;
            float: right;
            clear: both;
        }
        
        .assistant-message {
            background-color: #ffffff;
            padding: 15px;
            border-radius: 15px;
            margin: 10px 0;
            max-width: 80%;
            border: 1px solid #e0e0e0;
        }
        
        .source-card {
            background-color: #f5f5f5;
            padding: 10px;
            border-radius: 8px;
            margin: 5px 0;
            border-left: 3px solid #1e88e5;
        }
        
        /* Button styling */
        .stButton > button {
            border-radius: 20px;
            transition: all 0.3s ease;
        }
        
        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 10px rgba(0,0,0,0.2);
        }
        
        /* Sidebar styling */
        .sidebar .sidebar-content {
            background-color: #f0f2f6;
        }
        
        /* Animation for loading */
        @keyframes pulse {
            0% { opacity: 0.6; }
            50% { opacity: 1; }
            100% { opacity: 0.6; }
        }
        
        .loading {
            animation: pulse 1.5s infinite;
        }
        </style>
        """, unsafe_allow_html=True)
    
    def _check_rate_limit(self) -> bool:
        """Check if user has exceeded rate limit"""
        current_time = time.time()
        
        # Reset counter every 60 seconds
        if current_time - st.session_state.rate_limit_reset > 60:
            st.session_state.rate_limit_count = 0
            st.session_state.rate_limit_reset = current_time
        
        # Allow 10 queries per minute for guests, 30 for registered users
        limit = 30 if self.auth_manager.is_registered_user() else 10
        
        if st.session_state.rate_limit_count >= limit:
            remaining = int(60 - (current_time - st.session_state.rate_limit_reset))
            st.error(f"⏱️ Rate limit exceeded. Please wait {remaining} seconds before asking another question.")
            return False
        
        return True
    
    def _init_query_engine(self):
        """Initialize the query engine with cloud configuration"""
        if not st.session_state.initialized:
            try:
                # Get API key from Streamlit secrets
                api_key = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
                if not api_key:
                    st.error("OpenAI API key not configured. Please contact the administrator.")
                    return False
                
                os.environ["OPENAI_API_KEY"] = api_key
                
                # Initialize query engine
                with st.spinner("🚀 Initializing Space Mission Assistant..."):
                    st.session_state.query_engine = SpaceMissionQueryEngine(
                        use_cloud=True,
                        top_k=5,
                        similarity_threshold=0.35,
                        temperature=0.1,
                        llm_model="o3"
                    )
                    st.session_state.initialized = True
                return True
                
            except Exception as e:
                st.error(f"Error initializing query engine: {str(e)}")
                return False
    
    def _save_message(self, message_type: str, message: str, sources: Optional[List[Dict]] = None):
        """Save message to database"""
        try:
            user_id = self.auth_manager.get_current_user_id()
            self.db_manager.save_chat_message(
                session_id=st.session_state.session_id,
                message_type=message_type,
                message=message,
                sources=sources,
                user_id=user_id
            )
        except Exception as e:
            # Don't interrupt chat if saving fails
            print(f"Error saving message: {e}")
    
    def _load_chat_history(self):
        """Load chat history for the current user"""
        if self.auth_manager.is_registered_user():
            # Load recent chat history for registered users
            history = self.db_manager.get_user_chat_history(
                user_id=self.auth_manager.get_current_user_id(),
                limit=50
            )
            
            # Convert to message format
            messages = []
            for chat in history:
                msg = {
                    "role": "user" if chat['message_type'] == 'user' else "assistant",
                    "content": chat['message']
                }
                if chat['sources']:
                    msg['sources'] = chat['sources']
                messages.append(msg)
            
            if messages:
                st.session_state.messages = messages[-20:]  # Keep last 20 messages
    
    def _process_query(self, query: str) -> Dict[str, Any]:
        """Process a user query"""
        if not self._check_rate_limit():
            return None
        
        try:
            st.session_state.rate_limit_count += 1
            
            result = st.session_state.query_engine.query(
                query,
                response_mode=ResponseMode.COMPACT,
                return_sources=True,
                verbose=False
            )
            
            # Save messages to database
            self._save_message("user", query)
            self._save_message("assistant", result['response'], result.get('sources'))
            
            return result
            
        except Exception as e:
            error_msg = f"Error processing query: {str(e)}"
            st.error(error_msg)
            return {
                'response': "I apologize, but I encountered an error processing your request. Please try again.",
                'sources': [],
                'metadata': {'response_time': 0}
            }
    
    def _render_message(self, message: Dict[str, Any]):
        """Render a chat message with professional styling"""
        if message["role"] == "user":
            st.markdown(f"""
            <div class="user-message">
                <strong>You:</strong><br>
                {message["content"]}
            </div>
            """, unsafe_allow_html=True)
        else:
            # Assistant message
            st.markdown(f"""
            <div class="assistant-message">
                <strong>🤖 Assistant:</strong><br>
                {message["content"]}
            </div>
            """, unsafe_allow_html=True)
            
            # Always show sources if available
            if message.get("sources"):
                self._render_sources(message["sources"])
    
    def _render_sources(self, sources: List[Dict]):
        """Render source documents"""
        if not sources:
            return
        
        st.markdown("**📚 Sources:**")
        
        # Deduplicate sources by mission
        seen_missions = set()
        unique_sources = []
        
        for source in sources:
            mission = source.get('metadata', {}).get('title', 'Unknown')
            if mission not in seen_missions:
                seen_missions.add(mission)
                unique_sources.append(source)
        
        # Display sources in an expandable section
        with st.expander(f"View {len(unique_sources)} source documents", expanded=False):
            for i, source in enumerate(unique_sources[:3], 1):
                metadata = source.get('metadata', {})
                st.markdown(f"""
                <div class="source-card">
                    <strong>Source {i}:</strong> {metadata.get('title', 'Unknown')}<br>
                    <small>Score: {source.get('score', 0):.3f}</small><br>
                    <details>
                        <summary>View excerpt</summary>
                        {source.get('text', '')[:300]}...
                    </details>
                </div>
                """, unsafe_allow_html=True)
    
    def render_sidebar(self):
        """Render the sidebar with chat history and options"""
        with st.sidebar:
            # Logo and title
            st.markdown("# 🚀 Space Mission Assistant")
            st.markdown("*Powered by RAG & AI*")
            
            # User menu
            self.auth_manager.render_user_menu()
            
            st.divider()
            
            # Chat history for registered users
            if self.auth_manager.is_registered_user():
                st.subheader("📜 Chat History")
                
                # Get user's sessions
                sessions = self.db_manager.get_user_sessions(
                    self.auth_manager.get_current_user_id()
                )
                
                if sessions:
                    for session in sessions[:10]:  # Show last 10 sessions
                        session_date = session['last_message'].strftime("%m/%d %H:%M")
                        if st.button(
                            f"💬 {session_date} ({session['message_count']} msgs)",
                            key=f"session_{session['session_id']}"
                        ):
                            # Load this session's history
                            history = self.db_manager.get_session_chat_history(
                                session['session_id']
                            )
                            # Convert to message format
                            messages = []
                            for chat in history:
                                msg = {
                                    "role": "user" if chat['message_type'] == 'user' else "assistant",
                                    "content": chat['message']
                                }
                                if chat['sources']:
                                    msg['sources'] = chat['sources']
                                messages.append(msg)
                            st.session_state.messages = messages
                            st.rerun()
                else:
                    st.info("No chat history yet")
            
            st.divider()
            
            # Actions
            st.subheader("⚡ Actions")
            
            if st.button("🆕 New Chat", use_container_width=True):
                st.session_state.messages = []
                st.session_state.session_id = self._generate_session_id()
                st.rerun()
            
            if st.session_state.messages and self.auth_manager.is_registered_user():
                if st.button("📥 Export Chat", use_container_width=True):
                    self._export_chat()
            
            st.divider()
            
            # Example questions
            st.subheader("💡 Example Questions")
            examples = [
                "What orbit regimes are used for SAR satellites?",
                "Compare power systems in CubeSats vs traditional satellites",
                "What are the typical failure modes in small satellites?",
                "How do optical and SAR imaging satellites differ?"
            ]
            
            for example in examples:
                if st.button(example, key=f"ex_{hash(example)}"):
                    st.session_state.example_query = example
                    st.rerun()
            
            # Footer
            st.divider()
            st.markdown("""
            <small>
            Created by Emil Ares<br>
            <a href="https://github.com/JordanEmil/Mission-Design">GitHub</a> |
            <a href="https://github.com/JordanEmil/Mission-Design/issues">Report Issue</a>
            </small>
            """, unsafe_allow_html=True)
    
    def _export_chat(self):
        """Export current chat as JSON"""
        chat_data = {
            'session_id': st.session_state.session_id,
            'exported_at': datetime.now().isoformat(),
            'messages': st.session_state.messages
        }
        
        json_str = json.dumps(chat_data, indent=2)
        
        st.download_button(
            label="Download Chat History",
            data=json_str,
            file_name=f"chat_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )
    
    def render_chat_interface(self):
        """Render the main chat interface"""
        # Initialize query engine if needed
        if not st.session_state.initialized:
            if not self._init_query_engine():
                return
        
        # Chat container
        chat_container = st.container()
        
        with chat_container:
            # Display chat messages
            for message in st.session_state.messages:
                self._render_message(message)
        
        # Handle example query
        if hasattr(st.session_state, 'example_query'):
            query = st.session_state.example_query
            del st.session_state.example_query
            
            # Add to messages
            st.session_state.messages.append({"role": "user", "content": query})
            
            # Process query
            with st.spinner("🤔 Thinking..."):
                result = self._process_query(query)
                
            if result:
                # Add response to messages
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": result['response'],
                    "sources": result.get('sources', [])
                })
                st.rerun()
        
        # Chat input
        if prompt := st.chat_input("Ask about space missions..."):
            # Add user message
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            # Display user message immediately
            self._render_message({"role": "user", "content": prompt})
            
            # Process with loading animation
            with st.spinner("🔍 Searching knowledge base..."):
                result = self._process_query(prompt)
            
            if result:
                # Add assistant response
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": result['response'],
                    "sources": result.get('sources', [])
                })
                st.rerun()
    
    def run(self):
        """Main application entry point"""
        # Check authentication
        if not self.auth_manager.is_authenticated():
            self.auth_manager.render_auth_page()
        else:
            # Main app layout
            col1, col2 = st.columns([1, 3])
            
            with col1:
                self.render_sidebar()
            
            with col2:
                # Header
                st.title("🚀 Space Mission Design Assistant")
                st.markdown("Ask questions about space missions, satellite design, and orbital mechanics")
                
                # Load chat history on first load
                if len(st.session_state.messages) == 0 and self.auth_manager.is_registered_user():
                    self._load_chat_history()
                
                # Chat interface
                self.render_chat_interface()


def main():
    """Main function"""
    chatbot = SpaceMissionChatbot()
    chatbot.run()


if __name__ == "__main__":
    main()