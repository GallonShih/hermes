import os
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import (
    Base, ChatMessage, StreamStats, 
    ReplaceWord, SpecialWord,
    PendingReplaceWord, PendingSpecialWord, CurrencyRate
)
from app.core.database import get_db
from main import app

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db):
    Base.metadata.create_all(bind=engine)
    yield TestClient(app)
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def sample_stream_stats(db):
    from datetime import datetime, timezone
    stats = [
        StreamStats(
            live_stream_id="test_stream",
            concurrent_viewers=100 + i * 10,
            collected_at=datetime(2026, 1, 12, 10, i, 0, tzinfo=timezone.utc)
        )
        for i in range(5)
    ]
    db.add_all(stats)
    db.commit()
    return stats

@pytest.fixture
def sample_chat_messages(db):
    from datetime import datetime, timezone
    messages = [
        ChatMessage(
            message_id=f"msg_{i}",
            live_stream_id="test_stream",
            message=f"Test message {i}",
            timestamp=1704067200000000 + i * 1000000,
            published_at=datetime(2026, 1, 12, 10, i, 0, tzinfo=timezone.utc),
            author_name=f"User{i}",
            author_id=f"user_{i}",
            message_type="text_message" if i % 2 == 0 else "paid_message",
            raw_data={"money": {"currency": "TWD", "amount": "100"}} if i % 2 == 1 else None
        )
        for i in range(10)
    ]
    db.add_all(messages)
    db.commit()
    return messages

@pytest.fixture
def sample_replace_words(db):
    words = [
        ReplaceWord(source_word="錯字1", target_word="正字1"),
        ReplaceWord(source_word="錯字2", target_word="正字2"),
    ]
    db.add_all(words)
    db.commit()
    return words

@pytest.fixture
def sample_special_words(db):
    words = [
        SpecialWord(word="特殊詞1"),
        SpecialWord(word="特殊詞2"),
    ]
    db.add_all(words)
    db.commit()
    return words

@pytest.fixture
def sample_pending_replace_words(db):
    words = [
        PendingReplaceWord(
            source_word=f"待審核{i}",
            target_word=f"目標{i}",
            confidence_score=0.9 - i * 0.1,
            occurrence_count=10 - i,
            status="pending"
        )
        for i in range(5)
    ]
    db.add_all(words)
    db.commit()
    return words

@pytest.fixture
def sample_pending_special_words(db):
    words = [
        PendingSpecialWord(
            word=f"待審特殊{i}",
            word_type="meme",
            confidence_score=0.9 - i * 0.1,
            occurrence_count=10 - i,
            status="pending"
        )
        for i in range(5)
    ]
    db.add_all(words)
    db.commit()
    return words

@pytest.fixture
def sample_currency_rates(db):
    rates = [
        CurrencyRate(currency="USD", rate_to_twd=31.5, notes="美元"),
        CurrencyRate(currency="JPY", rate_to_twd=0.21, notes="日圓"),
        CurrencyRate(currency="TWD", rate_to_twd=1.0, notes="台幣"),
    ]
    db.add_all(rates)
    db.commit()
    return rates
