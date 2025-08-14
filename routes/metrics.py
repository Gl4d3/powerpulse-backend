from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import logging

from database import get_db
from services.analytics_service import analytics_service
from schemas import MetricsResponse

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(db: Session = Depends(get_db)):
    """
    Get aggregated business intelligence metrics:
    - Average sentiment score
    - CSAT percentage 
    - First Contact Resolution percentage
    - Average agent response time
    - Total conversations and messages
    - Most common topics/keywords
    """
    try:
        metrics = analytics_service.get_cached_metrics(db)
        return metrics
        
    except Exception as e:
        logger.error(f"Error retrieving metrics: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving metrics")

@router.post("/metrics/recalculate", response_model=MetricsResponse)
async def recalculate_metrics(db: Session = Depends(get_db)):
    """
    Force recalculation of all metrics.
    Use this endpoint to refresh metrics after data changes.
    """
    try:
        logger.info("Forcing metrics recalculation")
        metrics = analytics_service.calculate_and_cache_metrics(db)
        
        return MetricsResponse(
            avg_sentiment_score=metrics['avg_sentiment_score'],
            csat_percentage=metrics['csat_percentage'],
            fcr_percentage=metrics['fcr_percentage'],
            avg_response_time_minutes=metrics['avg_response_time_minutes'],
            total_conversations=metrics['total_conversations'],
            total_messages=metrics['total_messages'],
            most_common_topics=metrics['most_common_topics'],
            last_updated=metrics['last_updated']
        )
        
    except Exception as e:
        logger.error(f"Error recalculating metrics: {e}")
        raise HTTPException(status_code=500, detail="Error recalculating metrics")

@router.get("/metrics/summary")
async def get_metrics_summary(db: Session = Depends(get_db)):
    """Get a quick summary of key metrics"""
    try:
        from models import Conversation, Message
        
        total_conversations = db.query(Conversation).count()
        total_messages = db.query(Message).count()
        
        # Get latest processed conversations
        recent_conversations = db.query(Conversation).order_by(
            Conversation.updated_at.desc()
        ).limit(5).all()
        
        return {
            "total_conversations": total_conversations,
            "total_messages": total_messages,
            "recent_activity": [
                {
                    "chat_id": conv.fb_chat_id,
                    "satisfaction_score": conv.satisfaction_score,
                    "updated_at": conv.updated_at
                }
                for conv in recent_conversations
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting metrics summary: {e}")
        raise HTTPException(status_code=500, detail="Error getting metrics summary")
