#!/usr/bin/env python3
"""
TCS Competitive Intelligence System
Main entry point for running the application
"""

import os
import sys
import logging
import asyncio
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import uvicorn
from backend.api.main import app
from config.settings import settings

def setup_logging():
    """
    Configure logging for the application.
    """
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('logs/app.log') if Path('logs').exists() else logging.NullHandler()
        ]
    )

def check_environment():
    """
    Check if required environment variables are set.
    """
    required_vars = ['OPENAI_API_KEY']
    missing_vars = []

    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\n📝 Please create a .env file based on .env.example")
        print("   and set the required variables.")
        return False

    return True

def print_startup_info():
    """
    Print startup information.
    """
    print("🚀 TCS Competitive Intelligence System")
    print("=" * 50)
    print(f"📊 Environment: {settings.environment}")
    print(f"🌐 API Server: http://{settings.api_host}:{settings.api_port}")
    print(f"📱 Frontend: Open frontend/index.html in your browser")
    print(f"📚 API Docs: http://{settings.api_host}:{settings.api_port}/docs")
    print(f"🎯 Target Competitors: {len(settings.tcs_competitors)} companies")
    print("=" * 50)

def main():
    """
    Main entry point.
    """
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)

    # Check environment
    if not check_environment():
        sys.exit(1)

    # Print startup info
    print_startup_info()

    try:
        # Create logs directory if it doesn't exist
        logs_dir = Path('logs')
        logs_dir.mkdir(exist_ok=True)

        # Create data directory if it doesn't exist
        data_dir = Path('data')
        data_dir.mkdir(exist_ok=True)

        logger.info("Starting TCS Competitive Intelligence API server")

        # Run the server
        if settings.environment == "development":
            uvicorn.run(
                "backend.api.main:app",
                host=settings.api_host,
                port=settings.api_port,
                reload=True,
                log_level=settings.log_level.lower(),
                access_log=True
            )
        else:
            uvicorn.run(
                app,
                host=settings.api_host,
                port=settings.api_port,
                reload=False,
                log_level=settings.log_level.lower(),
                access_log=True
            )

    except KeyboardInterrupt:
        logger.info("Shutting down server...")
        print("\n👋 Server stopped")
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        print(f"❌ Failed to start server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()