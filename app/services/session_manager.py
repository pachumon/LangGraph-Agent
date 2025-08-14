"""
Session management service for handling user conversation sessions
"""

import uuid
import time
import logging
from typing import Dict, Optional, List, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class SessionInfo:
    """Information about an active session"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.created_at = time.time()
        self.last_activity = time.time()
        self.message_count = 0
    
    def update_activity(self):
        """Update the last activity timestamp"""
        self.last_activity = time.time()
    
    def is_expired(self, timeout_minutes: int = 30) -> bool:
        """Check if session has expired based on inactivity"""
        timeout_seconds = timeout_minutes * 60
        return (time.time() - self.last_activity) > timeout_seconds

class SessionManager:
    """
    Manages user conversation sessions with automatic cleanup
    """
    
    def __init__(self, session_timeout_minutes: int = 30):
        self.sessions: Dict[str, SessionInfo] = {}
        self.session_timeout = session_timeout_minutes
        logger.info(f"SessionManager initialized with {session_timeout_minutes}min timeout")
    
    def create_session(self) -> str:
        """
        Create a new session and return session ID
        
        Returns:
            str: Unique session identifier
        """
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = SessionInfo(session_id)
        logger.info(f"Created new session: {session_id}")
        return session_id
    
    def get_session(self, session_id: str) -> Optional[SessionInfo]:
        """
        Get session info, return None if not found or expired
        
        Args:
            session_id: Session identifier to lookup
            
        Returns:
            SessionInfo if found and valid, None otherwise
        """
        if session_id not in self.sessions:
            logger.warning(f"Session not found: {session_id}")
            return None
        
        session = self.sessions[session_id]
        if session.is_expired(self.session_timeout):
            logger.info(f"Session expired: {session_id}")
            self.end_session(session_id)
            return None
        
        session.update_activity()
        return session
    
    def end_session(self, session_id: str) -> bool:
        """
        End a session and cleanup resources
        
        Args:
            session_id: Session identifier to end
            
        Returns:
            bool: True if session was ended, False if not found
        """
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"Ended session: {session_id}")
            return True
        
        logger.warning(f"Attempted to end non-existent session: {session_id}")
        return False
    
    def get_active_sessions_count(self) -> int:
        """
        Get the number of currently active sessions
        
        Returns:
            int: Number of active sessions
        """
        return len(self.sessions)
    
    def cleanup_expired_sessions(self) -> int:
        """
        Remove all expired sessions
        
        Returns:
            int: Number of sessions that were cleaned up
        """
        expired_sessions = [
            sid for sid, session in self.sessions.items()
            if session.is_expired(self.session_timeout)
        ]
        
        for session_id in expired_sessions:
            self.end_session(session_id)
        
        if expired_sessions:
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
        
        return len(expired_sessions)
    
    def get_session_stats(self) -> Dict[str, Any]:
        """
        Get statistics about current sessions
        
        Returns:
            Dict containing session statistics
        """
        total_sessions = len(self.sessions)
        if total_sessions == 0:
            return {
                "total_sessions": 0,
                "average_messages": 0,
                "oldest_session_age": 0,
                "newest_session_age": 0
            }
        
        current_time = time.time()
        message_counts = [session.message_count for session in self.sessions.values()]
        session_ages = [current_time - session.created_at for session in self.sessions.values()]
        
        return {
            "total_sessions": total_sessions,
            "average_messages": sum(message_counts) / len(message_counts),
            "oldest_session_age": max(session_ages),
            "newest_session_age": min(session_ages)
        }

# Global session manager instance
session_manager = SessionManager()

def get_session_manager() -> SessionManager:
    """
    Dependency injection function for FastAPI
    
    Returns:
        SessionManager: The global session manager instance
    """
    return session_manager