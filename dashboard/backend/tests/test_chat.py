from datetime import datetime, timezone

from app.models import ChatMessage


def test_get_chat_messages_empty(client):
    response = client.get("/api/chat/messages")
    assert response.status_code == 200
    data = response.json()
    assert data["messages"] == []
    assert data["total"] == 0
    assert data["limit"] == 100
    assert data["offset"] == 0

def test_get_chat_messages_with_data(client, sample_chat_messages):
    response = client.get("/api/chat/messages")
    assert response.status_code == 200
    data = response.json()
    assert len(data["messages"]) == 10
    assert data["total"] == 10

def test_get_chat_messages_with_limit(client, sample_chat_messages):
    response = client.get("/api/chat/messages?limit=3")
    assert response.status_code == 200
    data = response.json()
    assert len(data["messages"]) == 3
    assert data["total"] == 10

def test_get_chat_messages_with_offset(client, sample_chat_messages):
    response = client.get("/api/chat/messages?limit=5&offset=5")
    assert response.status_code == 200
    data = response.json()
    assert len(data["messages"]) == 5
    assert data["offset"] == 5

def test_get_chat_messages_max_limit(client, sample_chat_messages):
    response = client.get("/api/chat/messages?limit=1000")
    assert response.status_code == 200
    data = response.json()
    assert data["limit"] == 500

def test_get_chat_messages_paid_only(client, sample_chat_messages):
    response = client.get("/api/chat/messages?paid_message_filter=paid_only")
    assert response.status_code == 200
    data = response.json()
    # 4 paid_message (1,3,5,7) + 1 ticker_paid_message_item (9) = 5
    assert data["total"] == 5
    paid_types = {"paid_message", "ticker_paid_message_item"}
    for msg in data["messages"]:
        assert msg["message_type"] in paid_types

def test_get_chat_messages_non_paid_only(client, sample_chat_messages):
    response = client.get("/api/chat/messages?paid_message_filter=non_paid_only")
    assert response.status_code == 200
    data = response.json()
    # 5 text_message (0,2,4,6,8)
    assert data["total"] == 5
    paid_types = {"paid_message", "ticker_paid_message_item"}
    for msg in data["messages"]:
        assert msg["message_type"] not in paid_types

def test_get_chat_messages_author_filter(client, sample_chat_messages):
    response = client.get("/api/chat/messages?author_filter=User1")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1

def test_get_chat_messages_message_filter(client, sample_chat_messages):
    response = client.get("/api/chat/messages?message_filter=Test")
    assert response.status_code == 200
    data = response.json()


# Test top-authors endpoint
def test_get_top_authors_empty(client):
    """Test top authors endpoint with no data."""
    response = client.get("/api/chat/top-authors")
    assert response.status_code == 200
    assert response.json() == []


def test_get_top_authors_with_data(client, sample_chat_messages):
    """Test top authors endpoint with sample data."""
    response = client.get("/api/chat/top-authors")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        assert "author_id" in data[0]
        assert "author" in data[0]
        assert "count" in data[0]


