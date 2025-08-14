from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Optional
import pandas as pd
import io
import logging
from datetime import datetime

from database import get_db
from models import Conversation, Message

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/download")
async def download_csv(
    db: Session = Depends(get_db),
    export_type: str = Query(default="conversations", pattern="^(conversations|messages|all)$"),
    min_satisfaction: Optional[float] = Query(default=None, ge=1, le=5),
    max_satisfaction: Optional[float] = Query(default=None, ge=1, le=5),
    date_from: Optional[str] = Query(default=None),
    date_to: Optional[str] = Query(default=None)
):
    """
    Export conversation and/or message data as CSV.
    Supports filtering by satisfaction scores and date ranges.
    """
    try:
        if export_type == "conversations":
            csv_content = await _export_conversations_csv(db, min_satisfaction, max_satisfaction, date_from, date_to)
            filename = f"conversations_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        elif export_type == "messages":
            csv_content = await _export_messages_csv(db, min_satisfaction, max_satisfaction, date_from, date_to)
            filename = f"messages_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        elif export_type == "all":
            csv_content = await _export_all_data_csv(db, min_satisfaction, max_satisfaction, date_from, date_to)
            filename = f"full_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        else:
            raise HTTPException(status_code=400, detail="Invalid export_type")
        
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": "text/csv; charset=utf-8"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting data: {e}")
        raise HTTPException(status_code=500, detail="Error exporting data")

async def _export_conversations_csv(
    db: Session, 
    min_satisfaction: Optional[float] = None,
    max_satisfaction: Optional[float] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None
) -> str:
    """Export conversations data as CSV"""
    try:
        # Build query
        query = db.query(Conversation)
        
        # Apply filters
        if min_satisfaction is not None:
            query = query.filter(Conversation.satisfaction_score >= min_satisfaction)
        
        if max_satisfaction is not None:
            query = query.filter(Conversation.satisfaction_score <= max_satisfaction)
        
        if date_from:
            try:
                date_from_dt = datetime.fromisoformat(date_from)
                query = query.filter(Conversation.first_message_time >= date_from_dt)
            except ValueError:
                pass
        
        if date_to:
            try:
                date_to_dt = datetime.fromisoformat(date_to)
                query = query.filter(Conversation.last_message_time <= date_to_dt)
            except ValueError:
                pass
        
        conversations = query.all()
        
        # Convert to DataFrame
        data = []
        for conv in conversations:
            data.append({
                'chat_id': conv.fb_chat_id,
                'total_messages': conv.total_messages,
                'customer_messages': conv.customer_messages,
                'agent_messages': conv.agent_messages,
                'satisfaction_score': conv.satisfaction_score,
                'satisfaction_confidence': conv.satisfaction_confidence,
                'is_satisfied': conv.is_satisfied,
                'avg_sentiment': conv.avg_sentiment,
                'first_contact_resolution': conv.first_contact_resolution,
                'avg_response_time_minutes': conv.avg_response_time_minutes,
                'first_message_time': conv.first_message_time,
                'last_message_time': conv.last_message_time,
                'common_topics': ', '.join(conv.common_topics) if conv.common_topics else '',
                'created_at': conv.created_at,
                'updated_at': conv.updated_at
            })
        
        df = pd.DataFrame(data)
        
        # Convert to CSV
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False, encoding='utf-8')
        return csv_buffer.getvalue()
        
    except Exception as e:
        logger.error(f"Error exporting conversations CSV: {e}")
        raise

async def _export_messages_csv(
    db: Session,
    min_satisfaction: Optional[float] = None,
    max_satisfaction: Optional[float] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None
) -> str:
    """Export messages data as CSV"""
    try:
        # Build query with conversation filters
        query = db.query(Message)
        
        if any([min_satisfaction, max_satisfaction, date_from, date_to]):
            # Join with conversations to apply filters
            conv_query = db.query(Conversation)
            
            if min_satisfaction is not None:
                conv_query = conv_query.filter(Conversation.satisfaction_score >= min_satisfaction)
            
            if max_satisfaction is not None:
                conv_query = conv_query.filter(Conversation.satisfaction_score <= max_satisfaction)
            
            if date_from:
                try:
                    date_from_dt = datetime.fromisoformat(date_from)
                    conv_query = conv_query.filter(Conversation.first_message_time >= date_from_dt)
                except ValueError:
                    pass
            
            if date_to:
                try:
                    date_to_dt = datetime.fromisoformat(date_to)
                    conv_query = conv_query.filter(Conversation.last_message_time <= date_to_dt)
                except ValueError:
                    pass
            
            # Get filtered chat IDs
            filtered_chat_ids = [conv.fb_chat_id for conv in conv_query.all()]
            query = query.filter(Message.fb_chat_id.in_(filtered_chat_ids))
        
        messages = query.order_by(Message.social_create_time).all()
        
        # Convert to DataFrame
        data = []
        for msg in messages:
            data.append({
                'message_id': msg.id,
                'chat_id': msg.fb_chat_id,
                'message_content': msg.message_content,
                'direction': msg.direction,
                'social_create_time': msg.social_create_time,
                'agent_info': str(msg.agent_info) if msg.agent_info else '',
                'sentiment_score': msg.sentiment_score,
                'sentiment_confidence': msg.sentiment_confidence,
                'topics': ', '.join(msg.topics) if msg.topics else '',
                'is_first_contact': msg.is_first_contact,
                'response_time_minutes': msg.response_time_minutes,
                'created_at': msg.created_at,
                'updated_at': msg.updated_at
            })
        
        df = pd.DataFrame(data)
        
        # Convert to CSV
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False, encoding='utf-8')
        return csv_buffer.getvalue()
        
    except Exception as e:
        logger.error(f"Error exporting messages CSV: {e}")
        raise

