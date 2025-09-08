"""
API endpoints for retrieving and searching individual conversations and their
CSI (Customer Satisfaction Index) data.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, asc, case, func
from typing import List
from datetime import date, datetime
import logging

from config import settings
from database import get_db
from models import Conversation, DailyAnalysis, Message
from schemas import ConversationListResponse, ConversationResponse, MessageResponse

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/conversations", response_model=ConversationListResponse)
def get_conversations(
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=settings.DEFAULT_PAGE_SIZE, ge=1, le=settings.MAX_PAGE_SIZE),
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
            func.max(case((DailyAnalysis.fcr_score > 7, 1), else_=0)).label("has_fcr")
        ).filter(DailyAnalysis.csi_score.isnot(None))\
        .group_by(DailyAnalysis.conversation_id).subquery()

        # Main query to join Conversation with aggregated stats
        query = db.query(
            Conversation,
            agg_subquery.c.avg_sentiment,
            agg_subquery.c.avg_csi,
            agg_subquery.c.has_fcr
        ).join(agg_subquery, Conversation.id == agg_subquery.c.conversation_id)

        total = query.count()
        
        results = query.order_by(desc(Conversation.last_message_time)).offset((page - 1) * page_size).limit(page_size).all()
        
        conversation_summaries = []
        for row in results:
            conv, avg_sentiment, avg_csi, has_fcr = row
            
            topics_query = db.query(DailyAnalysis.common_topics).filter(
                DailyAnalysis.conversation_id == conv.id,
                DailyAnalysis.common_topics.isnot(None)
            ).all()
            
            all_topics = set()
            for topic_row in topics_query:
                if topic_row[0] and isinstance(topic_row[0], list):
                    all_topics.update(topic_row[0])
            
            agents_query = db.query(Message.agent_info).filter(
                Message.conversation_id == conv.id,
                Message.agent_info.isnot(None),
                Message.direction == 'to_client'
            ).distinct().all()
            
            agents_list = [info[0] for info in agents_query if info[0] and info[0].get('name')]

            conversation_summaries.append(ConversationResponse(
                chat_id=conv.fb_chat_id,
                username=conv.customer_name,
                avg_sentiment_score=avg_sentiment,
                avg_csi_score=avg_csi,
                fcr=bool(has_fcr),
                topics=list(all_topics),
                agents=agents_list,
                created_at=conv.created_at,
                total_messages=conv.total_messages,
                customer_messages=conv.customer_messages,
                agent_messages=conv.agent_messages,
                first_message_time=conv.first_message_time,
                last_message_time=conv.last_message_time,
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
            func.max(case((DailyAnalysis.fcr_score > 7, 1), else_=0))
        ).join(DailyAnalysis, Conversation.id == DailyAnalysis.conversation_id)\
        .filter(Conversation.fb_chat_id == chat_id, DailyAnalysis.csi_score.isnot(None))\
        .group_by(Conversation.id).first()

        if not result:
            raise HTTPException(status_code=404, detail="Conversation not found or has no CSI data")

        conv, avg_sentiment, avg_csi, has_fcr = result
        
        topics_query = db.query(DailyAnalysis.common_topics).filter(
            DailyAnalysis.conversation_id == conv.id,
            DailyAnalysis.common_topics.isnot(None)
        ).all()
        
        all_topics = set()
        for topic_row in topics_query:
            if topic_row[0] and isinstance(topic_row[0], list):
                all_topics.update(topic_row[0])
        
        agents_query = db.query(Message.agent_info).filter(
            Message.conversation_id == conv.id,
            Message.agent_info.isnot(None),
            Message.direction == 'to_client'
        ).distinct().all()
        
        agents_list = [info[0] for info in agents_query if info[0] and info[0].get('name')]
        
        return ConversationResponse(
            chat_id=conv.fb_chat_id,
            username=conv.customer_name,
            avg_sentiment_score=avg_sentiment,
            avg_csi_score=avg_csi,
            fcr=bool(has_fcr),
            topics=list(all_topics),
            agents=agents_list,
            created_at=conv.created_at,
            total_messages=conv.total_messages,
            customer_messages=conv.customer_messages,
            agent_messages=conv.agent_messages,
            first_message_time=conv.first_message_time,
            last_message_time=conv.last_message_time,
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
        messages = db.query(Message).filter(Message.conversation_id == conversation.id).order_by(Message.social_create_time).all()
        
        # Convert to response format
        message_responses = []
        for msg in messages:
            message_responses.append(MessageResponse(
                timestamp=msg.social_create_time,
                direction=msg.direction,
                content=msg.message_content,
                sentiment_score=msg.sentiment_score,
                topics=msg.topics or [],
                agent_info=msg.agent_info
            ))
        
        return message_responses
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving messages for conversation {chat_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error retrieving messages")
