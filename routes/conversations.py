"""
API endpoints for retrieving and searching individual conversations and their
CSI (Customer Satisfaction Index) data.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc
from typing import Optional, List
from datetime import date, datetime
import logging

from config import Settings
settings = Settings()

from database import get_db
from models import Conversation, DailyAnalysis
from schemas import ConversationListResponse, ConversationResponse, DailyAnalysisResponse, MessageResponse
from sqlalchemy import func
from sqlalchemy.orm import aliased

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/conversations", response_model=ConversationListResponse)
def get_conversations(
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=settings.DEFAULT_PAGE_SIZE, ge=1, le=settings.MAX_PAGE_SIZE),
    # Note: Sorting and filtering will be simplified for this frontend-facing endpoint
):
    """
    Get a paginated list of conversation summaries, aggregated from daily analyses.
    """
    try:
        # Subquery to calculate aggregated stats per conversation
        agg_subquery = db.query(
            DailyAnalysis.conversation_id,
            func.avg(DailyAnalysis.sentiment_score).label("avg_sentiment"),
            func.avg(DailyAnalysis.csi_score).label("avg_csi"),
            func.bool_or(DailyAnalysis.fcr_score > 7).label("is_fcr")
        ).group_by(DailyAnalysis.conversation_id).subquery()

        # Main query to join Conversation with aggregated stats
        query = db.query(
            Conversation,
            agg_subquery.c.avg_sentiment,
            agg_subquery.c.avg_csi,
            agg_subquery.c.is_fcr
        ).join(agg_subquery, Conversation.id == agg_subquery.c.conversation_id)

        total = query.count()
        
        # Apply pagination
        results = query.order_by(Conversation.first_message_time.desc()).offset((page - 1) * page_size).limit(page_size).all()
        
        # Format the response to match the frontend contract
        conversation_summaries = []
        for conv, avg_sentiment, avg_csi, is_fcr in results:
            conversation_summaries.append(ConversationResponse(
                chat_id=conv.fb_chat_id,
                sentiment_score=avg_sentiment,
                satisfaction_score=avg_csi * 10 if avg_csi else None, # Scale to 100
                fcr=is_fcr,
                topics=conv.common_topics or [],
                created_at=conv.first_message_time,
                # TODO: Add agent info if available/needed
            ))

        return ConversationListResponse(
            conversations=conversation_summaries,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size
        )
        
    except Exception as e:
        logger.error(f"Error retrieving conversations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error retrieving conversations")

@router.get("/conversations/{chat_id}", response_model=ConversationResponse)
def get_conversation(chat_id: str, db: Session = Depends(get_db)):
    """Get an aggregated summary for a specific conversation."""
    try:
        # Similar aggregation logic as the list view, but for a single conversation
        result = db.query(
            Conversation,
            func.avg(DailyAnalysis.sentiment_score),
            func.avg(DailyAnalysis.csi_score),
            func.bool_or(DailyAnalysis.fcr_score > 7)
        ).join(DailyAnalysis, Conversation.id == DailyAnalysis.conversation_id)\
        .filter(Conversation.fb_chat_id == chat_id)\
        .group_by(Conversation.id).first()

        if not result:
            raise HTTPException(status_code=404, detail="Conversation not found")

        conv, avg_sentiment, avg_csi, is_fcr = result
        
        return ConversationResponse(
            chat_id=conv.fb_chat_id,
            sentiment_score=avg_sentiment,
            satisfaction_score=avg_csi * 10 if avg_csi else None, # Scale to 100
            fcr=is_fcr,
            topics=conv.common_topics or [],
            created_at=conv.first_message_time,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving conversation {chat_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error retrieving conversation")

@router.get("/conversations/{chat_id}/messages", response_model=List[MessageResponse])
async def get_conversation_messages(chat_id: str, db: Session = Depends(get_db)):
    """Get the full message transcript for a specific conversation."""
    try:
        # Check if conversation exists first
        conversation = db.query(Conversation).filter(Conversation.fb_chat_id == chat_id).first()
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Query for all messages in that conversation
        messages = db.query(Message).filter(Message.fb_chat_id == chat_id).order_by(Message.social_create_time).all()
        
        return [MessageResponse.from_orm(msg) for msg in messages]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving messages for conversation {chat_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error retrieving messages")
