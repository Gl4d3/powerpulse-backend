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
            func.avg(DailyAnalysis.csi_score).label("avg_csi"),
            func.avg(DailyAnalysis.effectiveness_score).label("avg_effectiveness"),
            func.avg(DailyAnalysis.efficiency_score).label("avg_efficiency"),
            func.avg(DailyAnalysis.effort_score).label("avg_effort"),
            func.avg(DailyAnalysis.empathy_score).label("avg_empathy")
        ).filter(DailyAnalysis.csi_score.isnot(None))\
        .group_by(DailyAnalysis.conversation_id).subquery()

        # Main query to join Conversation with aggregated stats
        query = db.query(
            Conversation,
            agg_subquery.c.avg_csi,
            agg_subquery.c.avg_effectiveness,
            agg_subquery.c.avg_efficiency,
            agg_subquery.c.avg_effort,
            agg_subquery.c.avg_empathy
        ).join(agg_subquery, Conversation.id == agg_subquery.c.conversation_id)

        total = query.count()
        
        results = query.order_by(desc(Conversation.last_message_time)).offset((page - 1) * page_size).limit(page_size).all()
        
        conversation_summaries = []
        for row in results:
            conv, avg_csi, avg_effectiveness, avg_efficiency, avg_effort, avg_empathy = row
            
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
            
            agents_list = [info[0] for info in agents_query if info[0] and (info[0].get('name') or info[0].get('email'))]

            conversation_summaries.append(ConversationResponse(
                chat_id=conv.fb_chat_id,
                username=conv.customer_name,
                avg_csi_score=avg_csi,
                avg_effectiveness_score=avg_effectiveness,
                avg_efficiency_score=avg_efficiency,
                avg_effort_score=avg_effort,
                avg_empathy_score=avg_empathy,
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
            func.avg(DailyAnalysis.csi_score),
            func.avg(DailyAnalysis.effectiveness_score),
            func.avg(DailyAnalysis.efficiency_score),
            func.avg(DailyAnalysis.effort_score),
            func.avg(DailyAnalysis.empathy_score)
        ).join(DailyAnalysis, Conversation.id == DailyAnalysis.conversation_id)\
        .filter(Conversation.fb_chat_id == chat_id, DailyAnalysis.csi_score.isnot(None))\
        .group_by(Conversation.id).first()

        if not result:
            raise HTTPException(status_code=404, detail="Conversation not found or has no CSI data")

        conv, avg_csi, avg_effectiveness, avg_efficiency, avg_effort, avg_empathy = result
        
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
        
        agents_list = [info[0] for info in agents_query if info[0] and (info[0].get('name') or info[0].get('email'))]
        
        return ConversationResponse(
            chat_id=conv.fb_chat_id,
            username=conv.customer_name,
            avg_csi_score=avg_csi,
            avg_effectiveness_score=avg_effectiveness,
            avg_efficiency_score=avg_efficiency,
            avg_effort_score=avg_effort,
            avg_empathy_score=avg_empathy,
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
def get_conversation_messages(chat_id: str, db: Session = Depends(get_db)):
    """Get the full message transcript for a specific conversation."""
    try:
        # Check if conversation exists first
        conversation = db.query(Conversation).filter(Conversation.fb_chat_id == chat_id).first()
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Query for all messages in that conversation
        messages = db.query(Message).filter(Message.conversation_id == conversation.id).order_by(Message.social_create_time).all()
        
        # The MessageResponse schema will automatically map the Message model attributes
        # because `from_attributes=True` is set in its Config.
        return messages
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving messages for conversation {chat_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error retrieving messages")
