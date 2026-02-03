import pytest
from app.models import SystemSetting
from app.core.settings import get_current_video_id


class TestGetCurrentVideoId:
    def test_returns_none_when_no_setting(self, db):
        result = get_current_video_id(db)
        assert result is None

    def test_returns_none_when_setting_has_no_value(self, db):
        db.add(SystemSetting(key='youtube_url', value=None))
        db.commit()
        
        result = get_current_video_id(db)
        assert result is None

    def test_extracts_video_id_from_full_url(self, db):
        db.add(SystemSetting(
            key='youtube_url',
            value='https://www.youtube.com/watch?v=H4X-DA9BMR0'
        ))
        db.commit()
        
        result = get_current_video_id(db)
        assert result == 'H4X-DA9BMR0'

    def test_extracts_video_id_from_short_url(self, db):
        db.add(SystemSetting(
            key='youtube_url',
            value='https://youtu.be/ABC123XYZ00'
        ))
        db.commit()
        
        result = get_current_video_id(db)
        assert result == 'ABC123XYZ00'

    def test_extracts_video_id_with_extra_params(self, db):
        db.add(SystemSetting(
            key='youtube_url',
            value='https://www.youtube.com/watch?v=TestId12345&list=PLxxx'
        ))
        db.commit()
        
        result = get_current_video_id(db)
        assert result == 'TestId12345'

    def test_returns_none_for_invalid_url(self, db):
        db.add(SystemSetting(
            key='youtube_url',
            value='not_a_valid_url'
        ))
        db.commit()
        
        result = get_current_video_id(db)
        assert result is None

    def test_ignores_other_settings(self, db):
        db.add(SystemSetting(key='other_key', value='some_value'))
        db.commit()
        
        result = get_current_video_id(db)
        assert result is None
