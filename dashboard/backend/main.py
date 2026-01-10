from fastapi import FastAPI, HTTPException, Depends, Body
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from database import get_db_session, get_db_manager
from models import (
    StreamStats, ChatMessage,
    PendingReplaceWord, PendingSpecialWord,
    ReplaceWord, SpecialWord, CurrencyRate
)
from validation import (
    validate_replace_word,
    validate_special_word,
    batch_validate_replace_words,
    batch_validate_special_words
)

import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta
from fastapi.middleware.cors import CORSMiddleware

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Hermes Dashboard API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development, allow all. In production, be more specific.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize DB
db_manager = get_db_manager()

# Startup event: Create tables automatically
@app.on_event("startup")
async def startup_event():
    """Create database tables on startup"""
    try:
        db_manager.create_tables()
        logger.info("✓ Database tables created/verified successfully")
    except Exception as e:
        logger.error(f"Error creating tables on startup: {e}")
        raise

def get_db():
    with get_db_session() as session:
        yield session

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/api/stats/viewers")
def get_viewer_stats(
    limit: int = 100, 
    hours: int = None, 
    start_time: datetime = None, 
    end_time: datetime = None, 
    db: Session = Depends(get_db)
):
    """
    Get recent concurrent viewer stats.
    Returns list of {time: str, count: int}
    """
    try:
        query = db.query(StreamStats).order_by(StreamStats.collected_at.desc())
        
        if start_time and end_time:
            query = query.filter(StreamStats.collected_at >= start_time, StreamStats.collected_at <= end_time)
        elif hours:
            since = datetime.utcnow() - timedelta(hours=hours)
            query = query.filter(StreamStats.collected_at >= since)
        else:
            query = query.limit(limit)
            
        stats = query.all()
        
        # Reverse to show chronological order
        result = []
        for s in reversed(stats):
            if s.concurrent_viewers is not None:
                result.append({
                    "time": s.collected_at.isoformat(), # Return ISO string for Chart.js parsing
                    "count": s.concurrent_viewers
                })
        return result
    except Exception as e:
        logger.error(f"Error fetching viewer stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stats/comments")
def get_comment_stats_hourly(
    hours: int = 24, 
    start_time: datetime = None, 
    end_time: datetime = None, 
    db: Session = Depends(get_db)
):
    """
    Get comment counts per hour.
    Returns list of {hour: str, count: int}
    """
    try:
        if start_time and end_time:
            since = start_time
            # For consistent filtering in the query below, we might need to handle end_time 
            # query logic is >= since. If using range, we need separate logic or adjust variable names.
            # Let's adjust the filtering logic below directly.
            pass 
        else:
            since = datetime.utcnow() - timedelta(hours=hours)
            start_time = since # use start_time as common variable for query filter start
            end_time = None # Open ended unless specified
        
        # Determine the database type to use appropriate date truncation function
        # Since we know it's Postgres from requirements and docker-compose
        trunc_func = func.date_trunc('hour', ChatMessage.published_at)
        
        # Query
        query = db.query(
            trunc_func.label('hour'),
            func.count(ChatMessage.message_id).label('count')
        ).filter(
            ChatMessage.published_at >= start_time
        )
        
        if end_time:
             query = query.filter(ChatMessage.published_at <= end_time)
             
        results = query.group_by(
            trunc_func
        ).order_by(
            trunc_func
        ).all()
        
        data = []
        for r in results:
            # Shift to local time if needed? keeping UTC for simplicity or adding +8 for Taipei?
            # User is likely in Taipei (+8). Ideally frontend handles timezone, but backend sending ISO string is best.
            # Here we just format as string.
            dt = r.hour
            # Simple conversion to +8 for display consistency with user context if desired, 
            # but standard is to return ISO and let frontend format. 
            # However, user's React example used `d.hour`.
            # Let's return full ISO string for the frontend to format.
            data.append({
                "hour": dt.isoformat(), 
                "count": r.count
            })
            
        return data
    except Exception as e:
        logger.error(f"Error fetching comment stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/chat/messages")
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
    """
    Get chat messages with pagination and optional filtering.
    Returns messages in descending order (newest first).
    
    Args:
        limit: Number of messages to return (max 500)
        offset: Pagination offset
        start_time: Filter messages from this time onwards (UTC)
        end_time: Filter messages up to this time (UTC)
        author_filter: Filter by author name (case-insensitive, fuzzy match)
        message_filter: Filter by message content (case-insensitive, fuzzy match)
        paid_message_filter: Filter by payment type ('all', 'paid_only', 'non_paid_only')
    
    Returns:
        {
            "messages": [...],
            "total": int,
            "limit": int,
            "offset": int
        }
    """
    try:
        # Enforce max limit
        if limit > 500:
            limit = 500
        
        # Base query
        query = db.query(ChatMessage).order_by(ChatMessage.published_at.desc())
        
        # Apply time filters
        if start_time:
            query = query.filter(ChatMessage.published_at >= start_time)
        if end_time:
            query = query.filter(ChatMessage.published_at <= end_time)
        
        # Apply author filter (case-insensitive fuzzy match)
        if author_filter:
            query = query.filter(ChatMessage.author_name.ilike(f'%{author_filter}%'))
        
        # Apply message filter (case-insensitive fuzzy match, supports emoji)
        if message_filter:
            query = query.filter(ChatMessage.message.ilike(f'%{message_filter}%'))
        
        # Apply paid message filter
        if paid_message_filter == 'paid_only':
            query = query.filter(ChatMessage.message_type == 'paid_message')
        elif paid_message_filter == 'non_paid_only':
            query = query.filter(ChatMessage.message_type != 'paid_message')
        
        # Get total count for pagination (before limit/offset)
        total = query.count()
        
        # Apply pagination
        messages = query.limit(limit).offset(offset).all()
        
        # Format response
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

