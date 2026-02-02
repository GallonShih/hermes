import pytest
from datetime import datetime, timezone, timedelta


def test_get_word_occurrences_empty(client):
    """Test word occurrence endpoint with no messages."""
    response = client.get("/api/admin/word-occurrences?word=test")
    assert response.status_code == 200
    data = response.json()
    assert data["word"] == "test"
    assert data["total_occurrences"] == 0
    assert data["messages"] == []
    assert data["text_mining_available"] is False


def test_get_word_occurrences_with_messages(client, sample_chat_messages):
    """Test word occurrence endpoint with messages containing the word."""
    response = client.get("/api/admin/word-occurrences?word=Test")
    assert response.status_code == 200
    data = response.json()
    
    assert data["word"] == "Test"
    assert data["total_occurrences"] > 0
    assert len(data["messages"]) > 0
    
    # Check message structure
    first_message = data["messages"][0]
    assert "author" in first_message
    assert "published_at" in first_message
    assert "message" in first_message
    assert "Test" in first_message["message"]


def test_get_word_occurrences_case_insensitive(client, sample_chat_messages):
    """Test that word search is case-insensitive."""
    response_lower = client.get("/api/admin/word-occurrences?word=test")
    response_upper = client.get("/api/admin/word-occurrences?word=TEST")
    
    assert response_lower.status_code == 200
    assert response_upper.status_code == 200
    
    data_lower = response_lower.json()
    data_upper = response_upper.json()
    
    # Should return same number of results
    assert data_lower["total_occurrences"] == data_upper["total_occurrences"]


def test_get_word_occurrences_with_limit(client, sample_chat_messages):
    """Test limit parameter for word occurrences."""
    response = client.get("/api/admin/word-occurrences?word=message&limit=3")
    assert response.status_code == 200
    data = response.json()
    
    # Should return at most 3 messages
    assert len(data["messages"]) <= 3


def test_get_word_occurrences_ordered_by_time(client, sample_chat_messages):
    """Test that messages are ordered by published_at DESC."""
    response = client.get("/api/admin/word-occurrences?word=message&limit=5")
    assert response.status_code == 200
    data = response.json()
    
    if len(data["messages"]) > 1:
        # Check that messages are in descending order
        for i in range(len(data["messages"]) - 1):
            time_1 = datetime.fromisoformat(data["messages"][i]["published_at"].replace("Z", "+00:00"))
            time_2 = datetime.fromisoformat(data["messages"][i + 1]["published_at"].replace("Z", "+00:00"))
            assert time_1 >= time_2, "Messages should be ordered newest first"


def test_get_word_occurrences_text_mining_available(client, db, sample_chat_messages):
    """Test text_mining_available flag when recent messages exist."""
    from app.models import ChatMessage
    
    # Add a recent message with a unique word
    recent_time = datetime.now(timezone.utc) - timedelta(days=1)
    recent_msg = ChatMessage(
        message_id="recent_test_msg",
        live_stream_id="test_stream",
        message="This contains uniqueword123",
        timestamp=int(recent_time.timestamp() * 1000000),
        published_at=recent_time,
        author_name="TestUser",
        author_id="test_user_id"
    )
    db.add(recent_msg)
    db.commit()
    
    response = client.get("/api/admin/word-occurrences?word=uniqueword123")
    assert response.status_code == 200
    data = response.json()
    
    assert data["text_mining_available"] is True
    assert data["seven_day_start"] is not None
    assert data["seven_day_end"] is not None


def test_get_word_occurrences_missing_word_parameter(client):
    """Test that endpoint requires word parameter."""
    response = client.get("/api/admin/word-occurrences")
    assert response.status_code == 422  # Validation error


def test_get_word_occurrences_with_word_type(client, sample_chat_messages):
    """Test word_type parameter is accepted."""
    response = client.get("/api/admin/word-occurrences?word=Test&word_type=replace")
    assert response.status_code == 200
    data = response.json()
    assert data["word"] == "Test"
