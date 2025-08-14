"""
Health check and system status API endpoints
"""

import os
import time
import logging
from typing import Dict, Any

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.models.schemas import HealthResponse
from app.services.session_manager import get_session_manager, SessionManager

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])

@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Check the health status of the API and its dependencies"
)
async def health_check(
    session_manager: SessionManager = Depends(get_session_manager)
):
    """
    Perform a health check of the service.
    
    Checks:
    - API server is running
    - Environment variables are configured
    - Session manager is operational
    - Returns active session count
    """
    try:
        # Check if required environment variables are set
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        api_key_status = "configured" if gemini_api_key else "missing"
        
        # Get session statistics
        active_sessions = session_manager.get_active_sessions_count()
        
        # Cleanup expired sessions as part of health check
        cleaned_sessions = session_manager.cleanup_expired_sessions()
        if cleaned_sessions > 0:
            logger.info(f"Health check cleaned up {cleaned_sessions} expired sessions")
        
        status = "healthy" if gemini_api_key else "degraded"
        
        return HealthResponse(
            status=status,
            timestamp=time.time(),
            active_sessions=active_sessions
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "timestamp": time.time(),
                "active_sessions": 0,
                "error": str(e)
            }
        )

@router.get(
    "/stats",
    summary="System Statistics",
    description="Get detailed system statistics and metrics"
)
async def get_system_stats(
    session_manager: SessionManager = Depends(get_session_manager)
):
    """
    Get detailed system statistics.
    
    Returns information about:
    - Active sessions
    - Session statistics
    - System health metrics
    """
    try:
        # Get session statistics
        session_stats = session_manager.get_session_stats()
        
        # Add system information
        stats = {
            "timestamp": time.time(),
            "sessions": session_stats,
            "environment": {
                "gemini_api_key_configured": bool(os.getenv("GEMINI_API_KEY")),
            }
        }
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting system stats: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Failed to get system statistics",
                "detail": str(e),
                "timestamp": time.time()
            }
        )