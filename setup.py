#!/usr/bin/env python3
import os
import subprocess
import sys

def install_requirements():
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed successfully!")
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies")
        sys.exit(1)

def setup_env_file():
    if not os.path.exists(".env"):
        api_key = input("Please enter your Gemini API key: ")
        with open(".env", "w") as f:
            f.write(f"GEMINI_API_KEY={api_key}\n")
        print("✅ .env file created successfully!")
    else:
        print("ℹ️  .env file already exists")

if __name__ == "__main__":
    print("Setting up LangGraph Gemini Agent...")
    print("=" * 40)
    
    install_requirements()
    setup_env_file()
    
    print("\n🚀 Setup complete! Run 'python langgraph_app.py' to start the agent.")