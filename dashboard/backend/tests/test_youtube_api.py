import datetime
from unittest.mock import patch, Mock

import pytest

from app.services.youtube_api import (
    _pick_best_thumbnail,
    _parse_datetime,
    fetch_video_metadata,
    build_live_stream_from_api,
)
from app.models import LiveStream


class TestPickBestThumbnail:
    def test_picks_maxres_first(self):
        thumbnails = {
            "default": {"url": "http://img/default.jpg"},
            "medium": {"url": "http://img/medium.jpg"},
            "high": {"url": "http://img/high.jpg"},
            "standard": {"url": "http://img/standard.jpg"},
            "maxres": {"url": "http://img/maxres.jpg"},
        }
        assert _pick_best_thumbnail(thumbnails) == "http://img/maxres.jpg"

    def test_falls_back_to_standard(self):
        thumbnails = {
            "default": {"url": "http://img/default.jpg"},
            "standard": {"url": "http://img/standard.jpg"},
        }
        assert _pick_best_thumbnail(thumbnails) == "http://img/standard.jpg"

    def test_falls_back_to_high(self):
        thumbnails = {
            "high": {"url": "http://img/high.jpg"},
            "default": {"url": "http://img/default.jpg"},
        }
        assert _pick_best_thumbnail(thumbnails) == "http://img/high.jpg"

    def test_falls_back_to_default(self):
        thumbnails = {
            "default": {"url": "http://img/default.jpg"},
        }
        assert _pick_best_thumbnail(thumbnails) == "http://img/default.jpg"

    def test_returns_none_for_empty_dict(self):
        assert _pick_best_thumbnail({}) is None

    def test_skips_entry_with_no_url(self):
        thumbnails = {
            "maxres": {"width": 1280},
            "high": {"url": "http://img/high.jpg"},
        }
        assert _pick_best_thumbnail(thumbnails) == "http://img/high.jpg"

    def test_skips_entry_with_empty_url(self):
        thumbnails = {
            "maxres": {"url": ""},
            "medium": {"url": "http://img/medium.jpg"},
        }
        assert _pick_best_thumbnail(thumbnails) == "http://img/medium.jpg"


class TestParseDatetime:
    def test_parses_iso_with_z(self):
        result = _parse_datetime("2024-01-15T10:30:00Z")
        assert result == datetime.datetime(2024, 1, 15, 10, 30, 0, tzinfo=datetime.timezone.utc)

    def test_parses_iso_with_offset(self):
        result = _parse_datetime("2024-01-15T10:30:00+08:00")
        assert result is not None
        assert result.year == 2024
        assert result.hour == 10

    def test_returns_none_for_none(self):
        assert _parse_datetime(None) is None

    def test_returns_none_for_empty_string(self):
        assert _parse_datetime("") is None