# ============================================
# Admin API Endpoints for Word Review System
# ============================================

@app.get("/api/admin/pending-replace-words")
def get_pending_replace_words(
    status: str = 'pending',
    limit: int = 50,
    offset: int = 0,
    sort_by: str = 'confidence',
    order: str = 'desc',
    source_word_filter: str = '',
    target_word_filter: str = '',
    db: Session = Depends(get_db)
):
    """
    獲取待審核的替換詞彙列表
    
    Args:
        status: 狀態篩選 (pending/approved/rejected)
        limit: 每頁數量
        offset: 分頁偏移
        sort_by: 排序欄位 (confidence/occurrence/discovered_at)
        order: 排序方向 (asc/desc)
        source_word_filter: Source word 搜尋過濾
        target_word_filter: Target word 搜尋過濾
    """
    try:
        # Base query
        query = db.query(PendingReplaceWord).filter(
            PendingReplaceWord.status == status
        )
        
        # Apply search filters
        if source_word_filter:
            query = query.filter(PendingReplaceWord.source_word.ilike(f'%{source_word_filter}%'))
        if target_word_filter:
            query = query.filter(PendingReplaceWord.target_word.ilike(f'%{target_word_filter}%'))
        
        # Sorting
        if sort_by == 'confidence':
            order_col = PendingReplaceWord.confidence_score
        elif sort_by == 'occurrence':
            order_col = PendingReplaceWord.occurrence_count
        else:  # discovered_at
            order_col = PendingReplaceWord.discovered_at
        
        if order == 'asc':
            query = query.order_by(order_col.asc())
        else:
            query = query.order_by(order_col.desc())
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        items = query.limit(limit).offset(offset).all()
        
        # Format response
        result = {
            "items": [
                {
                    "id": item.id,
                    "source_word": item.source_word,
                    "target_word": item.target_word,
                    "confidence_score": float(item.confidence_score) if item.confidence_score else None,
                    "occurrence_count": item.occurrence_count,
                    "example_messages": item.example_messages if item.example_messages else [],
                    "discovered_at": item.discovered_at.isoformat() if item.discovered_at else None,
                    "status": item.status,
                    "reviewed_at": item.reviewed_at.isoformat() if item.reviewed_at else None,
                    "reviewed_by": item.reviewed_by,
                    "notes": item.notes
                }
                for item in items
            ],
            "total": total,
            "limit": limit,
            "offset": offset
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Error fetching pending replace words: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/admin/pending-special-words")
def get_pending_special_words(
    status: str = 'pending',
    limit: int = 50,
    offset: int = 0,
    sort_by: str = 'confidence',
    order: str = 'desc',
    word_filter: str = '',
    db: Session = Depends(get_db)
):
    """
    獲取待審核的特殊詞彙列表
    
    Args:
        status: 狀態篩選 (pending/approved/rejected)
        limit: 每頁數量
        offset: 分頁偏移
        sort_by: 排序欄位 (confidence/occurrence/discovered_at)
        order: 排序方向 (asc/desc)
        word_filter: Word 搜尋過濾
    """
    try:
        # Base query
        query = db.query(PendingSpecialWord).filter(
            PendingSpecialWord.status == status
        )
        
        # Apply search filter
        if word_filter:
            query = query.filter(PendingSpecialWord.word.ilike(f'%{word_filter}%'))
        
        # Sorting
        if sort_by == 'confidence':
            order_col = PendingSpecialWord.confidence_score
        elif sort_by == 'occurrence':
            order_col = PendingSpecialWord.occurrence_count
        else:  # discovered_at
            order_col = PendingSpecialWord.discovered_at
        
        if order == 'asc':
            query = query.order_by(order_col.asc())
        else:
            query = query.order_by(order_col.desc())
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        items = query.limit(limit).offset(offset).all()
        
        # Format response
        result = {
            "items": [
                {
                    "id": item.id,
                    "word": item.word,
                    "word_type": item.word_type,
                    "confidence_score": float(item.confidence_score) if item.confidence_score else None,
                    "occurrence_count": item.occurrence_count,
                    "example_messages": item.example_messages if item.example_messages else [],
                    "discovered_at": item.discovered_at.isoformat() if item.discovered_at else None,
                    "status": item.status,
                    "reviewed_at": item.reviewed_at.isoformat() if item.reviewed_at else None,
                    "reviewed_by": item.reviewed_by,
                    "notes": item.notes
                }
                for item in items
            ],
            "total": total,
            "limit": limit,
            "offset": offset
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Error fetching pending special words: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/admin/validate-replace-word")
def validate_pending_replace_word(
    source_word: str = Body(...),
    target_word: str = Body(...),
    pending_id: int = Body(None),
    db: Session = Depends(get_db)
):
    """
    驗證替換詞彙是否有衝突
    """
    try:
        validation_result = validate_replace_word(
            db, source_word, target_word, pending_id
        )
        return validation_result
    except Exception as e:
        logger.error(f"Error validating replace word: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/admin/validate-special-word")
def validate_pending_special_word(
    word: str = Body(...),
    pending_id: int = Body(None),
    db: Session = Depends(get_db)
):
    """
    驗證特殊詞彙是否有衝突
    """
    try:
        validation_result = validate_special_word(
            db, word, pending_id
        )
        return validation_result
    except Exception as e:
        logger.error(f"Error validating special word: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/admin/approve-replace-word/{word_id}")
def approve_replace_word(
    word_id: int,
    reviewed_by: str = Body('admin'),
    notes: str = Body(''),
    db: Session = Depends(get_db)
):
    """
    批准替換詞彙並移至正式表
    """
    try:
        # Get pending word
        pending = db.query(PendingReplaceWord).filter(
            PendingReplaceWord.id == word_id
        ).first()
        
        if not pending:
            raise HTTPException(status_code=404, detail=f"找不到 ID 為 {word_id} 的待審核詞彙")
        
        # Validate
        validation = validate_replace_word(
            db, pending.source_word, pending.target_word, word_id
        )
        
        if not validation['valid']:
            return {
                "success": False,
                "message": "驗證失敗，存在衝突",
                "validation": validation
            }
        
        # Update pending word status
        pending.status = 'approved'
        pending.reviewed_at = func.now()
        pending.reviewed_by = reviewed_by
        pending.notes = notes
        
        # Insert or update in replace_words table (UPSERT)
        existing = db.query(ReplaceWord).filter(
            ReplaceWord.source_word == pending.source_word
        ).first()
        
        if existing:
            # Update existing
            existing.target_word = pending.target_word
            existing.updated_at = func.now()
        else:
            # Insert new
            new_word = ReplaceWord(
                source_word=pending.source_word,
                target_word=pending.target_word
            )
            db.add(new_word)
        
        db.commit()
        
        return {
            "success": True,
            "message": "替換詞彙已批准並加入正式表",
            "word": {
                "source_word": pending.source_word,
                "target_word": pending.target_word
            },
            "validation": validation
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error approving replace word: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/admin/approve-special-word/{word_id}")
def approve_special_word(
    word_id: int,
    reviewed_by: str = Body('admin'),
    notes: str = Body(''),
    db: Session = Depends(get_db)
):
    """
    批准特殊詞彙並移至正式表
    """
    try:
        # Get pending word
        pending = db.query(PendingSpecialWord).filter(
            PendingSpecialWord.id == word_id
        ).first()
        
        if not pending:
            raise HTTPException(status_code=404, detail=f"找不到 ID 為 {word_id} 的待審核詞彙")
        
        # Validate
        validation = validate_special_word(db, pending.word, word_id)
        
        if not validation['valid']:
            return {
                "success": False,
                "message": "驗證失敗，存在衝突",
                "validation": validation
            }
        
        # Update pending word status
        pending.status = 'approved'
        pending.reviewed_at = func.now()
        pending.reviewed_by = reviewed_by
        pending.notes = notes
        
        # Insert in special_words table (ignore if exists)
        existing = db.query(SpecialWord).filter(
            SpecialWord.word == pending.word
        ).first()
        
        if not existing:
            new_word = SpecialWord(word=pending.word)
            db.add(new_word)
        
        db.commit()
        
        return {
            "success": True,
            "message": "特殊詞彙已批准並加入正式表",
            "word": {
                "word": pending.word,
                "type": pending.word_type
            },
            "validation": validation
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error approving special word: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/admin/reject-replace-word/{word_id}")
def reject_replace_word(
    word_id: int,
    reviewed_by: str = Body('admin'),
    notes: str = Body(''),
    db: Session = Depends(get_db)
):
    """
    否決替換詞彙
    """
    try:
        # Get pending word
        pending = db.query(PendingReplaceWord).filter(
            PendingReplaceWord.id == word_id
        ).first()
        
        if not pending:
            raise HTTPException(status_code=404, detail=f"找不到 ID 為 {word_id} 的待審核詞彙")
        
        # Update status
        pending.status = 'rejected'
        pending.reviewed_at = func.now()
        pending.reviewed_by = reviewed_by
        pending.notes = notes
        
        db.commit()
        
        return {
            "success": True,
            "message": "替換詞彙已否決",
            "word": {
                "source_word": pending.source_word,
                "target_word": pending.target_word
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error rejecting replace word: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/admin/reject-special-word/{word_id}")
def reject_special_word(
    word_id: int,
    reviewed_by: str = Body('admin'),
    notes: str = Body(''),
    db: Session = Depends(get_db)
):
    """
    否決特殊詞彙
    """
    try:
        # Get pending word
        pending = db.query(PendingSpecialWord).filter(
            PendingSpecialWord.id == word_id
        ).first()
        
        if not pending:
            raise HTTPException(status_code=404, detail=f"找不到 ID 為 {word_id} 的待審核詞彙")
        
        # Update status
        pending.status = 'rejected'
        pending.reviewed_at = func.now()
        pending.reviewed_by = reviewed_by
        pending.notes = notes
        
        db.commit()
        
        return {
            "success": True,
            "message": "特殊詞彙已否決",
            "word": {
                "word": pending.word
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error rejecting special word: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/admin/batch-approve-replace-words")
def batch_approve_replace_words(
    ids: List[int] = Body(...),
    reviewed_by: str = Body('admin'),
    notes: str = Body(''),
    db: Session = Depends(get_db)
):
    """
    批量批准替換詞彙
    """
    try:
        # Validate all words first
        validations = batch_validate_replace_words(db, ids)
        
        approved = 0
        failed = 0
        errors = []
        
        for word_id in ids:
            validation = validations.get(word_id, {})
            
            if not validation.get('valid', False):
                failed += 1
                errors.append({
                    "id": word_id,
                    "error": "驗證失敗: " + str(validation.get('conflicts', []))
                })
                continue
            
            # Get and approve
            pending = db.query(PendingReplaceWord).filter(
                PendingReplaceWord.id == word_id
            ).first()
            
            if not pending:
                failed += 1
                errors.append({
                    "id": word_id,
                    "error": "找不到待審核詞彙"
                })
                continue
            
            # Update pending status
            pending.status = 'approved'
            pending.reviewed_at = func.now()
            pending.reviewed_by = reviewed_by
            pending.notes = notes
            
            # Insert or update in replace_words
            existing = db.query(ReplaceWord).filter(
                ReplaceWord.source_word == pending.source_word
            ).first()
            
            if existing:
                existing.target_word = pending.target_word
                existing.updated_at = func.now()
            else:
                new_word = ReplaceWord(
                    source_word=pending.source_word,
                    target_word=pending.target_word
                )
                db.add(new_word)
            
            approved += 1
        
        db.commit()
        
        return {
            "success": True,
            "approved": approved,
            "failed": failed,
            "errors": errors
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error batch approving replace words: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/admin/batch-reject-replace-words")
def batch_reject_replace_words(
    ids: List[int] = Body(...),
    reviewed_by: str = Body('admin'),
    notes: str = Body(''),
    db: Session = Depends(get_db)
):
    """
    批量否決替換詞彙
    """
    try:
        rejected = 0
        failed = 0
        errors = []
        
        for word_id in ids:
            pending = db.query(PendingReplaceWord).filter(
                PendingReplaceWord.id == word_id
            ).first()
            
            if not pending:
                failed += 1
                errors.append({
                    "id": word_id,
                    "error": "找不到待審核詞彙"
                })
                continue
            
            pending.status = 'rejected'
            pending.reviewed_at = func.now()
            pending.reviewed_by = reviewed_by
            pending.notes = notes
            rejected += 1
        
        db.commit()
        
        return {
            "success": True,
            "rejected": rejected,
            "failed": failed,
            "errors": errors
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error batch rejecting replace words: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/admin/statistics")
def get_admin_statistics(db: Session = Depends(get_db)):
    """
    獲取統計資訊
    """
    try:
        # Pending counts
        pending_replace = db.query(PendingReplaceWord).filter(
            PendingReplaceWord.status == 'pending'
        ).count()
        
        pending_special = db.query(PendingSpecialWord).filter(
            PendingSpecialWord.status == 'pending'
        ).count()
        
        # Today's approved/rejected counts
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        approved_replace_today = db.query(PendingReplaceWord).filter(
            PendingReplaceWord.status == 'approved',
            PendingReplaceWord.reviewed_at >= today_start
        ).count()
        
        approved_special_today = db.query(PendingSpecialWord).filter(
            PendingSpecialWord.status == 'approved',
            PendingSpecialWord.reviewed_at >= today_start
        ).count()
        
        rejected_replace_today = db.query(PendingReplaceWord).filter(
            PendingReplaceWord.status == 'rejected',
            PendingReplaceWord.reviewed_at >= today_start
        ).count()
        
        rejected_special_today = db.query(PendingSpecialWord).filter(
            PendingSpecialWord.status == 'rejected',
            PendingSpecialWord.reviewed_at >= today_start
        ).count()
        
        # Total counts in official tables
        total_replace = db.query(ReplaceWord).count()
        total_special = db.query(SpecialWord).count()
        
        return {
            "pending_replace_words": pending_replace,
            "pending_special_words": pending_special,
            "approved_replace_words_today": approved_replace_today,
            "approved_special_words_today": approved_special_today,
            "rejected_replace_words_today": rejected_replace_today,
            "rejected_special_words_today": rejected_special_today,
            "total_replace_words": total_replace,
            "total_special_words": total_special
        }
        
    except Exception as e:
        logger.error(f"Error fetching statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/admin/batch-approve-special-words")
def batch_approve_special_words(
    ids: List[int] = Body(...),
    reviewed_by: str = Body('admin'),
    notes: str = Body(''),
    db: Session = Depends(get_db)
):
    """
    批量批准特殊詞彙
    """
    try:
        # Validate all words first
        validations = batch_validate_special_words(db, ids)
        
        approved = 0
        failed = 0
        errors = []
        
        for word_id in ids:
            validation = validations.get(word_id, {})
            
            if not validation.get('valid', False):
                failed += 1
                errors.append({
                    "id": word_id,
                    "error": "驗證失敗: " + str(validation.get('conflicts', []))
                })
                continue
            
            # Get and approve
            pending = db.query(PendingSpecialWord).filter(
                PendingSpecialWord.id == word_id
            ).first()
            
            if not pending:
                failed += 1
                errors.append({
                    "id": word_id,
                    "error": "找不到待審核詞彙"
                })
                continue
            
            # Update pending status
            pending.status = 'approved'
            pending.reviewed_at = func.now()
            pending.reviewed_by = reviewed_by
            pending.notes = notes
            
            # Insert in special_words (ignore if exists)
            existing = db.query(SpecialWord).filter(
                SpecialWord.word == pending.word
            ).first()
            
            if not existing:
                new_word = SpecialWord(word=pending.word)
                db.add(new_word)
            
            approved += 1
        
        db.commit()
        
        return {
            "success": True,
            "approved": approved,
            "failed": failed,
            "errors": errors
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error batch approving special words: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/admin/batch-reject-special-words")
def batch_reject_special_words(
    ids: List[int] = Body(...),
    reviewed_by: str = Body('admin'),
    notes: str = Body(''),
    db: Session = Depends(get_db)
):
    """
    批量否決特殊詞彙
    """
    try:
        rejected = 0
        failed = 0
        errors = []
        
        for word_id in ids:
            pending = db.query(PendingSpecialWord).filter(
                PendingSpecialWord.id == word_id
            ).first()
            
            if not pending:
                failed += 1
                errors.append({
                    "id": word_id,
                    "error": "找不到待審核詞彙"
                })
                continue
            
            pending.status = 'rejected'
            pending.reviewed_at = func.now()
            pending.reviewed_by = reviewed_by
            pending.notes = notes
            rejected += 1
        
        db.commit()
        
        return {
            "success": True,
            "rejected": rejected,
            "failed": failed,
            "errors": errors
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error batch rejecting special words: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/admin/add-replace-word")
def add_replace_word(
    source_word: str = Body(...),
    target_word: str = Body(...),
    db: Session = Depends(get_db)
):
    """
    手動新增替換詞彙至正式詞庫
    Manually add a new replace word directly to the official table
    """
    try:
        # Validate before adding
        validation_result = validate_replace_word(
            db, source_word, target_word, pending_id=None
        )
        
        if not validation_result['valid']:
            return {
                "success": False,
                "message": "Validation failed",
                "conflicts": validation_result['conflicts']
            }
        
        # Check if already exists
        existing = db.query(ReplaceWord).filter(
            ReplaceWord.source_word == source_word,
            ReplaceWord.target_word == target_word
        ).first()
        
        if existing:
            return {
                "success": False,
                "message": "Replace word already exists"
            }
        
        # Add to official table
        new_word = ReplaceWord(
            source_word=source_word,
            target_word=target_word
        )
        db.add(new_word)
        db.commit()
        db.refresh(new_word)
        
        logger.info(f"Manually added replace word: {source_word} -> {target_word}")
        return {
            "success": True,
            "message": "Replace word added successfully",
            "word": {
                "id": new_word.id,
                "source_word": new_word.source_word,
                "target_word": new_word.target_word
            }
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error adding replace word: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/admin/add-special-word")
def add_special_word(
    word: str = Body(..., embed=True),
    db: Session = Depends(get_db)
):
    """
    手動新增特殊詞彙至正式詞庫
    Manually add a new special word directly to the official table
    """
    try:
        # Validate before adding
        validation_result = validate_special_word(db, word, pending_id=None)
        
        if not validation_result['valid']:
            return {
                "success": False,
                "message": "Validation failed",
                "conflicts": validation_result['conflicts']
            }
        
        # Check if already exists
        existing = db.query(SpecialWord).filter(
            SpecialWord.word == word
        ).first()
        
        if existing:
            return {
                "success": False,
                "message": "Special word already exists"
            }
        
        # Add to official table
        new_word = SpecialWord(
            word=word
        )
        db.add(new_word)
        db.commit()
        db.refresh(new_word)
        
        logger.info(f"Manually added special word: {word}")
        return {
            "success": True,
            "message": "Special word added successfully",
            "word": {
                "id": new_word.id,
                "word": new_word.word
            }
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error adding special word: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Currency Rate Management API Endpoints
# ============================================

@app.get("/api/admin/currency-rates")
def get_currency_rates(db: Session = Depends(get_db)):
    """
    獲取所有已設定的匯率
    """
    try:
        rates = db.query(CurrencyRate).order_by(CurrencyRate.currency).all()
        
        return {
            "rates": [
                {
                    "currency": rate.currency,
                    "rate_to_twd": float(rate.rate_to_twd) if rate.rate_to_twd else 0.0,
                    "updated_at": rate.updated_at.isoformat() if rate.updated_at else None,
                    "notes": rate.notes
                }
                for rate in rates
            ]
        }
    except Exception as e:
        logger.error(f"Error fetching currency rates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/admin/currency-rates")
def upsert_currency_rate(
    currency: str = Body(...),
    rate_to_twd: float = Body(...),
    notes: str = Body(''),
    db: Session = Depends(get_db)
):
    """
    新增或更新匯率
    """
    try:
        # Validate inputs
        if not currency or len(currency) > 10:
            raise HTTPException(status_code=400, detail="Invalid currency code")
        
        if rate_to_twd < 0:
            raise HTTPException(status_code=400, detail="Exchange rate must be non-negative")
        
        # Convert to uppercase for consistency
        currency = currency.upper().strip()
        
        # Check if exists
        existing = db.query(CurrencyRate).filter(
            CurrencyRate.currency == currency
        ).first()
        
        if existing:
            # Update
            existing.rate_to_twd = rate_to_twd
            existing.notes = notes
            existing.updated_at = func.now()
            message = f"Currency rate for {currency} updated successfully"
        else:
            # Insert
            new_rate = CurrencyRate(
                currency=currency,
                rate_to_twd=rate_to_twd,
                notes=notes
            )
            db.add(new_rate)
            message = f"Currency rate for {currency} added successfully"
        
        db.commit()
        
        return {
            "success": True,
            "message": message,
            "currency": currency,
            "rate_to_twd": rate_to_twd
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error upserting currency rate: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/admin/currency-rates/unknown")
def get_unknown_currencies(db: Session = Depends(get_db)):
    """
    列出資料庫中有出現但尚未設定匯率的幣別
    """
    try:
        # Get all currencies from chat_messages
        result = db.execute(text("""
            SELECT DISTINCT raw_data->'money'->>'currency' as currency,
                   COUNT(*) as message_count
            FROM chat_messages
            WHERE raw_data->'money' IS NOT NULL
              AND raw_data->'money'->>'currency' IS NOT NULL
            GROUP BY currency
            ORDER BY message_count DESC
        """))
        
        all_currencies = [(row[0], row[1]) for row in result if row[0]]
        
        # Get currencies that already have rates
        existing_rates = db.query(CurrencyRate.currency).all()
        existing_currency_set = {rate[0] for rate in existing_rates}
        
        # Filter out currencies that already have rates
        unknown = [
            {
                "currency": curr,
                "message_count": count
            }
            for curr, count in all_currencies
            if curr not in existing_currency_set
        ]
        
        return {
            "unknown_currencies": unknown,
            "total": len(unknown)
        }
        
    except Exception as e:
        logger.error(f"Error fetching unknown currencies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Money Summary Statistics API
# ============================================

@app.get("/api/stats/money-summary")
def get_money_summary(
    start_time: datetime = None,
    end_time: datetime = None,
    db: Session = Depends(get_db)
):
    """
    計算指定時間範圍內的金額統計
    
    Args:
        start_time: 開始時間 (UTC)
        end_time: 結束時間 (UTC)
    
    Returns:
        total_amount_twd: 總金額（台幣）
        paid_message_count: 付費訊息數量
        top_authors: 前 5 名作者及其金額
        unknown_currencies: 無法轉換的幣別列表
    """
    try:
        # Query paid messages
        query = db.query(ChatMessage).filter(
            ChatMessage.message_type == 'paid_message'
        )
        
        # Apply time filters
        if start_time:
            query = query.filter(ChatMessage.published_at >= start_time)
        if end_time:
            query = query.filter(ChatMessage.published_at <= end_time)
        
        messages = query.all()
        
        # Get all currency rates
        rates_query = db.query(CurrencyRate).all()
        rate_map = {rate.currency: float(rate.rate_to_twd) if rate.rate_to_twd else 0.0 for rate in rates_query}
        
        # Calculate statistics
        total_twd = 0.0
        author_amounts = {}  # {author_name: {'amount_twd': float, 'count': int}}
        unknown_currencies = set()
        paid_count = 0
        
        for msg in messages:
            if not msg.raw_data or 'money' not in msg.raw_data:
                continue
            
            money_data = msg.raw_data.get('money')
            if not money_data:
                continue
            
            currency = money_data.get('currency')
            amount_str = money_data.get('amount')
            
            # Skip if no currency or amount
            if not currency or not amount_str:
                continue
            
            # Parse amount (handle different formats)
            try:
                # Remove common currency symbols and commas
                amount_str = str(amount_str).replace(',', '').replace('$', '').strip()
                amount = float(amount_str)
            except (ValueError, TypeError):
                logger.warning(f"Could not parse amount: {amount_str}")
                continue
            
            # Convert to TWD
            if currency in rate_map:
                amount_twd = amount * rate_map[currency]
                total_twd += amount_twd
                
                # Track by author
                author = msg.author_name or 'Unknown'
                if author not in author_amounts:
                    author_amounts[author] = {'amount_twd': 0.0, 'count': 0}
                
                author_amounts[author]['amount_twd'] += amount_twd
                author_amounts[author]['count'] += 1
                paid_count += 1
            else:
                # Unknown currency
                unknown_currencies.add(currency)
        
        # Get top 5 authors, but include ties
        # Sort authors by amount descending
        sorted_authors = sorted(
            [
                {
                    'author': author,
                    'amount_twd': round(data['amount_twd'], 2),
                    'message_count': data['count']
                }
                for author, data in author_amounts.items()
            ],
            key=lambda x: x['amount_twd'],
            reverse=True
        )
        
        # If we have more than 5, check for ties at the 5th position
        if len(sorted_authors) > 5:
            fifth_amount = sorted_authors[4]['amount_twd']
            # Include all authors with amount >= 5th place amount
            top_authors = [a for a in sorted_authors if a['amount_twd'] >= fifth_amount]
        else:
            top_authors = sorted_authors

        
        return {
            "total_amount_twd": round(total_twd, 2),
            "paid_message_count": paid_count,
            "top_authors": top_authors,
            "unknown_currencies": list(unknown_currencies)
        }
        
    except Exception as e:
        logger.error(f"Error calculating money summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


