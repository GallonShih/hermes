"""
Configuration management for Hermes Worker
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    # Database
    DATABASE_URL = os.getenv('DATABASE_URL')

    # YouTube API
    YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
    YOUTUBE_URL = os.getenv('YOUTUBE_URL')

    # Worker settings
    POLL_INTERVAL = int(os.getenv('POLL_INTERVAL', 60))  # seconds
    ENABLE_BACKFILL = os.getenv('ENABLE_BACKFILL', 'false').lower() == 'true'

    # Retry settings
    RETRY_MAX_ATTEMPTS = int(os.getenv('RETRY_MAX_ATTEMPTS', 3))
    RETRY_BACKOFF_SECONDS = int(os.getenv('RETRY_BACKOFF_SECONDS', 5))

    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()

    @classmethod
    def validate(cls):
        """Validate required configuration"""
        required_vars = ['DATABASE_URL', 'YOUTUBE_API_KEY', 'YOUTUBE_URL']
        missing_vars = []

        for var in required_vars:
            if not getattr(cls, var):
                missing_vars.append(var)

        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

        return True

    @classmethod
    def print_config(cls):
        """Print current configuration (excluding sensitive data)"""
        print("=== Hermes Worker Configuration ===")
        print(f"DATABASE_URL: {'***' if cls.DATABASE_URL else 'NOT SET'}")
        print(f"YOUTUBE_API_KEY: {'***' if cls.YOUTUBE_API_KEY else 'NOT SET'}")
        print(f"YOUTUBE_URL: {cls.YOUTUBE_URL}")
        print(f"POLL_INTERVAL: {cls.POLL_INTERVAL}")
        print(f"ENABLE_BACKFILL: {cls.ENABLE_BACKFILL}")
        print(f"RETRY_MAX_ATTEMPTS: {cls.RETRY_MAX_ATTEMPTS}")
        print(f"RETRY_BACKOFF_SECONDS: {cls.RETRY_BACKOFF_SECONDS}")
        print(f"LOG_LEVEL: {cls.LOG_LEVEL}")
        print("=" * 35)