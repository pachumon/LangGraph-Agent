"""
Main FastAPI application module

This module initializes and configures the FastAPI application with all
necessary middleware, routers, and lifecycle management.
"""

import logging
import time
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

# Import configuration
from app.core.config import get_settings, validate_settings

# Import API routers
from app.api.v1.sessions import router as sessions_router
from app.api.v1.chat import router as chat_router
from app.api.v1.health import router as health_router

# Import services for initialization
from app.services.session_manager import get_session_manager
from app.services.agent_service import get_agent_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager - handles startup and shutdown
    """
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    
    try:
        # Validate configuration
        validate_settings()
        logger.info("Configuration validated successfully")
        
        # Initialize services
        session_manager = get_session_manager()
        agent_service = get_agent_service()
        
        logger.info("Services initialized successfully")
        logger.info(f"Session timeout: {settings.session_timeout_minutes} minutes")
        logger.info(f"Using Gemini model: {settings.gemini_model}")
        
    except Exception as e:
        logger.error(f"Failed to initialize application: {e}")
        raise
    
    logger.info("Application startup complete")
    yield
    
    # Shutdown: Cleanup resources
    logger.info("Shutting down application...")
    try:
        # Cleanup expired sessions
        session_manager = get_session_manager()
        cleaned = session_manager.cleanup_expired_sessions()
        if cleaned > 0:
            logger.info(f"Cleaned up {cleaned} expired sessions during shutdown")
    except Exception as e:
        logger.error(f"Error during shutdown cleanup: {e}")
    
    logger.info("Application shutdown complete")

# Initialize FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=settings.app_description,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=settings.cors_methods,
    allow_headers=settings.cors_headers,
)

# Add request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests"""
    start_time = time.time()
    
    # Log request
    logger.info(f"{request.method} {request.url.path} - {request.client.host}")
    
    # Process request
    response = await call_next(request)
    
    # Log response
    process_time = time.time() - start_time
    logger.info(f"{request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s")
    
    return response

# Include API routers
app.include_router(health_router, prefix="/api/v1")
app.include_router(sessions_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")

# Global exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors"""
    logger.warning(f"Validation error for {request.url.path}: {exc}")
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation Error",
            "detail": exc.errors(),
            "timestamp": time.time()
        }
    )

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions"""
    logger.warning(f"HTTP {exc.status_code} for {request.url.path}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": f"HTTP {exc.status_code}",
            "detail": exc.detail,
            "timestamp": time.time()
        }
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all other exceptions"""
    logger.error(f"Unhandled exception for {request.url.path}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "detail": "An unexpected error occurred",
            "timestamp": time.time()
        }
    )

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "description": settings.app_description,
        "docs_url": "/docs",
        "health_url": "/api/v1/health"
    }

# Run the application (for development)
if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level
    )