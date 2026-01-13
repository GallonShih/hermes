import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import Base, SystemSetting
from app.core.settings import get_current_video_id

@pytest.fixture
def settings_db():
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

class TestGetCurrentVideoId:
    def test_returns_none_when_no_setting(self, settings_db):
        result = get_current_video_id(settings_db)
        assert result is None

    def test_returns_none_when_setting_has_no_value(self, settings_db):
        settings_db.add(SystemSetting(key='youtube_url', value=None))
        settings_db.commit()
        
        result = get_current_video_id(settings_db)
        assert result is None

    def test_extracts_video_id_from_full_url(self, settings_db):
        settings_db.add(SystemSetting(
            key='youtube_url',
            value='https://www.youtube.com/watch?v=H4X-DA9BMR0'
        ))
        settings_db.commit()
        
        result = get_current_video_id(settings_db)
        assert result == 'H4X-DA9BMR0'

    def test_extracts_video_id_from_short_url(self, settings_db):
        settings_db.add(SystemSetting(
            key='youtube_url',
            value='https://youtu.be/ABC123XYZ00'
        ))
        settings_db.commit()
        
        result = get_current_video_id(settings_db)
        assert result == 'ABC123XYZ00'

    def test_extracts_video_id_with_extra_params(self, settings_db):
        settings_db.add(SystemSetting(
            key='youtube_url',
            value='https://www.youtube.com/watch?v=TestId12345&list=PLxxx'
        ))
        settings_db.commit()
        
        result = get_current_video_id(settings_db)
        assert result == 'TestId12345'

    def test_returns_none_for_invalid_url(self, settings_db):
        settings_db.add(SystemSetting(
            key='youtube_url',
            value='not_a_valid_url'
        ))
        settings_db.commit()
        
        result = get_current_video_id(settings_db)
        assert result is None

    def test_ignores_other_settings(self, settings_db):
        settings_db.add(SystemSetting(key='other_key', value='some_value'))
        settings_db.commit()
        
        result = get_current_video_id(settings_db)
        assert result is None
