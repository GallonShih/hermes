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
    for msg in data["messages"]:
        assert msg["message_type"] == "paid_message"

def test_get_chat_messages_non_paid_only(client, sample_chat_messages):
    response = client.get("/api/chat/messages?paid_message_filter=non_paid_only")
    assert response.status_code == 200
    data = response.json()
    for msg in data["messages"]:
        assert msg["message_type"] != "paid_message"

def test_get_chat_messages_author_filter(client, sample_chat_messages):
    response = client.get("/api/chat/messages?author_filter=User1")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1

def test_get_chat_messages_message_filter(client, sample_chat_messages):
    response = client.get("/api/chat/messages?message_filter=Test")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 10
