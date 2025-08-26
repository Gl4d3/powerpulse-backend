"""
API endpoints for retrieving and searching individual conversations and their
CSI (Customer Satisfaction Index) data.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc
from typing import Optional
from datetime import date, datetime
import logging

from database import get_db
from models import Conversation, Message
from schemas import ConversationListResponse, ConversationResponse
from config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/conversations", response_model=ConversationListResponse)
async def get_conversations(
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=settings.DEFAULT_PAGE_SIZE, ge=1, le=settings.MAX_PAGE_SIZE),
    sort_by: str = Query(default="updated_at", pattern="^(updated_at|csi_score|avg_sentiment|total_messages)$"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    min_csi_score: Optional[float] = Query(default=None, ge=1, le=10),
    max_csi_score: Optional[float] = Query(default=None, ge=1, le=10),
    start_date: Optional[date] = Query(None, description="Start date for filtering (ISO 8601 format: YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date for filtering (ISO 8601 format: YYYY-MM-DD)")
):
    """
    Get a paginated list of conversations with their CSI scores and metadata.
    Supports filtering by CSI score and date, and sorting.
    """
    try:
        query = db.query(Conversation)
        
        # Apply filters
        if min_csi_score is not None:
            query = query.filter(Conversation.csi_score >= min_csi_score)
        
        if max_csi_score is not None:
            query = query.filter(Conversation.csi_score <= max_csi_score)
        
        if start_date:
            query = query.filter(Conversation.first_message_time >= datetime.combine(start_date, datetime.min.time()))
        
        if end_date:
            query = query.filter(Conversation.last_message_time <= datetime.combine(end_date, datetime.max.time()))
        
        total = query.count()
        
        # Apply sorting
        sort_column = getattr(Conversation, sort_by)
        query = query.order_by(desc(sort_column) if sort_order == "desc" else asc(sort_column))
        
        # Apply pagination
        conversations = query.offset((page - 1) * page_size).limit(page_size).all()
        
        return ConversationListResponse(
            conversations=[ConversationResponse.from_orm(conv) for conv in conversations],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size
        )
        
    except Exception as e:
        logger.error(f"Error retrieving conversations: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving conversations")

@router.get("/conversations/{chat_id}", response_model=ConversationResponse)
async def get_conversation(chat_id: str, db: Session = Depends(get_db)):
    """Get detailed information and CSI scores for a specific conversation."""
    try:
        conversation = db.query(Conversation).filter(Conversation.fb_chat_id == chat_id).first()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        return ConversationResponse.from_orm(conversation)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving conversation {chat_id}: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving conversation")