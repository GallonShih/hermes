from datetime import datetime, timezone
from unittest.mock import patch

from app.models import LiveStream, StreamStats, SystemSetting


class TestGetStreamInfo:
    """Tests for GET /api/stream-info endpoint."""

    def test_returns_null_when_no_youtube_url(self, client):
        """Should return null stream when no youtube_url setting exists."""
        response = client.get("/api/stream-info")
        assert response.status_code == 200
        data = response.json()
        assert data["stream"] is None

    def test_returns_null_when_no_live_stream_record(self, client, db):
        """Should return null stream when video_id exists but no LiveStream record."""
        db.add(SystemSetting(
            key="youtube_url",
            value="https://www.youtube.com/watch?v=NoRecord_11"
        ))
        db.flush()

        response = client.get("/api/stream-info")
        assert response.status_code == 200
        data = response.json()
        assert data["stream"] is None

    def test_returns_stream_without_stats(self, client, db):
        """Should return stream metadata with null stats when no StreamStats exist."""
        video_id = "TestVid_111"  # exactly 11 chars
        db.add(SystemSetting(
            key="youtube_url",
            value=f"https://www.youtube.com/watch?v={video_id}"
        ))
        db.add(LiveStream(
            video_id=video_id,
            title="Test Live Stream",
            channel_id="UC_test",
            channel_title="Test Channel",
            thumbnail_url="http://img/thumb.jpg",
            live_broadcast_content="live",
            published_at=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
        ))
        db.flush()

        response = client.get("/api/stream-info")
        assert response.status_code == 200
        data = response.json()

        stream = data["stream"]
        assert stream is not None
        assert stream["video_id"] == video_id
        assert stream["title"] == "Test Live Stream"
        assert stream["channel_id"] == "UC_test"
        assert stream["channel_title"] == "Test Channel"
        assert stream["thumbnail_url"] == "http://img/thumb.jpg"
        assert stream["live_broadcast_content"] == "live"
        assert stream["stats"] is None

    def test_returns_stream_with_stats(self, client, db):
        """Should return stream metadata with latest stats."""
        video_id = "WithStats_1"  # exactly 11 chars
        db.add(SystemSetting(
            key="youtube_url",
            value=f"https://www.youtube.com/watch?v={video_id}"
        ))
        db.add(LiveStream(
            video_id=video_id,
            title="Stream With Stats",
            channel_title="Stats Channel",
            live_broadcast_content="live",
        ))
        # Add two stats snapshots — endpoint should return the latest
        db.add(StreamStats(
            live_stream_id=video_id,
            concurrent_viewers=500,
            view_count=10000,
            like_count=200,
            collected_at=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
        ))
        db.add(StreamStats(
            live_stream_id=video_id,
            concurrent_viewers=800,
            view_count=15000,
            like_count=350,
            collected_at=datetime(2024, 1, 15, 10, 5, 0, tzinfo=timezone.utc),
        ))
        db.flush()

        response = client.get("/api/stream-info")
        assert response.status_code == 200
        data = response.json()

        stream = data["stream"]
        assert stream is not None
        assert stream["video_id"] == video_id

        stats = stream["stats"]
        assert stats is not None
        # Should be the latest snapshot (10:05)
        assert stats["concurrent_viewers"] == 800
        assert stats["view_count"] == 15000
        assert stats["like_count"] == 350
        assert stats["collected_at"] is not None

    def test_does_not_require_authentication(self, client, db):
        """Should be accessible without authentication (public endpoint)."""
        # No admin_headers needed
        response = client.get("/api/stream-info")
        assert response.status_code == 200

    def test_returns_all_metadata_fields(self, client, db):
        """Should include all metadata fields in response."""
        video_id = "FullField_1"  # exactly 11 chars
        db.add(SystemSetting(
            key="youtube_url",
            value=f"https://www.youtube.com/watch?v={video_id}"
        ))
        db.add(LiveStream(
            video_id=video_id,
            title="Full Fields Stream",
            channel_id="UC_full",
            channel_title="Full Channel",
            thumbnail_url="http://img/full.jpg",
            tags=["tag1", "tag2"],
            category_id="20",
            published_at=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
            scheduled_start_time=datetime(2024, 1, 15, 9, 0, 0, tzinfo=timezone.utc),
            actual_start_time=datetime(2024, 1, 15, 10, 5, 0, tzinfo=timezone.utc),
            live_broadcast_content="live",
            default_language="zh-TW",
            topic_categories=["https://en.wikipedia.org/wiki/Gaming"],
        ))
        db.flush()

        response = client.get("/api/stream-info")
        stream = response.json()["stream"]

        assert stream["video_id"] == video_id
        assert stream["title"] == "Full Fields Stream"
        assert stream["channel_id"] == "UC_full"
        assert stream["channel_title"] == "Full Channel"
        assert stream["thumbnail_url"] == "http://img/full.jpg"
        assert stream["tags"] == ["tag1", "tag2"]
        assert stream["category_id"] == "20"
        assert stream["published_at"] is not None
        assert stream["scheduled_start_time"] is not None
        assert stream["actual_start_time"] is not None
        assert stream["live_broadcast_content"] == "live"
        assert stream["default_language"] == "zh-TW"
        assert stream["topic_categories"] == ["https://en.wikipedia.org/wiki/Gaming"]
        assert stream["fetched_at"] is not None

    def test_ignores_stats_from_different_video(self, client, db):
        """Should only return stats matching the current video_id."""
        video_id = "CurrentV_11"  # exactly 11 chars
        db.add(SystemSetting(
            key="youtube_url",
            value=f"https://www.youtube.com/watch?v={video_id}"
        ))
        db.add(LiveStream(
            video_id=video_id,
            title="Current Stream",
            live_broadcast_content="live",
        ))
        # Stats for a different video
        db.add(StreamStats(
            live_stream_id="OtherVid_11",
            concurrent_viewers=9999,
            view_count=99999,
            like_count=999,
            collected_at=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
        ))
        db.flush()

        response = client.get("/api/stream-info")
        stream = response.json()["stream"]

        assert stream is not None
        assert stream["video_id"] == video_id
        assert stream["stats"] is None
