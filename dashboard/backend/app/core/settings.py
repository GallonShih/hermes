import re
from typing import Optional
from sqlalchemy.orm import Session

from app.models import SystemSetting

def get_current_video_id(db: Session) -> Optional[str]:
    """從 system_settings 取得當前 video ID"""
    try:
        setting = db.query(SystemSetting).filter(
            SystemSetting.key == 'youtube_url'
        ).first()
        
        if setting and setting.value:
            match = re.search(r'(?:v=|/)([a-zA-Z0-9_-]{11})', setting.value)
            return match.group(1) if match else None
    except Exception:
        pass
    return None