def test_get_top_authors_with_filters(client, sample_chat_messages):
    """Test top authors with message filter."""
    response = client.get("/api/chat/top-authors?message_filter=Test")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_get_top_authors_paid_only(client, sample_chat_messages):
    """Test top authors filtered to paid messages only."""
    response = client.get("/api/chat/top-authors?paid_message_filter=paid_only")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_get_top_authors_with_time_range(client, sample_chat_messages):
    """Test top authors with time range filter."""
    response = client.get(
        "/api/chat/top-authors?start_time=2026-01-01T00:00:00&end_time=2026-12-31T23:59:59"
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_get_top_authors_include_meta(client, sample_chat_messages):
    """Test top authors endpoint with metadata payload."""
    response = client.get(
        "/api/chat/top-authors?include_meta=true"
        "&start_time=2026-01-01T00:00:00&end_time=2026-12-31T23:59:59"
    )
    assert response.status_code == 200
    data = response.json()

    assert isinstance(data, dict)
    assert "top_authors" in data
    assert "total_authors" in data
    assert "displayed_authors" in data
    assert "tie_extended" in data
    assert data["total_authors"] == 10
    assert data["displayed_authors"] == len(data["top_authors"])


def test_get_top_authors_uses_author_id_and_latest_name(client, db):
    """Test aggregation by author_id and display name from latest message."""
    older = ChatMessage(
        message_id="same_author_old",
        live_stream_id="test_stream",
        message="hello old",
        timestamp=1704067200000000,
        published_at=datetime(2026, 1, 12, 10, 0, 0, tzinfo=timezone.utc),
        author_name="OldName",
        author_id="same_user",
        message_type="text_message",
        raw_data=None,
    )
    newer = ChatMessage(
        message_id="same_author_new",
        live_stream_id="test_stream",
        message="hello new",
        timestamp=1704067201000000,
        published_at=datetime(2026, 1, 12, 10, 1, 0, tzinfo=timezone.utc),
        author_name="NewName",
        author_id="same_user",
        message_type="text_message",
        raw_data=None,
    )
    another = ChatMessage(
        message_id="another_author",
        live_stream_id="test_stream",
        message="another",
        timestamp=1704067202000000,
        published_at=datetime(2026, 1, 12, 10, 2, 0, tzinfo=timezone.utc),
        author_name="AnotherName",
        author_id="another_user",
        message_type="text_message",
        raw_data=None,
    )
    db.add_all([older, newer, another])
    db.flush()

    response = client.get(
        "/api/chat/top-authors?include_meta=true"
        "&start_time=2026-01-01T00:00:00&end_time=2026-12-31T23:59:59"
    )
    assert response.status_code == 200
    data = response.json()

    top = data["top_authors"]
    assert top[0]["author_id"] == "same_user"
    assert top[0]["count"] == 2
    assert top[0]["author"] == "NewName"
    assert data["total_authors"] == 2


def test_get_author_summary_not_found(client):
    response = client.get("/api/chat/authors/not_exists/summary")
    assert response.status_code == 404
    detail = response.json().get("detail", "")
    assert "可能不在目前直播或時間範圍內" in detail


def test_get_author_summary_alias_order_and_stats(client, db):
    alias_old = ChatMessage(
        message_id="alias_old",
        live_stream_id="test_stream",
        message="old alias message",
        timestamp=1704067200000000,
        published_at=datetime(2026, 1, 12, 8, 0, 0, tzinfo=timezone.utc),
        author_name="Alpha",
        author_id="author_x",
        message_type="text_message",
        raw_data=None,
    )
    alias_mid_paid = ChatMessage(
        message_id="alias_mid_paid",
        live_stream_id="test_stream",
        message="paid alias message",
        timestamp=1704067201000000,
        published_at=datetime(2026, 1, 12, 9, 0, 0, tzinfo=timezone.utc),
        author_name="Beta",
        author_id="author_x",
        message_type="paid_message",
        raw_data={"money": {"currency": "TWD", "amount": "100"}},
    )
    alias_latest = ChatMessage(
        message_id="alias_latest",
        live_stream_id="test_stream",
        message="latest alias message",
        timestamp=1704067202000000,
        published_at=datetime(2026, 1, 12, 10, 0, 0, tzinfo=timezone.utc),
        author_name="Gamma",
        author_id="author_x",
        message_type="text_message",
        raw_data=None,
    )
    db.add_all([alias_old, alias_mid_paid, alias_latest])
    db.flush()

    response = client.get(
        "/api/chat/authors/author_x/summary"
        "?start_time=2026-01-12T07:00:00Z&end_time=2026-01-12T11:00:00Z"
    )
    assert response.status_code == 200
    data = response.json()

    assert data["author_id"] == "author_x"
    assert data["display_name"] == "Gamma"
    assert data["total_messages"] == 3
    assert data["paid_messages"] == 1

    aliases = data["aliases"]
    assert [a["name"] for a in aliases] == ["Alpha", "Beta", "Gamma"]
    assert aliases[0]["message_count"] == 1
    assert aliases[1]["message_count"] == 1
    assert aliases[2]["message_count"] == 1


def test_get_author_messages_filters_by_author_and_paginates(client, db):
    msgs = [
        ChatMessage(
            message_id=f"author_y_{i}",
            live_stream_id="test_stream",
            message=f"Y message {i}",
            timestamp=1704067200000000 + i * 1000000,
            published_at=datetime(2026, 1, 12, 10, i, 0, tzinfo=timezone.utc),
            author_name="AuthorY",
            author_id="author_y",
            message_type="text_message",
            raw_data=None,
        )
        for i in range(4)
    ]
    other = ChatMessage(
        message_id="author_z_1",
        live_stream_id="test_stream",
        message="Z message",
        timestamp=1704067209000000,
        published_at=datetime(2026, 1, 12, 10, 30, 0, tzinfo=timezone.utc),
        author_name="AuthorZ",
        author_id="author_z",
        message_type="text_message",
        raw_data=None,
    )
    db.add_all(msgs + [other])
    db.flush()

    response = client.get(
        "/api/chat/authors/author_y/messages"
        "?start_time=2026-01-12T09:00:00Z&end_time=2026-01-12T11:00:00Z"
        "&limit=2&offset=1"
    )
    assert response.status_code == 200
    data = response.json()

    assert data["author_id"] == "author_y"
    assert data["total"] == 4
    assert data["limit"] == 2
    assert data["offset"] == 1
    assert len(data["messages"]) == 2
    for msg in data["messages"]:
        assert msg["author"] == "AuthorY"


def test_get_author_trend_with_time_range(client, db):
    rows = [
        ChatMessage(
            message_id="trend_a1",
            live_stream_id="test_stream",
            message="trend 1",
            timestamp=1704067200000000,
            published_at=datetime(2026, 1, 12, 10, 5, 0, tzinfo=timezone.utc),
            author_name="TrendAuthor",
            author_id="trend_author",
            message_type="text_message",
            raw_data=None,
        ),
        ChatMessage(
            message_id="trend_a2",
            live_stream_id="test_stream",
            message="trend 2",
            timestamp=1704067201000000,
            published_at=datetime(2026, 1, 12, 10, 40, 0, tzinfo=timezone.utc),
            author_name="TrendAuthor",
            author_id="trend_author",
            message_type="text_message",
            raw_data=None,
        ),
        ChatMessage(
            message_id="trend_a3",
            live_stream_id="test_stream",
            message="trend 3",
            timestamp=1704067202000000,
            published_at=datetime(2026, 1, 12, 11, 10, 0, tzinfo=timezone.utc),
            author_name="TrendAuthor",
            author_id="trend_author",
            message_type="text_message",
            raw_data=None,
        ),
    ]
    db.add_all(rows)
    db.flush()

    response = client.get(
        "/api/chat/authors/trend_author/trend"
        "?start_time=2026-01-12T10:00:00Z&end_time=2026-01-12T11:59:59Z"
    )
    assert response.status_code == 200
    data = response.json()

    assert len(data) == 2
    assert data[0]["count"] == 2
    assert data[1]["count"] == 1


def test_get_author_summary_invalid_time_returns_422(client):
    response = client.get("/api/chat/authors/author_x/summary?start_time=bad-date")
    assert response.status_code == 422


def test_get_author_summary_includes_badges_icon_url(client, db):
    msg = ChatMessage(
        message_id="badge_msg_1",
        live_stream_id="test_stream",
        message="badge test",
        timestamp=1704067205000000,
        published_at=datetime(2026, 1, 12, 10, 5, 0, tzinfo=timezone.utc),
        author_name="BadgeUser",
        author_id="badge_user",
        message_type="text_message",
        raw_data={
            "author": {
                "badges": [
                    {
                        "title": "Member (6 months)",
                        "icons": [
                            {"id": "source", "url": "https://example.com/source.png"},
                            {"id": "16x16", "url": "https://example.com/16.png"},
                        ],
                    }
                ]
            }
        },
    )
    db.add(msg)
    db.flush()

    response = client.get(
        "/api/chat/authors/badge_user/summary"
        "?start_time=2026-01-12T09:00:00Z&end_time=2026-01-12T11:00:00Z"
    )
    assert response.status_code == 200
    data = response.json()

    assert "badges" in data
    assert len(data["badges"]) == 1
    assert data["badges"][0]["title"] == "Member (6 months)"
    assert data["badges"][0]["icon_url"] == "https://example.com/16.png"
