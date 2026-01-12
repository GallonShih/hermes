import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import Base, ReplaceWord, SpecialWord, PendingReplaceWord, PendingSpecialWord
from app.services.validation import (
    validate_replace_word, 
    validate_special_word,
    batch_validate_replace_words,
    batch_validate_special_words
)

@pytest.fixture
def validation_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()

class TestValidateReplaceWord:
    def test_valid_replace_word(self, validation_db):
        result = validate_replace_word(validation_db, "錯字", "正字")
        assert result["valid"] == True
        assert result["conflicts"] == []
        assert result["warnings"] == []

    def test_same_source_and_target(self, validation_db):
        result = validate_replace_word(validation_db, "相同", "相同")
        assert result["valid"] == False
        assert any(c["type"] == "same_word" for c in result["conflicts"])

    def test_source_in_special_words(self, validation_db):
        validation_db.add(SpecialWord(word="特殊詞"))
        validation_db.commit()
        
        result = validate_replace_word(validation_db, "特殊詞", "目標")
        assert result["valid"] == False
        assert any(c["type"] == "source_in_special_words" for c in result["conflicts"])

    def test_source_in_target_words(self, validation_db):
        validation_db.add(ReplaceWord(source_word="原詞", target_word="中間詞"))
        validation_db.commit()
        
        result = validate_replace_word(validation_db, "中間詞", "最終詞")
        assert result["valid"] == False
        assert any(c["type"] == "source_in_target_words" for c in result["conflicts"])

    def test_source_already_exists_warning(self, validation_db):
        validation_db.add(ReplaceWord(source_word="錯字", target_word="舊正字"))
        validation_db.commit()
        
        result = validate_replace_word(validation_db, "錯字", "新正字")
        assert result["valid"] == True
        assert any(w["type"] == "source_already_exists" for w in result["warnings"])

    def test_target_in_special_words_warning(self, validation_db):
        validation_db.add(SpecialWord(word="目標詞"))
        validation_db.commit()
        
        result = validate_replace_word(validation_db, "錯字", "目標詞")
        assert result["valid"] == True
        assert any(w["type"] == "target_in_special_words" for w in result["warnings"])

    def test_duplicate_pending_warning(self, validation_db):
        validation_db.add(PendingReplaceWord(
            source_word="錯字", target_word="正字", status="pending"
        ))
        validation_db.commit()
        
        result = validate_replace_word(validation_db, "錯字", "正字")
        assert result["valid"] == True
        assert any(w["type"] == "duplicate_pending" for w in result["warnings"])

class TestValidateSpecialWord:
    def test_valid_special_word(self, validation_db):
        result = validate_special_word(validation_db, "新詞彙")
        assert result["valid"] == True
        assert result["conflicts"] == []

    def test_word_in_target_words(self, validation_db):
        validation_db.add(ReplaceWord(source_word="錯字", target_word="正字"))
        validation_db.commit()
        
        result = validate_special_word(validation_db, "正字")
        assert result["valid"] == False
        assert any(c["type"] == "word_in_target_words" for c in result["conflicts"])

    def test_word_in_source_words(self, validation_db):
        validation_db.add(ReplaceWord(source_word="錯字", target_word="正字"))
        validation_db.commit()
        
        result = validate_special_word(validation_db, "錯字")
        assert result["valid"] == False
        assert any(c["type"] == "word_in_source_words" for c in result["conflicts"])

    def test_word_already_exists_warning(self, validation_db):
        validation_db.add(SpecialWord(word="現有詞"))
        validation_db.commit()
        
        result = validate_special_word(validation_db, "現有詞")
        assert result["valid"] == True
        assert any(w["type"] == "word_already_exists" for w in result["warnings"])

class TestBatchValidation:
    def test_batch_validate_replace_words(self, validation_db):
        pending1 = PendingReplaceWord(source_word="錯1", target_word="正1", status="pending")
        pending2 = PendingReplaceWord(source_word="錯2", target_word="正2", status="pending")
        validation_db.add_all([pending1, pending2])
        validation_db.commit()
        
        results = batch_validate_replace_words(validation_db, [pending1.id, pending2.id])
        assert len(results) == 2
        assert results[pending1.id]["valid"] == True
        assert results[pending2.id]["valid"] == True

    def test_batch_validate_replace_words_not_found(self, validation_db):
        results = batch_validate_replace_words(validation_db, [999])
        assert results[999]["valid"] == False
        assert any(c["type"] == "not_found" for c in results[999]["conflicts"])

    def test_batch_validate_special_words(self, validation_db):
        pending1 = PendingSpecialWord(word="詞1", status="pending")
        pending2 = PendingSpecialWord(word="詞2", status="pending")
        validation_db.add_all([pending1, pending2])
        validation_db.commit()
        
        results = batch_validate_special_words(validation_db, [pending1.id, pending2.id])
        assert len(results) == 2
        assert results[pending1.id]["valid"] == True

    def test_batch_validate_special_words_not_found(self, validation_db):
        results = batch_validate_special_words(validation_db, [999])
        assert results[999]["valid"] == False
