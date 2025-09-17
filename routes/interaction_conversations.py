"""
API endpoints for retrieving and searching conversations with interaction-based analysis.
This provides an alternative view to daily analysis, focusing on individual interactions.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, asc, case, func
from typing import List
from datetime import date, datetime
import logging

from config import settings
from database import get_db
from models import Conversation, InteractionAnalysis, Message
from schemas import (
    InteractionConversationListResponse, 
    InteractionConversationResponse, 
    InteractionAnalysisResponse,
    MessageResponse
)

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/conversations", response_model=InteractionConversationListResponse)
def get_conversations_by_interactions(
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=settings.DEFAULT_PAGE_SIZE, ge=1, le=settings.MAX_PAGE_SIZE),
):
    """
    Get a paginated list of conversation summaries, aggregated from interaction analyses.
    """
    try:
        # Subquery to calculate aggregated stats per conversation from interactions
        agg_subquery = db.query(
            InteractionAnalysis.conversation_id,
            func.avg(InteractionAnalysis.csi_score).label("avg_csi"),
            func.avg(InteractionAnalysis.effectiveness_score).label("avg_effectiveness"),
            func.avg(InteractionAnalysis.efficiency_score).label("avg_efficiency"),
            func.avg(InteractionAnalysis.effort_score).label("avg_effort"),
            func.avg(InteractionAnalysis.empathy_score).label("avg_empathy"),
            func.count(InteractionAnalysis.id).label("interaction_count"),
            func.avg(InteractionAnalysis.interaction_duration).label("avg_duration")
        ).filter(InteractionAnalysis.csi_score.isnot(None))\
        .group_by(InteractionAnalysis.conversation_id).subquery()

        # Main query to join Conversation with aggregated interaction stats
        query = db.query(
            Conversation,
            agg_subquery.c.avg_csi,
            agg_subquery.c.avg_effectiveness,
            agg_subquery.c.avg_efficiency,
            agg_subquery.c.avg_effort,
            agg_subquery.c.avg_empathy,
            agg_subquery.c.interaction_count,
            agg_subquery.c.avg_duration
        ).join(agg_subquery, Conversation.id == agg_subquery.c.conversation_id)

        total = query.count()
        
        results = query.order_by(desc(Conversation.last_message_time)).offset((page - 1) * page_size).limit(page_size).all()
        
        conversation_summaries = []
        for row in results:
            conv, avg_csi, avg_effectiveness, avg_efficiency, avg_effort, avg_empathy, interaction_count, avg_duration = row
            
            # Get topics from interaction analyses
            topics_query = db.query(InteractionAnalysis.common_topics).filter(
                InteractionAnalysis.conversation_id == conv.id,
                InteractionAnalysis.common_topics.isnot(None)
            ).all()
            
            all_topics = set()
            for topic_row in topics_query:
                if topic_row[0] and isinstance(topic_row[0], list):
                    all_topics.update(topic_row[0])
            
            # Get interaction type distribution
            interaction_types = db.query(
                InteractionAnalysis.interaction_type,
                func.count(InteractionAnalysis.interaction_type)
            ).filter(
                InteractionAnalysis.conversation_id == conv.id,
                InteractionAnalysis.interaction_type.isnot(None)
            ).group_by(InteractionAnalysis.interaction_type).all()
            
            # Get complexity distribution
            complexity_dist = db.query(
                InteractionAnalysis.interaction_complexity,
                func.count(InteractionAnalysis.interaction_complexity)
            ).filter(
                InteractionAnalysis.conversation_id == conv.id,
                InteractionAnalysis.interaction_complexity.isnot(None)
            ).group_by(InteractionAnalysis.interaction_complexity).all()
            
            # Find most common interaction type
            most_common_type = None
            if interaction_types:
                most_common_type = max(interaction_types, key=lambda x: x[1])[0]
            
            # Get agents information
            agents_query = db.query(Message.agent_info).filter(
                Message.conversation_id == conv.id,
                Message.agent_info.isnot(None),
                Message.direction == 'to_client'
            ).distinct().all()
            
            agents_list = [info[0] for info in agents_query if info[0] and (info[0].get('name') or info[0].get('email'))]

            conversation_summaries.append(InteractionConversationResponse(
                chat_id=conv.fb_chat_id,
                username=conv.customer_name,
                avg_csi_score=avg_csi,
                avg_effectiveness_score=avg_effectiveness,
                avg_efficiency_score=avg_efficiency,
                avg_effort_score=avg_effort,
                avg_empathy_score=avg_empathy,
                total_interactions=interaction_count or 0,
                avg_interaction_duration=avg_duration,
                most_common_interaction_type=most_common_type,
                complexity_distribution={k: v for k, v in complexity_dist} if complexity_dist else {},
                topics=list(all_topics),
                agents=agents_list,
                created_at=conv.created_at,
                total_messages=conv.total_messages,
                customer_messages=conv.customer_messages,
                agent_messages=conv.agent_messages,
                first_message_time=conv.first_message_time,
                last_message_time=conv.last_message_time,
            ))

        return InteractionConversationListResponse(
            conversations=conversation_summaries,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size
        )
        
    except Exception as e:
        logger.error(f"Error retrieving interaction-based conversations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error retrieving conversations")

@router.get("/conversations/{chat_id}", response_model=InteractionConversationResponse)
def get_conversation_by_interactions(chat_id: str, db: Session = Depends(get_db)):
    """Get an aggregated summary for a specific conversation based on interactions."""
    try:
        # Similar aggregation logic as the list view, but for a single conversation
        result = db.query(
            Conversation,
            func.avg(InteractionAnalysis.csi_score),
            func.avg(InteractionAnalysis.effectiveness_score),
            func.avg(InteractionAnalysis.efficiency_score),
            func.avg(InteractionAnalysis.effort_score),
            func.avg(InteractionAnalysis.empathy_score),
            func.count(InteractionAnalysis.id),
            func.avg(InteractionAnalysis.interaction_duration)
        ).join(InteractionAnalysis, Conversation.id == InteractionAnalysis.conversation_id)\
        .filter(Conversation.fb_chat_id == chat_id, InteractionAnalysis.csi_score.isnot(None))\
        .group_by(Conversation.id).first()

        if not result:
            raise HTTPException(status_code=404, detail="Conversation not found or has no interaction data")

        conv, avg_csi, avg_effectiveness, avg_efficiency, avg_effort, avg_empathy, interaction_count, avg_duration = result
        
        # Get topics from interaction analyses
        topics_query = db.query(InteractionAnalysis.common_topics).filter(
            InteractionAnalysis.conversation_id == conv.id,
            InteractionAnalysis.common_topics.isnot(None)
        ).all()
        
        all_topics = set()
        for topic_row in topics_query:
            if topic_row[0] and isinstance(topic_row[0], list):
                all_topics.update(topic_row[0])
        
        # Get interaction type distribution
        interaction_types = db.query(
            InteractionAnalysis.interaction_type,
            func.count(InteractionAnalysis.interaction_type)
        ).filter(
            InteractionAnalysis.conversation_id == conv.id,
            InteractionAnalysis.interaction_type.isnot(None)
        ).group_by(InteractionAnalysis.interaction_type).all()
        
        # Get complexity distribution
        complexity_dist = db.query(
            InteractionAnalysis.interaction_complexity,
            func.count(InteractionAnalysis.interaction_complexity)
        ).filter(
            InteractionAnalysis.conversation_id == conv.id,
            InteractionAnalysis.interaction_complexity.isnot(None)
        ).group_by(InteractionAnalysis.interaction_complexity).all()
        
        # Find most common interaction type
        most_common_type = None
        if interaction_types:
            most_common_type = max(interaction_types, key=lambda x: x[1])[0]
        
        # Get agents information
        agents_query = db.query(Message.agent_info).filter(
            Message.conversation_id == conv.id,
            Message.agent_info.isnot(None),
            Message.direction == 'to_client'
        ).distinct().all()
        
        agents_list = [info[0] for info in agents_query if info[0] and (info[0].get('name') or info[0].get('email'))]
        
        return InteractionConversationResponse(
            chat_id=conv.fb_chat_id,
            username=conv.customer_name,
            avg_csi_score=avg_csi,
            avg_effectiveness_score=avg_effectiveness,
            avg_efficiency_score=avg_efficiency,
            avg_effort_score=avg_effort,
            avg_empathy_score=avg_empathy,
            total_interactions=interaction_count or 0,
            avg_interaction_duration=avg_duration,
            most_common_interaction_type=most_common_type,
            complexity_distribution={k: v for k, v in complexity_dist} if complexity_dist else {},
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
        logger.error(f"Error retrieving interaction-based conversation {chat_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error retrieving conversation")

@router.get("/conversations/{chat_id}/interactions", response_model=List[InteractionAnalysisResponse])
def get_conversation_interactions(chat_id: str, db: Session = Depends(get_db)):
    """Get all interaction analyses for a specific conversation."""
    try:
        # Check if conversation exists first
        conversation = db.query(Conversation).filter(Conversation.fb_chat_id == chat_id).first()
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Query for all interaction analyses in that conversation
        interactions = db.query(InteractionAnalysis).filter(
            InteractionAnalysis.conversation_id == conversation.id
        ).order_by(InteractionAnalysis.interaction_start).all()
        
        return interactions
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving interactions for conversation {chat_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error retrieving interactions")

@router.get("/conversations/{chat_id}/messages", response_model=List[MessageResponse])
def get_conversation_messages_with_interactions(chat_id: str, db: Session = Depends(get_db)):
    """
    Get the full message transcript for a specific conversation, 
    same as daily analysis but maintained for consistency.
    """
    try:
        # Check if conversation exists first
        conversation = db.query(Conversation).filter(Conversation.fb_chat_id == chat_id).first()
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Query for all messages in that conversation
        messages = db.query(Message).filter(Message.conversation_id == conversation.id).order_by(Message.social_create_time).all()
        
        return messages
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving messages for conversation {chat_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error retrieving messages")