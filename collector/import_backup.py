"""
Manually import backup JSON files into the database.

Backup files are stored under /data/backup/<live_stream_id>/ directories.
The script infers live_stream_id from the directory name.

Usage:
  # Import all streams under the backup root
  python import_backup.py /data/backup

  # Import a specific stream's backups
  python import_backup.py /data/backup/dQw4w9WgXcQ

  # Import a single file (infers stream_id from parent directory)
  python import_backup.py /data/backup/dQw4w9WgXcQ/chat_buffer_backup_170780.json

  # Override stream_id explicitly
  python import_backup.py /data/backup --stream-id dQw4w9WgXcQ

  # Delete files after successful import
  python import_backup.py /data/backup --delete
"""

import argparse
import glob
import json
import logging
import os
import sys

from database import get_db_session, get_db_manager
from models import ChatMessage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def import_file(filepath, live_stream_id):
    """Import a single backup JSON file.

    Returns (saved, errors). On partial failure, rewrites the file
    with only the failed messages so the next run skips already-imported ones.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        messages = json.load(f)

    if not isinstance(messages, list) or not messages:
        return 0, 0

    saved_count = 0
    error_count = 0
    failed_messages = []

    with get_db_session() as session:
        for msg_data in messages:
            try:
                nested = session.begin_nested()
                chat_message = ChatMessage.from_chat_data(msg_data, live_stream_id)
                if chat_message:
                    session.merge(chat_message)
                    nested.commit()
                    saved_count += 1
                else:
                    nested.rollback()
            except Exception as e:
                nested.rollback()
                error_count += 1
                failed_messages.append(msg_data)
                logger.debug(f"Error importing message: {e}")

    # Rewrite file with only the failed messages for retry
    if failed_messages:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(failed_messages, f, ensure_ascii=False, default=str)
        logger.warning(f"  Rewrote {os.path.basename(filepath)} with {len(failed_messages)} failed message(s)")

    return saved_count, error_count


def collect_import_tasks(path, video_id=None):
    """Collect (stream_id, filepath) pairs from the given path.

    - Single file: requires video_id
    - Stream directory (contains .json files): uses dirname as stream_id
    - Backup root (contains stream subdirs): scans all subdirectories
    """
    tasks = []

    if os.path.isfile(path):
        if not video_id:
            # Try to infer from parent directory name
            parent = os.path.basename(os.path.dirname(path))
            if parent and parent != os.path.basename(path):
                video_id = parent
            else:
                logger.error("Cannot infer video_id from file path. Provide --video-id.")
                sys.exit(1)
        tasks.append((video_id, path))
        return tasks

    if not os.path.isdir(path):
        logger.error(f"Path not found: {path}")
        sys.exit(1)

    # Check if this directory directly contains backup files (stream directory)
    direct_files = sorted(glob.glob(os.path.join(path, "chat_buffer_backup_*.json")))
    if direct_files:
        stream_id = video_id or os.path.basename(path)
        for f in direct_files:
            tasks.append((stream_id, f))
        return tasks

    # Otherwise treat as backup root — scan subdirectories
    for stream_id in sorted(os.listdir(path)):
        stream_dir = os.path.join(path, stream_id)
        if not os.path.isdir(stream_dir):
            continue
        for filepath in sorted(glob.glob(os.path.join(stream_dir, "chat_buffer_backup_*.json"))):
            tasks.append((stream_id, filepath))

    return tasks


def main():
    parser = argparse.ArgumentParser(description="Import backup JSON files into the database")
    parser.add_argument("path", help="Backup root, stream directory, or single JSON file")
    parser.add_argument("--stream-id", help="Override live_stream_id (default: inferred from directory name)")
    parser.add_argument("--delete", action="store_true", help="Delete files after successful import")
    args = parser.parse_args()

    # Test DB connection
    if not get_db_manager().test_connection():
        logger.error("Database connection failed")
        sys.exit(1)

    tasks = collect_import_tasks(args.path, args.stream_id)

    if not tasks:
        logger.info("No backup files found")
        return

    logger.info(f"Found {len(tasks)} file(s) to import")

    total_saved = 0
    total_errors = 0

    for stream_id, filepath in tasks:
        try:
            saved, errors = import_file(filepath, stream_id)
            total_saved += saved
            total_errors += errors
            logger.info(f"  [{stream_id}] {os.path.basename(filepath)}: {saved} saved, {errors} errors")

            if args.delete and errors == 0:
                os.remove(filepath)
                logger.info(f"  Deleted {os.path.basename(filepath)}")

        except Exception as e:
            logger.error(f"  Failed to import {os.path.basename(filepath)}: {e}")

    logger.info(f"Done. Total: {total_saved} saved, {total_errors} errors")


if __name__ == "__main__":
    main()
