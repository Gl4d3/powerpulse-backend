from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc
from typing import Optional
import logging

from database import get_db
from models import Conversation, Message
from schemas import ConversationListResponse, ConversationResponse, PaginationParams
from config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/conversations", response_model=ConversationListResponse)
async def get_conversations(
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=settings.DEFAULT_PAGE_SIZE, ge=1, le=settings.MAX_PAGE_SIZE),
    sort_by: str = Query(default="updated_at", pattern="^(updated_at|satisfaction_score|avg_sentiment|total_messages)$"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    min_satisfaction: Optional[float] = Query(default=None, ge=1, le=5),
    max_satisfaction: Optional[float] = Query(default=None, ge=1, le=5),
    satisfied_only: Optional[bool] = Query(default=None)
):
    """
    Get paginated list of conversations with scores and metadata.
    Supports filtering and sorting options.
    """
    try:
        # Build query
        query = db.query(Conversation)
        
        # Apply filters
        if min_satisfaction is not None:
            query = query.filter(Conversation.satisfaction_score >= min_satisfaction)
        
        if max_satisfaction is not None:
            query = query.filter(Conversation.satisfaction_score <= max_satisfaction)
        
        if satisfied_only is not None:
            query = query.filter(Conversation.is_satisfied == satisfied_only)
        
        # Get total count before pagination
        total = query.count()
        
        # Apply sorting
        sort_column = getattr(Conversation, sort_by)
        if sort_order == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))
        
        # Apply pagination
        offset = (page - 1) * page_size
        conversations = query.offset(offset).limit(page_size).all()
        
        # Calculate total pages
        total_pages = (total + page_size - 1) // page_size
        
        return ConversationListResponse(
            conversations=[ConversationResponse.from_orm(conv) for conv in conversations],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
        
    except Exception as e:
        logger.error(f"Error retrieving conversations: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving conversations")

@router.get("/conversations/{chat_id}", response_model=ConversationResponse)
async def get_conversation(chat_id: str, db: Session = Depends(get_db)):
    """Get detailed information about a specific conversation"""
    try:
        conversation = db.query(Conversation).filter(
            Conversation.fb_chat_id == chat_id
        ).first()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        return ConversationResponse.from_orm(conversation)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving conversation {chat_id}: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving conversation")

@router.get("/conversations/{chat_id}/messages")
async def get_conversation_messages(
    chat_id: str,
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100)
):
    """Get paginated messages for a specific conversation"""
    try:
        # Check if conversation exists
        conversation = db.query(Conversation).filter(
            Conversation.fb_chat_id == chat_id
        ).first()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Get messages
        query = db.query(Message).filter(Message.fb_chat_id == chat_id)
        total = query.count()
        
        # Apply pagination and sorting
        offset = (page - 1) * page_size
        messages = query.order_by(asc(Message.social_create_time)).offset(offset).limit(page_size).all()
        
        total_pages = (total + page_size - 1) // page_size
        
        return {
            "messages": [
                {
                    "id": msg.id,
                    "message_content": msg.message_content,
                    "direction": msg.direction,
                    "social_create_time": msg.social_create_time,
                    "sentiment_score": msg.sentiment_score,
                    "sentiment_confidence": msg.sentiment_confidence,
                    "topics": msg.topics,
                    "response_time_minutes": msg.response_time_minutes
                }
                for msg in messages
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "conversation": {
                "chat_id": conversation.fb_chat_id,
                "satisfaction_score": conversation.satisfaction_score,
                "avg_sentiment": conversation.avg_sentiment
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving messages for conversation {chat_id}: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving conversation messages")

@router.get("/conversations/search")
async def search_conversations(
    db: Session = Depends(get_db),
    query: str = Query(..., min_length=2),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100)
):
    """Search conversations by content or topics"""
    try:
        # Search in message content
        search_query = db.query(Conversation).join(Message).filter(
            Message.message_content.contains(query)
        ).distinct()
        
        total = search_query.count()
        
        # Apply pagination
        offset = (page - 1) * page_size
        conversations = search_query.offset(offset).limit(page_size).all()
        
        total_pages = (total + page_size - 1) // page_size
        
        return {
            "conversations": [ConversationResponse.from_orm(conv) for conv in conversations],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "search_query": query
        }
        
    except Exception as e:
        logger.error(f"Error searching conversations: {e}")
        raise HTTPException(status_code=500, detail="Error searching conversations")
