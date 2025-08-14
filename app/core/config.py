"""
Application configuration settings
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # API Configuration
    app_name: str = "LangGraph Gemini Agent API"
    app_version: str = "1.0.0"
    app_description: str = "RESTful API for session-based AI conversations using LangGraph and Gemini"
    
    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True
    reload: bool = True
    log_level: str = "info"
    
    # Session Configuration
    session_timeout_minutes: int = 30
    
    # AI Model Configuration
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-2.0-flash-exp"
    gemini_temperature: float = 0.7
    
    # CORS Configuration
    cors_origins: list = ["*"]  # Configure properly for production
    cors_methods: list = ["GET", "POST", "PUT", "DELETE"]
    cors_headers: list = ["*"]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# Global settings instance
settings = Settings()

# Validate required settings
def validate_settings():
    """Validate that all required settings are configured"""
    if not settings.gemini_api_key:
        raise ValueError("GEMINI_API_KEY environment variable is required")

def get_settings() -> Settings:
    """Get the global settings instance"""
    return settings