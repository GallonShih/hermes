import os
import logging
import datetime

import requests

from app.models import LiveStream

logger = logging.getLogger(__name__)

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3/videos"


def _pick_best_thumbnail(thumbnails: dict) -> str | None:
    """Select the highest resolution thumbnail available."""
    for key in ("maxres", "standard", "high", "medium", "default"):
        if key in thumbnails and thumbnails[key].get("url"):
            return thumbnails[key]["url"]
    return None


def _parse_datetime(value: str | None) -> datetime.datetime | None:
    if not value:
        return None
    return datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))


def fetch_video_metadata(video_id: str) -> dict | None:
    """Call YouTube Data API v3 to fetch video metadata.

    Returns the first item dict, or None if the request fails or no items found.
    Uses part=snippet,liveStreamingDetails,topicDetails (1 quota unit).
    """
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        logger.warning("YOUTUBE_API_KEY not set, cannot fetch video metadata")
        return None

    params = {
        "part": "snippet,liveStreamingDetails,topicDetails",
        "id": video_id,
        "key": api_key,
    }

    try:
        resp = requests.get(YOUTUBE_API_BASE, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        logger.warning(f"YouTube API request failed for video {video_id}: {e}")
        return None

    items = data.get("items", [])
    if not items:
        logger.warning(f"No items returned from YouTube API for video {video_id}")
        return None

    return items[0]


def build_live_stream_from_api(video_id: str, item: dict) -> LiveStream:
    """Convert a YouTube API item dict into a LiveStream model instance."""
    snippet = item.get("snippet", {})
    live_details = item.get("liveStreamingDetails", {})
    topic_details = item.get("topicDetails", {})

    return LiveStream(
        video_id=video_id,
        title=snippet.get("title"),
        channel_id=snippet.get("channelId"),
        channel_title=snippet.get("channelTitle"),
        description=snippet.get("description"),
        thumbnail_url=_pick_best_thumbnail(snippet.get("thumbnails", {})),
        tags=snippet.get("tags"),
        category_id=snippet.get("categoryId"),
        published_at=_parse_datetime(snippet.get("publishedAt")),
        scheduled_start_time=_parse_datetime(live_details.get("scheduledStartTime")),
        actual_start_time=_parse_datetime(live_details.get("actualStartTime")),
        live_broadcast_content=snippet.get("liveBroadcastContent"),
        default_language=snippet.get("defaultLanguage"),
        topic_categories=topic_details.get("topicCategories"),
        fetched_at=datetime.datetime.now(datetime.timezone.utc),
    )
