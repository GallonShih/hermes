from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc
import logging

from app.core.database import get_db
from app.core.settings import get_current_video_id
from app.models import LiveStream, StreamStats

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["stream-info"])


@router.get("/stream-info")
def get_stream_info(db: Session = Depends(get_db)):
    """Return current live stream metadata and latest stats.

    Public endpoint (no auth required).
    """
    video_id = get_current_video_id(db)
    if not video_id:
        return {"stream": None}

    live_stream = db.query(LiveStream).filter(
        LiveStream.video_id == video_id
    ).first()

    if not live_stream:
        return {"stream": None}

    # Get the latest stats snapshot for this video
    latest_stats = db.query(StreamStats).filter(
        StreamStats.live_stream_id == video_id
    ).order_by(desc(StreamStats.collected_at)).first()

    stats_data = None
    if latest_stats:
        stats_data = {
            "concurrent_viewers": latest_stats.concurrent_viewers,
            "view_count": latest_stats.view_count,
            "like_count": latest_stats.like_count,
            "collected_at": latest_stats.collected_at.isoformat() if latest_stats.collected_at else None,
        }

    return {
        "stream": {
            "video_id": live_stream.video_id,
            "title": live_stream.title,
            "channel_id": live_stream.channel_id,
            "channel_title": live_stream.channel_title,
            "thumbnail_url": live_stream.thumbnail_url,
            "tags": live_stream.tags,
            "category_id": live_stream.category_id,
            "published_at": live_stream.published_at.isoformat() if live_stream.published_at else None,
            "scheduled_start_time": live_stream.scheduled_start_time.isoformat() if live_stream.scheduled_start_time else None,
            "actual_start_time": live_stream.actual_start_time.isoformat() if live_stream.actual_start_time else None,
            "live_broadcast_content": live_stream.live_broadcast_content,
            "default_language": live_stream.default_language,
            "topic_categories": live_stream.topic_categories,
            "fetched_at": live_stream.fetched_at.isoformat() if live_stream.fetched_at else None,
            "stats": stats_data,
        }
    }
