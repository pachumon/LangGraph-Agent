#!/usr/bin/env python3
"""
Development server runner for the LangGraph Gemini Agent API
"""

import os
import sys

def main():
    """Run the FastAPI development server"""
    print("Starting LangGraph Gemini Agent API...")
    print("=" * 50)
    
    # Check if virtual environment is activated
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("⚠️  Warning: Virtual environment not detected")
        print("   Recommended: Activate your virtual environment first")
        print("   Windows: .venv\\Scripts\\activate")
        print("   Linux/Mac: source .venv/bin/activate")
        print()
    
    # Check if .env file exists
    if not os.path.exists(".env"):
        print("⚠️  Warning: .env file not found")
        print("   Create a .env file with your GEMINI_API_KEY")
        print("   Example: GEMINI_API_KEY=your_api_key_here")
        print()
    
    try:
        import uvicorn
        from app.main import app
        
        print("🚀 Starting server...")
        print("   API Documentation: http://localhost:8000/docs")
        print("   Health Check: http://localhost:8000/api/v1/health")
        print("   Press Ctrl+C to stop")
        print()
        
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
        
    except ImportError as e:
        print(f"❌ Error: Required dependencies not installed")
        print(f"   {str(e)}")
        print("   Run: pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error starting server: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()