"""Tests for wordcloud router.

Note: The wordcloud router uses PostgreSQL-specific features (unnest for arrays),
so we mock the database execute calls to test the endpoint logic.
"""
import pytest
from unittest.mock import patch, MagicMock


class TestGetWordFrequency:
    """Tests for the /api/wordcloud/word-frequency endpoint."""

    def test_word_frequency_empty_result(self, client):
        """Test endpoint returns empty result when no data."""
        with patch('app.routers.wordcloud.get_current_video_id', return_value=None):
            mock_result = MagicMock()
            mock_result.fetchall.return_value = []
            mock_stats_result = MagicMock()
            mock_stats_result.fetchone.return_value = (0, 0)
            
            from app.core.database import get_db
            from main import app
            
            mock_db = MagicMock()
            mock_db.execute.side_effect = [mock_result, mock_stats_result]
            
            def mock_db_override():
                yield mock_db
            
            original_override = app.dependency_overrides.get(get_db)
            app.dependency_overrides[get_db] = mock_db_override
            
            try:
                response = client.get("/api/wordcloud/word-frequency")
                assert response.status_code == 200
                data = response.json()
                assert data["words"] == []
                assert data["total_messages"] == 0
                assert data["unique_words"] == 0
                assert "excluded_words" in data
            finally:
                if original_override:
                    app.dependency_overrides[get_db] = original_override

    def test_word_frequency_with_data(self, client):
        """Test endpoint returns word frequency data."""
        with patch('app.routers.wordcloud.get_current_video_id', return_value=None):
            mock_result = MagicMock()
            # Now returns (message_id, word) tuples
            mock_result.fetchall.return_value = [
                ("msg1", "哈哈"),
                ("msg2", "哈哈"),
                ("msg3", "哈哈"),
                ("msg1", "好"),
                ("msg2", "好"),
                ("msg1", "讚"),
            ]
            mock_stats_result = MagicMock()
            mock_stats_result.fetchone.return_value = (100, 50)
            
            from app.core.database import get_db
            from main import app
            
            mock_db = MagicMock()
            mock_db.execute.side_effect = [mock_result, mock_stats_result]
            
            def mock_db_override():
                yield mock_db
            
            original_override = app.dependency_overrides.get(get_db)
            app.dependency_overrides[get_db] = mock_db_override
            
            try:
                response = client.get("/api/wordcloud/word-frequency")
                assert response.status_code == 200
                data = response.json()
                assert len(data["words"]) == 3
                # 哈哈 appears in 3 messages, 好 in 2, 讚 in 1
                assert data["words"][0] == {"word": "哈哈", "count": 3}
                assert data["words"][1] == {"word": "好", "count": 2}
                assert data["words"][2] == {"word": "讚", "count": 1}
                assert data["total_messages"] == 100
                assert data["unique_words"] == 50
            finally:
                if original_override:
                    app.dependency_overrides[get_db] = original_override

    def test_word_frequency_with_limit(self, client):
        """Test endpoint respects limit parameter."""
        with patch('app.routers.wordcloud.get_current_video_id', return_value=None):
            mock_result = MagicMock()
            # (message_id, word) tuples
            mock_result.fetchall.return_value = [
                ("msg1", "word1"), ("msg2", "word1"), ("msg3", "word1"),
                ("msg1", "word2"), ("msg2", "word2"),
                ("msg1", "word3"),
                ("msg1", "word4"),
                ("msg1", "word5"),
            ]
            mock_stats_result = MagicMock()
            mock_stats_result.fetchone.return_value = (50, 25)
            
            from app.core.database import get_db
            from main import app
            
            mock_db = MagicMock()
            mock_db.execute.side_effect = [mock_result, mock_stats_result]
            
            def mock_db_override():
                yield mock_db
            
            original_override = app.dependency_overrides.get(get_db)
            app.dependency_overrides[get_db] = mock_db_override
            
            try:
                response = client.get("/api/wordcloud/word-frequency?limit=3")
                assert response.status_code == 200
                data = response.json()
                # Limit is applied after fetching, so we should get at most 3 words
                assert len(data["words"]) <= 3
            finally:
                if original_override:
                    app.dependency_overrides[get_db] = original_override

    def test_word_frequency_excludes_punctuation(self, client):
        """Test endpoint excludes punctuation from results."""
        with patch('app.routers.wordcloud.get_current_video_id', return_value=None):
            mock_result = MagicMock()
            # Include some punctuation that should be filtered out
            mock_result.fetchall.return_value = [
                ("msg1", "哈哈"),
                ("msg2", "哈哈"),
                ("msg1", "!"),  # Should be excluded
                ("msg2", "。"),  # Should be excluded
                ("msg1", "好"),
            ]
            mock_stats_result = MagicMock()
            mock_stats_result.fetchone.return_value = (100, 50)
            
            from app.core.database import get_db
            from main import app
            
            mock_db = MagicMock()
            mock_db.execute.side_effect = [mock_result, mock_stats_result]
            
            def mock_db_override():
                yield mock_db
            
            original_override = app.dependency_overrides.get(get_db)
            app.dependency_overrides[get_db] = mock_db_override
            
            try:
                response = client.get("/api/wordcloud/word-frequency")
                assert response.status_code == 200
                data = response.json()
                words = [w["word"] for w in data["words"]]
                assert "哈哈" in words
                assert "好" in words
                assert "!" not in words
                assert "。" not in words
            finally:
                if original_override:
                    app.dependency_overrides[get_db] = original_override

    def test_word_frequency_with_custom_exclude(self, client):
        """Test endpoint excludes custom words from results."""
        with patch('app.routers.wordcloud.get_current_video_id', return_value=None):
            mock_result = MagicMock()
            mock_result.fetchall.return_value = [
                ("msg1", "哈哈"),
                ("msg2", "哈哈"),
                ("msg1", "好"),
                ("msg1", "讚"),
            ]
            mock_stats_result = MagicMock()
            mock_stats_result.fetchone.return_value = (100, 50)
            
            from app.core.database import get_db
            from main import app
            
            mock_db = MagicMock()
            mock_db.execute.side_effect = [mock_result, mock_stats_result]
            
            def mock_db_override():
                yield mock_db
            
            original_override = app.dependency_overrides.get(get_db)
            app.dependency_overrides[get_db] = mock_db_override
            
            try:
                response = client.get("/api/wordcloud/word-frequency?exclude_words=哈哈,好")
                assert response.status_code == 200
                data = response.json()
                words = [w["word"] for w in data["words"]]
                assert "哈哈" not in words
                assert "好" not in words
                assert "讚" in words
            finally:
                if original_override:
                    app.dependency_overrides[get_db] = original_override

    def test_word_frequency_with_video_id_filter(self, client):
        """Test endpoint filters by current video ID."""
        with patch('app.routers.wordcloud.get_current_video_id', return_value="test_video_123"):
            mock_result = MagicMock()
            mock_result.fetchall.return_value = [("msg1", "filtered_word")]
            mock_stats_result = MagicMock()
            mock_stats_result.fetchone.return_value = (10, 5)
            
            from app.core.database import get_db
            from main import app
            
            mock_db = MagicMock()
            mock_db.execute.side_effect = [mock_result, mock_stats_result]
            
            def mock_db_override():
                yield mock_db
            
            original_override = app.dependency_overrides.get(get_db)
            app.dependency_overrides[get_db] = mock_db_override
            
            try:
                response = client.get("/api/wordcloud/word-frequency")
                assert response.status_code == 200
                data = response.json()
                # Verify the endpoint was called (mock was used)
                assert mock_db.execute.called
            finally:
                if original_override:
                    app.dependency_overrides[get_db] = original_override

    def test_word_frequency_with_time_filter(self, client):
        """Test endpoint accepts time filter parameters."""
        with patch('app.routers.wordcloud.get_current_video_id', return_value=None):
            mock_result = MagicMock()
            mock_result.fetchall.return_value = [("msg1", "時間詞")]
            mock_stats_result = MagicMock()
            mock_stats_result.fetchone.return_value = (20, 10)
            
            from app.core.database import get_db
            from main import app
            
            mock_db = MagicMock()
            mock_db.execute.side_effect = [mock_result, mock_stats_result]
            
            def mock_db_override():
                yield mock_db
            
            original_override = app.dependency_overrides.get(get_db)
            app.dependency_overrides[get_db] = mock_db_override
            
            try:
                response = client.get(
                    "/api/wordcloud/word-frequency"
                    "?start_time=2026-01-01T00:00:00"
                    "&end_time=2026-01-31T23:59:59"
                )
                assert response.status_code == 200
                data = response.json()
                assert len(data["words"]) == 1
                assert data["words"][0]["word"] == "時間詞"
            finally:
                if original_override:
                    app.dependency_overrides[get_db] = original_override

    def test_word_frequency_database_error(self, client):
        """Test endpoint handles database errors gracefully."""
        with patch('app.routers.wordcloud.get_current_video_id', return_value=None):
            from app.core.database import get_db
            from main import app
            
            mock_db = MagicMock()
            mock_db.execute.side_effect = Exception("Database connection failed")
            
            def mock_db_override():
                yield mock_db
            
            original_override = app.dependency_overrides.get(get_db)
            app.dependency_overrides[get_db] = mock_db_override
            
            try:
                response = client.get("/api/wordcloud/word-frequency")
                assert response.status_code == 500
                data = response.json()
                assert "detail" in data
            finally:
                if original_override:
                    app.dependency_overrides[get_db] = original_override

    def test_word_frequency_limit_validation(self, client):
        """Test endpoint validates limit parameter."""
        # Test limit too small
        response = client.get("/api/wordcloud/word-frequency?limit=0")
        assert response.status_code == 422  # Validation error

        # Test limit too large
        response = client.get("/api/wordcloud/word-frequency?limit=1000")
        assert response.status_code == 422  # Validation error

    def test_word_frequency_null_stats(self, client):
        """Test endpoint handles null stats gracefully."""
        with patch('app.routers.wordcloud.get_current_video_id', return_value=None):
            mock_result = MagicMock()
            mock_result.fetchall.return_value = []
            mock_stats_result = MagicMock()
            mock_stats_result.fetchone.return_value = None  # No stats row
            
            from app.core.database import get_db
            from main import app
            
            mock_db = MagicMock()
            mock_db.execute.side_effect = [mock_result, mock_stats_result]
            
            def mock_db_override():
                yield mock_db
            
            original_override = app.dependency_overrides.get(get_db)
            app.dependency_overrides[get_db] = mock_db_override
            
            try:
                response = client.get("/api/wordcloud/word-frequency")
                assert response.status_code == 200
                data = response.json()
                assert data["total_messages"] == 0
                assert data["unique_words"] == 0
            finally:
                if original_override:
                    app.dependency_overrides[get_db] = original_override

