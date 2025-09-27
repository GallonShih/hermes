"""
Main application for Hermes Worker
Coordinates chat collection and stats polling
"""

import logging
import threading
import signal
import sys
import time
from config import Config
from database import get_db_manager
from chat_collector import ChatCollector, extract_video_id_from_url
from youtube_api import StatsCollector

# Setup logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class HermesWorker:
    def __init__(self, youtube_url=None):
        # Use URL from config if not provided
        self.youtube_url = youtube_url or Config.YOUTUBE_URL
        if not self.youtube_url:
            raise ValueError("YouTube URL must be provided either as parameter or in YOUTUBE_URL environment variable")

        self.video_id = extract_video_id_from_url(self.youtube_url)

        # Initialize components
        self.chat_collector = ChatCollector(self.video_id)
        self.stats_collector = StatsCollector()

        # Threading
        self.chat_thread = None
        self.stats_thread = None
        self.is_running = False

    def start(self):
        """Start the Hermes worker"""
        logger.info("=== Starting Hermes Worker ===")
        Config.print_config()

        # Validate configuration
        try:
            Config.validate()
        except ValueError as e:
            logger.error(f"Configuration error: {e}")
            sys.exit(1)

        # Test database connection
        db_manager = get_db_manager()
        if not db_manager.test_connection():
            logger.error("Database connection failed")
            sys.exit(1)

        # Set running flag
        self.is_running = True

        # Start chat collection in separate thread
        self.chat_thread = threading.Thread(
            target=self._run_chat_collection,
            name="ChatCollector"
        )
        self.chat_thread.daemon = True
        self.chat_thread.start()

        # Start stats polling in separate thread
        self.stats_thread = threading.Thread(
            target=self._run_stats_polling,
            name="StatsCollector"
        )
        self.stats_thread.daemon = True
        self.stats_thread.start()

        logger.info(f"Worker started for video: {self.video_id}")
        logger.info("Press Ctrl+C to stop...")

        # Keep main thread alive
        try:
            while self.is_running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        """Stop the Hermes worker"""
        logger.info("=== Stopping Hermes Worker ===")

        self.is_running = False

        # Stop collectors
        if self.chat_collector:
            self.chat_collector.stop_collection()

        if self.stats_collector:
            self.stats_collector.stop_polling()

        # Wait for threads to finish
        if self.chat_thread and self.chat_thread.is_alive():
            logger.info("Waiting for chat collection to stop...")
            self.chat_thread.join(timeout=10)

        if self.stats_thread and self.stats_thread.is_alive():
            logger.info("Waiting for stats polling to stop...")
            self.stats_thread.join(timeout=10)

        # Close database connections
        db_manager = get_db_manager()
        db_manager.close()

        logger.info("Worker stopped successfully")

    def _run_chat_collection(self):
        """Run chat collection with retry logic"""
        while self.is_running:
            try:
                logger.info("Starting chat collection...")
                self.chat_collector.collect_with_retry(
                    self.youtube_url,
                    max_retries=Config.RETRY_MAX_ATTEMPTS,
                    backoff_seconds=Config.RETRY_BACKOFF_SECONDS
                )

                # If we get here, collection ended normally
                if self.is_running:
                    logger.info("Chat collection ended, restarting in 30 seconds...")
                    time.sleep(30)

            except Exception as e:
                logger.error(f"Chat collection failed: {e}")
                if self.is_running:
                    logger.info("Restarting chat collection in 60 seconds...")
                    time.sleep(60)

    def _run_stats_polling(self):
        """Run stats polling with retry logic"""
        while self.is_running:
            try:
                logger.info("Starting stats polling...")
                self.stats_collector.start_polling(
                    self.video_id,
                    interval_seconds=Config.POLL_INTERVAL
                )

            except Exception as e:
                logger.error(f"Stats polling failed: {e}")
                if self.is_running:
                    logger.info("Restarting stats polling in 60 seconds...")
                    time.sleep(60)


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, shutting down...")
    sys.exit(0)


def main():
    """Main entry point"""
    youtube_url = None

    # Check if URL provided as command line argument
    if len(sys.argv) >= 2:
        youtube_url = sys.argv[1]

    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Create and start worker (will use URL from env if not provided)
    worker = HermesWorker(youtube_url)

    try:
        worker.start()
    except Exception as e:
        logger.error(f"Worker failed: {e}")
        sys.exit(1)
    finally:
        worker.stop()


if __name__ == "__main__":
    main()