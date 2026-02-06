def test_get_all_settings_empty(client):
    response = client.get("/api/admin/settings")
    assert response.status_code == 200
    data = response.json()
    assert "settings" in data

def test_get_setting_not_exists(client):
    response = client.get("/api/admin/settings/nonexistent")
    assert response.status_code == 200
    data = response.json()
    assert data["key"] == "nonexistent"
    assert data["value"] is None

def test_create_setting(admin_client):
    response = admin_client.post("/api/admin/settings", json={
        "key": "test_key",
        "value": "test_value",
        "description": "Test description"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True
    assert data["key"] == "test_key"
    assert data["value"] == "test_value"

def test_update_setting(admin_client):
    # Create first
    admin_client.post("/api/admin/settings", json={
        "key": "update_key",
        "value": "original_value"
    })

    # Update
    response = admin_client.post("/api/admin/settings", json={
        "key": "update_key",
        "value": "new_value"
    })

    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True
    assert "updated" in data["message"]

def test_get_setting_after_create(admin_client, client):
    admin_client.post("/api/admin/settings", json={
        "key": "fetch_key",
        "value": "fetch_value"
    })

    response = client.get("/api/admin/settings/fetch_key")
    assert response.status_code == 200
    data = response.json()
    assert data["key"] == "fetch_key"
    assert data["value"] == "fetch_value"

def test_create_youtube_url_setting(admin_client):
    response = admin_client.post("/api/admin/settings", json={
        "key": "youtube_url",
        "value": "https://www.youtube.com/watch?v=TestVideo123"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True
    assert data["key"] == "youtube_url"

def test_invalid_key_too_long(admin_client):
    long_key = "a" * 150
    response = admin_client.post("/api/admin/settings", json={
        "key": long_key,
        "value": "value"
    })
    assert response.status_code == 400


def test_delete_setting_success(admin_client, client):
    """Test successful deletion of a setting."""
    # Create first
    admin_client.post("/api/admin/settings", json={
        "key": "delete_me",
        "value": "will_be_deleted"
    })

    # Delete
    response = admin_client.delete("/api/admin/settings/delete_me")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True
    assert "deleted" in data["message"]

    # Verify deletion
    get_response = client.get("/api/admin/settings/delete_me")
    assert get_response.json()["value"] is None


def test_delete_setting_not_found(admin_client):
    """Test deletion of non-existent setting returns 404."""
    response = admin_client.delete("/api/admin/settings/nonexistent_key")
    assert response.status_code == 404


# --- YouTube URL metadata fetch trigger tests ---

from unittest.mock import patch, Mock
from app.models import LiveStream


class TestYoutubeUrlMetadataFetch:
    """Tests for the metadata fetch triggered when saving youtube_url."""

    @patch("app.routers.admin_settings.fetch_video_metadata")
    @patch("app.routers.admin_settings.build_live_stream_from_api")
    def test_fetches_metadata_on_youtube_url_save(
        self, mock_build, mock_fetch, admin_client, db
    ):
        """Should call YouTube API when youtube_url is saved."""
        video_id = "TestVid1234"  # exactly 11 chars
        mock_fetch.return_value = {"snippet": {"title": "Test"}}
        mock_build.return_value = LiveStream(
            video_id=video_id,
            title="Test Stream",
        )

        response = admin_client.post("/api/admin/settings", json={
            "key": "youtube_url",
            "value": f"https://www.youtube.com/watch?v={video_id}"
        })

        assert response.status_code == 200
        assert response.json()["success"] is True
        mock_fetch.assert_called_once_with(video_id)
        mock_build.assert_called_once()

    @patch("app.routers.admin_settings.fetch_video_metadata")
    def test_setting_saved_even_when_fetch_fails(self, mock_fetch, admin_client, db):
        """Setting should be saved even if metadata fetch fails."""
        mock_fetch.side_effect = Exception("API down")

        response = admin_client.post("/api/admin/settings", json={
            "key": "youtube_url",
            "value": "https://www.youtube.com/watch?v=FailFetch12"
        })

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["key"] == "youtube_url"
        assert data["value"] == "https://www.youtube.com/watch?v=FailFetch12"

    @patch("app.routers.admin_settings.fetch_video_metadata")
    def test_setting_saved_when_fetch_returns_none(self, mock_fetch, admin_client, db):
        """Setting should be saved when metadata fetch returns None (no API key, etc.)."""
        mock_fetch.return_value = None

        response = admin_client.post("/api/admin/settings", json={
            "key": "youtube_url",
            "value": "https://www.youtube.com/watch?v=NoMeta12345"
        })

        assert response.status_code == 200
        assert response.json()["success"] is True
        mock_fetch.assert_called_once_with("NoMeta12345")

    @patch("app.routers.admin_settings.fetch_video_metadata")
    def test_no_fetch_for_non_youtube_url_key(self, mock_fetch, admin_client, db):
        """Should NOT fetch metadata when saving a non-youtube_url key."""
        response = admin_client.post("/api/admin/settings", json={
            "key": "other_setting",
            "value": "some_value"
        })

        assert response.status_code == 200
        mock_fetch.assert_not_called()

    @patch("app.routers.admin_settings.fetch_video_metadata")
    def test_no_fetch_for_invalid_video_id(self, mock_fetch, admin_client, db):
        """Should not call fetch when video_id cannot be extracted from URL."""
        response = admin_client.post("/api/admin/settings", json={
            "key": "youtube_url",
            "value": "https://example.com/short"
        })

        assert response.status_code == 200
        assert response.json()["success"] is True
        mock_fetch.assert_not_called()

    @patch("app.routers.admin_settings.fetch_video_metadata")
    @patch("app.routers.admin_settings.build_live_stream_from_api")
    def test_upserts_live_stream_record(
        self, mock_build, mock_fetch, admin_client, db
    ):
        """Should upsert LiveStream record via db.merge."""
        live_stream = LiveStream(
            video_id="UpsertVid12",
            title="First Title",
        )
        mock_fetch.return_value = {"snippet": {"title": "First Title"}}
        mock_build.return_value = live_stream

        # First save
        response = admin_client.post("/api/admin/settings", json={
            "key": "youtube_url",
            "value": "https://www.youtube.com/watch?v=UpsertVid12"
        })
        assert response.status_code == 200

        # Verify LiveStream was saved
        saved = db.query(LiveStream).filter(
            LiveStream.video_id == "UpsertVid12"
        ).first()
        assert saved is not None
        assert saved.title == "First Title"
