import re
from typing import Optional
from sqlalchemy.orm import Session

from app.models import SystemSetting

def get_video_id_from_url(url: str) -> Optional[str]:
    """從 YouTube URL 提取 video ID"""
    match = re.search(r'(?:v=|/)([a-zA-Z0-9_-]{11})', url)
    return match.group(1) if match else None


def get_current_video_id(db: Session) -> Optional[str]:
    """從 system_settings 取得當前 video ID"""
    try:
        setting = db.query(SystemSetting).filter(
            SystemSetting.key == 'youtube_url'
        ).first()

        if setting and setting.value:
            return get_video_id_from_url(setting.value)
    except Exception:
        pass
    return None
