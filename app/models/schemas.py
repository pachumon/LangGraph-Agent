"""
Pydantic models for request/response validation and API documentation
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import time

# Request Models
class CreateSessionRequest(BaseModel):
    """Request model for creating a new conversation session"""
    pass  # No parameters needed for session creation

class QueryRequest(BaseModel):
    """Request model for sending queries to an existing session"""
    query: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="The user's question or prompt for the AI agent",
        example="What is the meaning of life?"
    )

# Response Models
class SessionResponse(BaseModel):
    """Response model for session creation and information"""
    session_id: str = Field(description="Unique session identifier")
    created_at: float = Field(description="Unix timestamp when session was created")
    message_count: int = Field(description="Number of messages in this session", default=0)

class ConversationMessage(BaseModel):
    """Model representing a single message in conversation history"""
    role: str = Field(description="Message role: 'user' or 'assistant'")
    content: str = Field(description="Message content")
    timestamp: float = Field(description="Unix timestamp when message was created")

class QueryResponse(BaseModel):
    """Response model for query processing"""
    session_id: str = Field(description="Session identifier")
    query: str = Field(description="The original user query")
    response: str = Field(description="The AI agent's response")
    message_count: int = Field(description="Total messages in this session")
    processing_time: float = Field(description="Time taken to process the query in seconds")
    timestamp: float = Field(description="Unix timestamp when response was generated")

class SessionHistoryResponse(BaseModel):
    """Response model for session conversation history"""
    session_id: str = Field(description="Session identifier")
    created_at: float = Field(description="Unix timestamp when session was created")
    last_activity: float = Field(description="Unix timestamp of last activity")
    message_count: int = Field(description="Total number of messages")
    conversation_history: List[ConversationMessage] = Field(
        description="Complete conversation history"
    )

class HealthResponse(BaseModel):
    """Health check response model"""
    status: str = Field(description="Service health status")
    timestamp: float = Field(description="Current timestamp")
    active_sessions: int = Field(description="Number of active sessions", default=0)

class ErrorResponse(BaseModel):
    """Error response model for consistent error handling"""
    error: str = Field(description="Error message")
    detail: Optional[str] = Field(description="Additional error details")
    timestamp: float = Field(description="Timestamp when error occurred", default_factory=time.time)

class SessionEndResponse(BaseModel):
    """Response model for session termination"""
    session_id: str = Field(description="Session identifier that was ended")
    success: bool = Field(description="Whether session was successfully ended")
    message: str = Field(description="Confirmation message")

# Internal Models (not exposed in API)
class SessionState(BaseModel):
    """Internal model for session state management"""
    session_id: str
    current_query: str = ""
    response: str = ""
    conversation_history: List[Dict[str, Any]] = []
    created_at: float
    last_activity: float