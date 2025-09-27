"""
Chat message collection using chat-downloader
"""

import logging
import time
from chat_downloader import ChatDownloader
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from models import ChatMessage
from database import get_db_session

logger = logging.getLogger(__name__)


class ChatCollector:
    def __init__(self, live_stream_id):
        self.live_stream_id = live_stream_id
        self.chat_downloader = ChatDownloader()
        self.is_running = False

    def start_collection(self, url):
        """Start collecting chat messages from live stream"""
        logger.info(f"Starting chat collection for stream: {self.live_stream_id}")
        logger.info(f"URL: {url}")

        self.is_running = True

        try:
            chat = self.chat_downloader.get_chat(url)

            for message_data in chat:
                if not self.is_running:
                    logger.info("Chat collection stopped")
                    break

                try:
                    self._save_message(message_data)
                except Exception as e:
                    logger.error(f"Error saving message: {e}")
                    # Continue collecting even if one message fails

        except Exception as e:
            logger.error(f"Chat collection error: {e}")
            raise

    def _save_message(self, message_data):
        """Save a single chat message to database"""
        try:
            # Create ChatMessage instance
            chat_message = ChatMessage.from_chat_data(message_data, self.live_stream_id)

            # Extract values before session to avoid lazy loading issues
            message_id = chat_message.message_id
            author_name = chat_message.author_name

            # Save to database
            with get_db_session() as session:
                session.add(chat_message)

            logger.debug(f"Saved message: {message_id} from {author_name}")

        except IntegrityError as e:
            # Message already exists (duplicate message_id)
            logger.debug(f"Duplicate message ignored: {message_data.get('message_id')}")

        except SQLAlchemyError as e:
            logger.error(f"Database error saving message: {e}")
            raise

        except Exception as e:
            logger.error(f"Unexpected error saving message: {e}")
            logger.error(f"Message data: {message_data}")
            raise

    def stop_collection(self):
        """Stop chat collection"""
        logger.info("Stopping chat collection...")
        self.is_running = False

    def collect_with_retry(self, url, max_retries=3, backoff_seconds=5):
        """Collect chat with retry logic"""
        for attempt in range(max_retries):
            try:
                self.start_collection(url)
                return  # Success, exit retry loop

            except Exception as e:
                logger.error(f"Collection attempt {attempt + 1} failed: {e}")

                if attempt < max_retries - 1:
                    wait_time = backoff_seconds * (2 ** attempt)  # Exponential backoff
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"All {max_retries} collection attempts failed")
                    raise


def extract_video_id_from_url(url):
    """Extract YouTube video ID from URL"""
    import re

    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]+)',
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    raise ValueError(f"Could not extract video ID from URL: {url}")


if __name__ == "__main__":
    # Test the chat collector
    import sys
    from config import Config

    # Setup logging
    logging.basicConfig(level=logging.INFO)

    # Validate config
    Config.validate()

    if len(sys.argv) < 2:
        print("Usage: python chat_collector.py <youtube_url>")
        sys.exit(1)

    url = sys.argv[1]
    video_id = extract_video_id_from_url(url)

    collector = ChatCollector(video_id)

    try:
        collector.collect_with_retry(url, max_retries=Config.RETRY_MAX_ATTEMPTS, backoff_seconds=Config.RETRY_BACKOFF_SECONDS)
    except KeyboardInterrupt:
        logger.info("Chat collection stopped by user")
    except Exception as e:
        logger.error(f"Chat collection failed: {e}")
        sys.exit(1)