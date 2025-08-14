"""
Session management API endpoints
"""

import time
import logging
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse

from app.models.schemas import (
    CreateSessionRequest,
    SessionResponse,
    SessionEndResponse,
    ErrorResponse
)
from app.services.session_manager import get_session_manager, SessionManager
from app.services.agent_service import get_agent_service, AgentService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sessions", tags=["sessions"])

@router.post(
    "/",
    response_model=SessionResponse,
    summary="Create New Session",
    description="Create a new conversation session for interacting with the AI agent"
)
async def create_session(
    request: CreateSessionRequest,
    session_manager: SessionManager = Depends(get_session_manager)
):
    """
    Create a new conversation session.
    
    Returns a unique session ID that should be used for all subsequent
    interactions with the AI agent.
    """
    try:
        session_id = session_manager.create_session()
        session = session_manager.get_session(session_id)
        
        logger.info(f"Created new session: {session_id}")
        
        return SessionResponse(
            session_id=session_id,
            created_at=session.created_at,
            message_count=session.message_count
        )
        
    except Exception as e:
        logger.error(f"Error creating session: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create session: {str(e)}"
        )

@router.get(
    "/{session_id}",
    response_model=SessionResponse,
    summary="Get Session Info",
    description="Get information about an existing session"
)
async def get_session_info(
    session_id: str,
    session_manager: SessionManager = Depends(get_session_manager)
):
    """
    Get information about an existing session.
    
    Returns session metadata including creation time and message count.
    """
    try:
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=404,
                detail=f"Session {session_id} not found or expired"
            )
        
        return SessionResponse(
            session_id=session_id,
            created_at=session.created_at,
            message_count=session.message_count
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session info for {session_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get session info: {str(e)}"
        )

@router.delete(
    "/{session_id}",
    response_model=SessionEndResponse,
    summary="End Session",
    description="End an existing conversation session and cleanup resources"
)
async def end_session(
    session_id: str,
    session_manager: SessionManager = Depends(get_session_manager),
    agent_service: AgentService = Depends(get_agent_service)
):
    """
    End a conversation session.
    
    This will cleanup all session data and resources. The session ID
    will no longer be valid after this operation.
    """
    try:
        # Check if session exists before ending
        session_exists = session_manager.get_session(session_id) is not None
        
        if not session_exists:
            return SessionEndResponse(
                session_id=session_id,
                success=False,
                message=f"Session {session_id} not found or already expired"
            )
        
        # End the session and cleanup agent resources
        success = session_manager.end_session(session_id)
        agent_service.cleanup_session_graph(session_id)
        
        if success:
            logger.info(f"Ended session: {session_id}")
            return SessionEndResponse(
                session_id=session_id,
                success=True,
                message="Session ended successfully"
            )
        else:
            return SessionEndResponse(
                session_id=session_id,
                success=False,
                message="Failed to end session"
            )
            
    except Exception as e:
        logger.error(f"Error ending session {session_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to end session: {str(e)}"
        )