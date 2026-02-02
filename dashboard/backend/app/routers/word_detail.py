from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel
from typing import List, Optional
import logging

from app.core.database import get_db
from app.models import ChatMessage

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin", tags=["admin-word-detail"])


class MessageOccurrence(BaseModel):
    """Single message occurrence."""
    author: str
    published_at: datetime
    message: str


class WordOccurrenceResponse(BaseModel):
    """Response for word occurrence endpoint."""
    word: str
    total_occurrences: int
    messages: List[MessageOccurrence]
    text_mining_available: bool
    seven_day_start: Optional[datetime]
    seven_day_end: Optional[datetime]


@router.get("/word-occurrences", response_model=WordOccurrenceResponse)
def get_word_occurrences(
    word: str = Query(..., description="Word to search for"),
    limit: int = Query(10, ge=1, le=100, description="Number of messages to return"),
    word_type: Optional[str] = Query(None, description="Type of word: 'replace' or 'special'"),
    db: Session = Depends(get_db)
):
    """
    Get recent messages containing a specific word.
    
    Returns the most recent messages (up to limit) that contain the word,
    along with metadata about text mining availability.
    """
    try:
        # Search for messages containing the word (case-insensitive)
        # Using ILIKE for case-insensitive search
        query = db.query(ChatMessage).filter(
            ChatMessage.message.ilike(f"%{word}%")
        ).order_by(ChatMessage.published_at.desc())
        
        # Get total count
        total_count = query.count()
        
        # Get limited messages
        messages = query.limit(limit).all()
        
        # Prepare message occurrences
        message_occurrences = [
            MessageOccurrence(
                author=msg.author_name,
                published_at=msg.published_at,
                message=msg.message
            )
            for msg in messages
        ]
        
        # Calculate 7-day range for text mining
        # Use the current time as the end of the range
        now = datetime.now(tz=timezone.utc)
        seven_day_start = now - timedelta(days=7)
        seven_day_end = now
        
        # Check if there are any messages in the 7-day range
        text_mining_query = db.query(ChatMessage).filter(
            ChatMessage.message.ilike(f"%{word}%"),
            ChatMessage.published_at >= seven_day_start,
            ChatMessage.published_at <= seven_day_end
        )
        text_mining_count = text_mining_query.count()
        text_mining_available = text_mining_count > 0
        
        logger.info(
            f"Word occurrence query for '{word}': "
            f"total={total_count}, returned={len(messages)}, "
            f"7-day count={text_mining_count}"
        )
        
        return WordOccurrenceResponse(
            word=word,
            total_occurrences=total_count,
            messages=message_occurrences,
            text_mining_available=text_mining_available,
            seven_day_start=seven_day_start if text_mining_available else None,
            seven_day_end=seven_day_end if text_mining_available else None
        )
        
    except Exception as e:
        logger.error(f"Error fetching word occurrences for '{word}': {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch word occurrences: {str(e)}")