async def _export_all_data_csv(
    db: Session,
    min_satisfaction: Optional[float] = None,
    max_satisfaction: Optional[float] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None
) -> str:
    """Export combined conversation and message data as CSV"""
    try:
        # Join conversations and messages
        query = db.query(Message, Conversation).join(
            Conversation, Message.fb_chat_id == Conversation.fb_chat_id
        )
        
        # Apply filters
        if min_satisfaction is not None:
            query = query.filter(Conversation.satisfaction_score >= min_satisfaction)
        
        if max_satisfaction is not None:
            query = query.filter(Conversation.satisfaction_score <= max_satisfaction)
        
        if date_from:
            try:
                date_from_dt = datetime.fromisoformat(date_from)
                query = query.filter(Conversation.first_message_time >= date_from_dt)
            except ValueError:
                pass
        
        if date_to:
            try:
                date_to_dt = datetime.fromisoformat(date_to)
                query = query.filter(Conversation.last_message_time <= date_to_dt)
            except ValueError:
                pass
        
        results = query.order_by(Message.social_create_time).all()
        
        # Convert to DataFrame
        data = []
        for msg, conv in results:
            data.append({
                'message_id': msg.id,
                'chat_id': msg.fb_chat_id,
                'message_content': msg.message_content,
                'direction': msg.direction,
                'social_create_time': msg.social_create_time,
                'agent_info': str(msg.agent_info) if msg.agent_info else '',
                'message_sentiment_score': msg.sentiment_score,
                'message_sentiment_confidence': msg.sentiment_confidence,
                'message_topics': ', '.join(msg.topics) if msg.topics else '',
                'is_first_contact': msg.is_first_contact,
                'response_time_minutes': msg.response_time_minutes,
                'conversation_total_messages': conv.total_messages,
                'conversation_satisfaction_score': conv.satisfaction_score,
                'conversation_satisfaction_confidence': conv.satisfaction_confidence,
                'conversation_is_satisfied': conv.is_satisfied,
                'conversation_avg_sentiment': conv.avg_sentiment,
                'conversation_fcr': conv.first_contact_resolution,
                'conversation_avg_response_time': conv.avg_response_time_minutes,
                'conversation_common_topics': ', '.join(conv.common_topics) if conv.common_topics else '',
                'message_created_at': msg.created_at,
                'conversation_updated_at': conv.updated_at
            })
        
        df = pd.DataFrame(data)
        
        # Convert to CSV
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False, encoding='utf-8')
        return csv_buffer.getvalue()
        
    except Exception as e:
        logger.error(f"Error exporting combined CSV: {e}")
        raise

@router.get("/download/metrics")
async def download_metrics_csv(db: Session = Depends(get_db)):
    """Export current metrics as CSV"""
    try:
        from services.analytics_service import analytics_service
        
        metrics = analytics_service.get_cached_metrics(db)
        
        # Create metrics DataFrame
        data = [
            {'metric_name': 'Average Sentiment Score', 'value': metrics.avg_sentiment_score},
            {'metric_name': 'CSAT Percentage', 'value': metrics.csat_percentage},
            {'metric_name': 'FCR Percentage', 'value': metrics.fcr_percentage},
            {'metric_name': 'Average Response Time (minutes)', 'value': metrics.avg_response_time_minutes},
            {'metric_name': 'Total Conversations', 'value': metrics.total_conversations},
            {'metric_name': 'Total Messages', 'value': metrics.total_messages},
        ]
        
        # Add topics data
        for i, topic in enumerate(metrics.most_common_topics):
            data.append({
                'metric_name': f'Top Topic {i+1}',
                'value': f"{topic['topic']} ({topic['count']} mentions, {topic['percentage']}%)"
            })
        
        df = pd.DataFrame(data)
        
        # Convert to CSV
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False, encoding='utf-8')
        
        filename = f"metrics_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return Response(
            content=csv_buffer.getvalue(),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": "text/csv; charset=utf-8"
            }
        )
        
    except Exception as e:
        logger.error(f"Error exporting metrics CSV: {e}")
        raise HTTPException(status_code=500, detail="Error exporting metrics")
