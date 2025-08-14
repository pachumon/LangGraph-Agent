"""
Chat API endpoints for AI agent interaction
"""

import time
import logging
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse

from app.models.schemas import (
    QueryRequest,
    QueryResponse,
    SessionHistoryResponse,
    ConversationMessage,
    ErrorResponse
)
from app.services.session_manager import get_session_manager, SessionManager
from app.services.agent_service import get_agent_service, AgentService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])

@router.post(
    "/{session_id}/query",
    response_model=QueryResponse,
    summary="Send Query to AI Agent",
    description="Send a query to the AI agent within a specific session context"
)
async def send_query(
    session_id: str,
    request: QueryRequest,
    session_manager: SessionManager = Depends(get_session_manager),
    agent_service: AgentService = Depends(get_agent_service)
):
    """
    Send a query to the AI agent within a session.
    
    The agent will maintain conversation context and history within
    the session, allowing for multi-turn conversations.
    """
    start_time = time.time()
    
    try:
        # Validate session exists
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=404,
                detail=f"Session {session_id} not found or expired"
            )
        
        logger.info(f"Processing query for session {session_id}: {request.query[:50]}...")
        
        # Process the query through the agent
        result = agent_service.process_query(session_id, request.query)
        
        processing_time = time.time() - start_time
        
        return QueryResponse(
            session_id=session_id,
            query=request.query,
            response=result["response"],
            message_count=result["message_count"],
            processing_time=processing_time,
            timestamp=time.time()
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        # This catches session validation errors from agent service
        logger.warning(f"Session validation error: {str(e)}")
        raise HTTPException(
            status_code=404,
            detail=str(e)
        )
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Error processing query for session {session_id} after {processing_time:.2f}s: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process query: {str(e)}"
        )

@router.get(
    "/{session_id}/history",
    response_model=SessionHistoryResponse,
    summary="Get Conversation History",
    description="Retrieve the complete conversation history for a session"
)
async def get_conversation_history(
    session_id: str,
    session_manager: SessionManager = Depends(get_session_manager),
    agent_service: AgentService = Depends(get_agent_service)
):
    """
    Get the complete conversation history for a session.
    
    Returns all messages (both user and assistant) in chronological order
    along with session metadata.
    """
    try:
        # Validate session exists
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=404,
                detail=f"Session {session_id} not found or expired"
            )
        
        # Get conversation history from agent service
        history_data = agent_service.get_session_history(session_id)
        
        # Convert history to response format
        conversation_messages = [
            ConversationMessage(
                role=msg["role"],
                content=msg["content"],
                timestamp=msg["timestamp"]
            )
            for msg in history_data.get("conversation_history", [])
        ]
        
        return SessionHistoryResponse(
            session_id=session_id,
            created_at=history_data["created_at"],
            last_activity=history_data["last_activity"],
            message_count=history_data["message_count"],
            conversation_history=conversation_messages
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Session validation error: {str(e)}")
        raise HTTPException(
            status_code=404,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting history for session {session_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get conversation history: {str(e)}"
        )