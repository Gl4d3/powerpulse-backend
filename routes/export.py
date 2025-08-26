"""
API endpoints for exporting conversation and metrics data to CSV format,
with a focus on the new CSI (Customer Satisfaction Index) scores.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from typing import Optional
import pandas as pd
import io
import logging
from datetime import datetime

from database import get_db
from models import Conversation, Message
from services.analytics_service import analytics_service

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/download")
async def download_csv(
    db: Session = Depends(get_db),
    export_type: str = Query(default="conversations", pattern="^(conversations|messages|all)$"),
    min_csi_score: Optional[float] = Query(default=None, ge=1, le=10),
    max_csi_score: Optional[float] = Query(default=None, ge=1, le=10),
    date_from: Optional[str] = Query(default=None),
    date_to: Optional[str] = Query(default=None)
):
    """
    Export conversation and/or message data as CSV.
    Supports filtering by CSI scores and date ranges.
    """
    try:
        if export_type == "conversations":
            csv_content = await _export_conversations_csv(db, min_csi_score, max_csi_score, date_from, date_to)
            filename = f"conversations_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        elif export_type == "messages":
            csv_content = await _export_messages_csv(db, min_csi_score, max_csi_score, date_from, date_to)
            filename = f"messages_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        else: # all
            csv_content = await _export_all_data_csv(db, min_csi_score, max_csi_score, date_from, date_to)
            filename = f"full_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        logger.error(f"Error exporting data: {e}")
        raise HTTPException(status_code=500, detail="Error exporting data")

async def _export_conversations_csv(
    db: Session, 
    min_csi_score: Optional[float] = None,
    max_csi_score: Optional[float] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None
) -> str:
    query = db.query(Conversation)
    
    if min_csi_score is not None: query = query.filter(Conversation.csi_score >= min_csi_score)
    if max_csi_score is not None: query = query.filter(Conversation.csi_score <= max_csi_score)
    if date_from: query = query.filter(Conversation.first_message_time >= datetime.fromisoformat(date_from))
    if date_to: query = query.filter(Conversation.last_message_time <= datetime.fromisoformat(date_to))
    
    data = [{
        'chat_id': conv.fb_chat_id,
        'csi_score': conv.csi_score,
        'effectiveness_score': conv.effectiveness_score,
        'efficiency_score': conv.efficiency_score,
        'effort_score': conv.effort_score,
        'empathy_score': conv.empathy_score,
        'total_messages': conv.total_messages,
        'avg_sentiment': conv.avg_sentiment,
        'first_contact_resolution': conv.first_contact_resolution,
        'avg_response_time_minutes': conv.avg_response_time_minutes,
        'first_message_time': conv.first_message_time,
        'last_message_time': conv.last_message_time,
        'common_topics': ', '.join(conv.common_topics) if conv.common_topics else ''
    } for conv in query.all()]
    
    df = pd.DataFrame(data)
    with io.StringIO() as buffer: 
        df.to_csv(buffer, index=False)
        return buffer.getvalue()

async def _export_all_data_csv(
    db: Session,
    min_csi_score: Optional[float] = None,
    max_csi_score: Optional[float] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None
) -> str:
    query = db.query(Message, Conversation).join(Conversation, Message.fb_chat_id == Conversation.fb_chat_id)

    if min_csi_score is not None: query = query.filter(Conversation.csi_score >= min_csi_score)
    if max_csi_score is not None: query = query.filter(Conversation.csi_score <= max_csi_score)
    if date_from: query = query.filter(Conversation.first_message_time >= datetime.fromisoformat(date_from))
    if date_to: query = query.filter(Conversation.last_message_time <= datetime.fromisoformat(date_to))

    data = [{
        'message_id': msg.id,
        'chat_id': msg.fb_chat_id,
        'message_content': msg.message_content,
        'direction': msg.direction,
        'social_create_time': msg.social_create_time,
        'message_sentiment_score': msg.sentiment_score,
        'conversation_csi_score': conv.csi_score,
        'conversation_effectiveness_score': conv.effectiveness_score,
        'conversation_efficiency_score': conv.efficiency_score,
        'conversation_effort_score': conv.effort_score,
        'conversation_empathy_score': conv.empathy_score,
    } for msg, conv in query.order_by(Message.social_create_time).all()]

    df = pd.DataFrame(data)
    with io.StringIO() as buffer:
        df.to_csv(buffer, index=False)
        return buffer.getvalue()

@router.get("/download/metrics")
async def download_metrics_csv(db: Session = Depends(get_db)):
    """Export current CSI metrics as CSV."""
    try:
        metrics = analytics_service.get_cached_csi_metrics(db)
        data = [
            {'metric_name': 'Overall CSI Score', 'value': metrics.overall_csi_score},
            {'metric_name': 'Average Effectiveness Score', 'value': metrics.avg_effectiveness_score},
            {'metric_name': 'Average Efficiency Score', 'value': metrics.avg_efficiency_score},
            {'metric_name': 'Average Effort Score', 'value': metrics.avg_effort_score},
            {'metric_name': 'Average Empathy Score', 'value': metrics.avg_empathy_score},
            {'metric_name': 'Total Conversations Analyzed', 'value': metrics.total_conversations_analyzed},
        ]
        df = pd.DataFrame(data)
        with io.StringIO() as buffer:
            df.to_csv(buffer, index=False)
            filename = f"csi_metrics_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            return Response(
                content=buffer.getvalue(),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )
    except Exception as e:
        logger.error(f"Error exporting CSI metrics CSV: {e}")
        raise HTTPException(status_code=500, detail="Error exporting CSI metrics CSV")