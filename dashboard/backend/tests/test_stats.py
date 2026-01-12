import pytest

def test_get_viewer_stats_empty(client):
    response = client.get("/api/stats/viewers")
    assert response.status_code == 200
    assert response.json() == []

def test_get_viewer_stats_with_data(client, sample_stream_stats):
    response = client.get("/api/stats/viewers")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 5
    assert "time" in data[0]
    assert "count" in data[0]

def test_get_viewer_stats_with_limit(client, sample_stream_stats):
    response = client.get("/api/stats/viewers?limit=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2

@pytest.mark.skip(reason="date_trunc is PostgreSQL-specific, not available in SQLite")
def test_get_comment_stats_empty(client):
    response = client.get("/api/stats/comments")
    assert response.status_code == 200
    assert response.json() == []

@pytest.mark.skip(reason="date_trunc is PostgreSQL-specific, not available in SQLite")
def test_get_comment_stats_with_data(client, sample_chat_messages):
    response = client.get("/api/stats/comments?hours=24")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_get_money_summary_empty(client):
    response = client.get("/api/stats/money-summary")
    assert response.status_code == 200
    data = response.json()
    assert data["total_amount_twd"] == 0
    assert data["paid_message_count"] == 0
    assert data["top_authors"] == []

def test_get_money_summary_with_data(client, sample_chat_messages, sample_currency_rates):
    response = client.get("/api/stats/money-summary")
    assert response.status_code == 200
    data = response.json()
    assert "total_amount_twd" in data
    assert "paid_message_count" in data
    assert "top_authors" in data
    assert "unknown_currencies" in data
