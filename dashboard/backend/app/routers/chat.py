from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime
import logging

from app.core.database import get_db
from app.models import ChatMessage

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["chat"])

@router.get("/messages")
def get_chat_messages(
    limit: int = 100,
    offset: int = 0,
    start_time: datetime = None,
    end_time: datetime = None,
    author_filter: str = None,
    message_filter: str = None,
    paid_message_filter: str = 'all',
    db: Session = Depends(get_db)
):
    try:
        if limit > 500:
            limit = 500
        
        query = db.query(ChatMessage).order_by(ChatMessage.published_at.desc())
        
        if start_time:
            query = query.filter(ChatMessage.published_at >= start_time)
        if end_time:
            query = query.filter(ChatMessage.published_at <= end_time)
        
        if author_filter:
            query = query.filter(ChatMessage.author_name.ilike(f'%{author_filter}%'))
        
        if message_filter:
            query = query.filter(ChatMessage.message.ilike(f'%{message_filter}%'))
        
        if paid_message_filter == 'paid_only':
            query = query.filter(ChatMessage.message_type == 'paid_message')
        elif paid_message_filter == 'non_paid_only':
            query = query.filter(ChatMessage.message_type != 'paid_message')
        
        total = query.count()
        
        messages = query.limit(limit).offset(offset).all()
        
        result = {
            "messages": [
                {
                    "id": msg.message_id,
                    "time": msg.published_at.isoformat() if msg.published_at else None,
                    "author": msg.author_name,
                    "message": msg.message,
                    "emotes": msg.emotes if msg.emotes else [],
                    "message_type": msg.message_type,
                    "money": msg.raw_data.get('money') if msg.raw_data else None
                }
                for msg in messages
            ],
            "total": total,
            "limit": limit,
            "offset": offset
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Error fetching chat messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))
