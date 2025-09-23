#!/usr/bin/env python3
"""
Database manager for user authentication and chat history
"""

import os
import json
from datetime import datetime
from typing import List, Dict, Optional, Any
import hashlib
import secrets
from sqlalchemy import create_engine, Column, String, Text, DateTime, Integer, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError
import bcrypt
import streamlit as st

Base = declarative_base()

class User(Base):
    """User model for authentication"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)
    is_active = Column(Boolean, default=True)

class ChatHistory(Base):
    """Chat history model"""
    __tablename__ = 'chat_history'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=True)  # Nullable for guest users
    session_id = Column(String(100), nullable=False, index=True)
    message_type = Column(String(20), nullable=False)  # 'user' or 'assistant'
    message = Column(Text, nullable=False)
    sources = Column(Text, nullable=True)  # JSON string of sources
    created_at = Column(DateTime, default=datetime.utcnow)


class DatabaseManager:
    """Manages database operations for users and chat history"""
    
    def __init__(self, database_url: Optional[str] = None):
        """Initialize database connection"""
        if database_url is None:
            # Use SQLite for local development
            database_url = os.getenv("DATABASE_URL", "sqlite:///./space_mission_chat.db")
        
        # Handle Streamlit Cloud PostgreSQL URL format
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
            
        self.engine = create_engine(database_url, echo=False)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
    
    def get_session(self) -> Session:
        """Get database session"""
        return self.SessionLocal()
    
    def create_user(self, username: str, email: str, password: str) -> Optional[Dict[str, Any]]:
        """Create a new user"""
        session = self.get_session()
        try:
            # Hash password
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            
            # Create user
            user = User(
                username=username,
                email=email,
                password_hash=password_hash.decode('utf-8')
            )
            
            session.add(user)
            session.commit()
            
            return {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'created_at': user.created_at
            }
        except IntegrityError:
            session.rollback()
            return None
        finally:
            session.close()
    
    def authenticate_user(self, username_or_email: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate a user"""
        session = self.get_session()
        try:
            # Find user by username or email
            user = session.query(User).filter(
                (User.username == username_or_email) | 
                (User.email == username_or_email)
            ).first()
            
            if user and user.is_active:
                # Check password
                if bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
                    # Update last login
                    user.last_login = datetime.utcnow()
                    session.commit()
                    
                    return {
                        'id': user.id,
                        'username': user.username,
                        'email': user.email,
                        'last_login': user.last_login
                    }
            return None
        finally:
            session.close()
    
    def save_chat_message(
        self, 
        session_id: str, 
        message_type: str, 
        message: str, 
        sources: Optional[List[Dict]] = None,
        user_id: Optional[int] = None
    ):
        """Save a chat message to history"""
        session = self.get_session()
        try:
            chat = ChatHistory(
                user_id=user_id,
                session_id=session_id,
                message_type=message_type,
                message=message,
                sources=json.dumps(sources) if sources else None
            )
            session.add(chat)
            session.commit()
        finally:
            session.close()
    
    def get_user_chat_history(
        self, 
        user_id: int, 
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get chat history for a user"""
        session = self.get_session()
        try:
            chats = session.query(ChatHistory).filter(
                ChatHistory.user_id == user_id
            ).order_by(
                ChatHistory.created_at.desc()
            ).limit(limit).offset(offset).all()
            
            history = []
            for chat in reversed(chats):  # Reverse to get chronological order
                history.append({
                    'id': chat.id,
                    'session_id': chat.session_id,
                    'message_type': chat.message_type,
                    'message': chat.message,
                    'sources': json.loads(chat.sources) if chat.sources else None,
                    'created_at': chat.created_at.isoformat()
                })
            
            return history
        finally:
            session.close()
    
    def get_session_chat_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Get chat history for a specific session"""
        session = self.get_session()
        try:
            chats = session.query(ChatHistory).filter(
                ChatHistory.session_id == session_id
            ).order_by(ChatHistory.created_at).all()
            
            history = []
            for chat in chats:
                history.append({
                    'id': chat.id,
                    'message_type': chat.message_type,
                    'message': chat.message,
                    'sources': json.loads(chat.sources) if chat.sources else None,
                    'created_at': chat.created_at.isoformat()
                })
            
            return history
        finally:
            session.close()
    
    def get_user_sessions(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all unique sessions for a user"""
        session = self.get_session()
        try:
            # Get unique sessions with their first and last message times
            result = session.execute("""
                SELECT 
                    session_id,
                    MIN(created_at) as first_message,
                    MAX(created_at) as last_message,
                    COUNT(*) as message_count
                FROM chat_history
                WHERE user_id = :user_id
                GROUP BY session_id
                ORDER BY MAX(created_at) DESC
            """, {'user_id': user_id})
            
            sessions = []
            for row in result:
                sessions.append({
                    'session_id': row[0],
                    'first_message': row[1],
                    'last_message': row[2],
                    'message_count': row[3]
                })
            
            return sessions
        finally:
            session.close()
    
    def delete_session_history(self, session_id: str, user_id: Optional[int] = None):
        """Delete all messages from a session"""
        session = self.get_session()
        try:
            query = session.query(ChatHistory).filter(
                ChatHistory.session_id == session_id
            )
            
            # Only allow users to delete their own sessions
            if user_id:
                query = query.filter(ChatHistory.user_id == user_id)
            
            query.delete()
            session.commit()
        finally:
            session.close()
    
    def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """Get statistics for a user"""
        session = self.get_session()
        try:
            total_messages = session.query(ChatHistory).filter(
                ChatHistory.user_id == user_id
            ).count()
            
            unique_sessions = session.execute("""
                SELECT COUNT(DISTINCT session_id)
                FROM chat_history
                WHERE user_id = :user_id
            """, {'user_id': user_id}).scalar()
            
            return {
                'total_messages': total_messages,
                'unique_sessions': unique_sessions
            }
        finally:
            session.close()

# Initialize database manager as a singleton
@st.cache_resource
def get_database_manager():
    """Get or create database manager instance"""
    return DatabaseManager()