class TestFetchVideoMetadata:
    @patch.dict("os.environ", {"YOUTUBE_API_KEY": ""}, clear=False)
    def test_returns_none_when_no_api_key(self):
        """Should return None when YOUTUBE_API_KEY is not set."""
        with patch.dict("os.environ", {}, clear=False):
            # Remove the key entirely
            import os
            orig = os.environ.pop("YOUTUBE_API_KEY", None)
            try:
                result = fetch_video_metadata("test_id")
                assert result is None
            finally:
                if orig is not None:
                    os.environ["YOUTUBE_API_KEY"] = orig

    @patch("app.services.youtube_api.requests.get")
    @patch.dict("os.environ", {"YOUTUBE_API_KEY": "fake-key"})
    def test_returns_first_item_on_success(self, mock_get):
        """Should return the first item from the API response."""
        mock_resp = Mock()
        mock_resp.raise_for_status = Mock()
        mock_resp.json.return_value = {
            "items": [
                {"id": "vid123", "snippet": {"title": "Test"}},
                {"id": "vid456", "snippet": {"title": "Other"}},
            ]
        }
        mock_get.return_value = mock_resp

        result = fetch_video_metadata("vid123")

        assert result == {"id": "vid123", "snippet": {"title": "Test"}}
        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args
        assert call_kwargs[1]["params"]["id"] == "vid123"
        assert call_kwargs[1]["params"]["key"] == "fake-key"

    @patch("app.services.youtube_api.requests.get")
    @patch.dict("os.environ", {"YOUTUBE_API_KEY": "fake-key"})
    def test_returns_none_on_empty_items(self, mock_get):
        """Should return None when API returns no items."""
        mock_resp = Mock()
        mock_resp.raise_for_status = Mock()
        mock_resp.json.return_value = {"items": []}
        mock_get.return_value = mock_resp

        result = fetch_video_metadata("nonexistent")
        assert result is None

    @patch("app.services.youtube_api.requests.get")
    @patch.dict("os.environ", {"YOUTUBE_API_KEY": "fake-key"})
    def test_returns_none_on_http_error(self, mock_get):
        """Should return None when API returns non-200 status."""
        import requests
        mock_get.side_effect = requests.RequestException("403 Forbidden")

        result = fetch_video_metadata("vid123")
        assert result is None

    @patch("app.services.youtube_api.requests.get")
    @patch.dict("os.environ", {"YOUTUBE_API_KEY": "fake-key"})
    def test_returns_none_on_timeout(self, mock_get):
        """Should return None on request timeout."""
        import requests
        mock_get.side_effect = requests.Timeout("Connection timed out")

        result = fetch_video_metadata("vid123")
        assert result is None


class TestBuildLiveStreamFromApi:
    def test_builds_full_live_stream(self):
        """Should populate all fields from a complete API response."""
        item = {
            "snippet": {
                "title": "Test Stream Title",
                "channelId": "UC12345",
                "channelTitle": "Test Channel",
                "description": "Stream description",
                "thumbnails": {
                    "high": {"url": "http://img/high.jpg"},
                    "maxres": {"url": "http://img/maxres.jpg"},
                },
                "tags": ["gaming", "live"],
                "categoryId": "20",
                "publishedAt": "2024-01-15T10:00:00Z",
                "liveBroadcastContent": "live",
                "defaultLanguage": "zh-TW",
            },
            "liveStreamingDetails": {
                "scheduledStartTime": "2024-01-15T09:00:00Z",
                "actualStartTime": "2024-01-15T10:05:00Z",
            },
            "topicDetails": {
                "topicCategories": [
                    "https://en.wikipedia.org/wiki/Video_game",
                ]
            },
        }

        result = build_live_stream_from_api("vid123", item)

        assert isinstance(result, LiveStream)
        assert result.video_id == "vid123"
        assert result.title == "Test Stream Title"
        assert result.channel_id == "UC12345"
        assert result.channel_title == "Test Channel"
        assert result.description == "Stream description"
        assert result.thumbnail_url == "http://img/maxres.jpg"
        assert result.tags == ["gaming", "live"]
        assert result.category_id == "20"
        assert result.published_at == datetime.datetime(
            2024, 1, 15, 10, 0, 0, tzinfo=datetime.timezone.utc
        )
        assert result.scheduled_start_time is not None
        assert result.actual_start_time is not None
        assert result.live_broadcast_content == "live"
        assert result.default_language == "zh-TW"
        assert result.topic_categories == [
            "https://en.wikipedia.org/wiki/Video_game"
        ]
        assert result.fetched_at is not None

    def test_builds_with_minimal_data(self):
        """Should handle missing optional fields gracefully."""
        item = {
            "snippet": {
                "title": "Minimal Stream",
            },
        }

        result = build_live_stream_from_api("vid_min", item)

        assert isinstance(result, LiveStream)
        assert result.video_id == "vid_min"
        assert result.title == "Minimal Stream"
        assert result.channel_id is None
        assert result.channel_title is None
        assert result.thumbnail_url is None
        assert result.tags is None
        assert result.scheduled_start_time is None
        assert result.actual_start_time is None
        assert result.topic_categories is None

    def test_builds_with_empty_item(self):
        """Should handle completely empty item dict."""
        result = build_live_stream_from_api("vid_empty", {})

        assert isinstance(result, LiveStream)
        assert result.video_id == "vid_empty"
        assert result.title is None
