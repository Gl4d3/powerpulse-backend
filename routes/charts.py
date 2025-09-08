"""
API endpoints for providing data specifically formatted for frontend charts.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date
import logging
from typing import List, Dict, Any

from database import get_db
from services.analytics_service import analytics_service
from models import DailyAnalysis

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/sentiment-trend")
async def get_sentiment_trend(
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db)
):
    """
    Provides daily average sentiment scores over a date range, formatted for charts.
    """
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date cannot be after end_date")
        
    try:
        return await analytics_service.get_sentiment_trend(db, start_date, end_date)
    except Exception as e:
        logger.error(f"Error getting sentiment trend data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error getting sentiment trend data")

@router.get("/csi-trend")
async def get_csi_trend(
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db)
):
    """
    Provides daily average CSI and pillar scores over a date range, formatted for charts.
    """
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date cannot be after end_date")
        
    try:
        return await analytics_service.get_csi_trend(db, start_date, end_date)
    except Exception as e:
        logger.error(f"Error getting CSI trend data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error getting CSI trend data")

@router.get("/sentiment-distribution")
def get_sentiment_distribution(
    start_date: date = None,
    end_date: date = None,
    db: Session = Depends(get_db)
):
    """
    Provides sentiment distribution (positive, neutral, negative) for the specified date range.
    """
    try:
        # Base query for sentiment scores
        query = db.query(DailyAnalysis).filter(
            DailyAnalysis.sentiment_score.isnot(None),
            DailyAnalysis.csi_score.isnot(None)  # Only include analyzed conversations
        )
        
        if start_date and end_date:
            if start_date > end_date:
                raise HTTPException(status_code=400, detail="start_date cannot be after end_date")
            query = query.filter(DailyAnalysis.analysis_date.between(start_date, end_date))

        total_sentiment_scores = query.count()
        if total_sentiment_scores == 0:
            return {"positive": 0, "neutral": 0, "negative": 0}

        # Calculate sentiment distribution based on score ranges
        positive_count = query.filter(DailyAnalysis.sentiment_score >= 7).count()
        negative_count = query.filter(DailyAnalysis.sentiment_score <= 4).count()
        neutral_count = total_sentiment_scores - positive_count - negative_count

        return {
            "positive": round(positive_count / total_sentiment_scores, 3),
            "neutral": round(neutral_count / total_sentiment_scores, 3),
            "negative": round(negative_count / total_sentiment_scores, 3),
        }
        
    except Exception as e:
        logger.error(f"Error calculating sentiment distribution: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error calculating sentiment distribution")

@router.get("/topic-frequency")
def get_topic_frequency(
    start_date: date = None,
    end_date: date = None,
    limit: int = 30,
    db: Session = Depends(get_db)
):
    """
    Provides the top topics by frequency for the specified date range.
    Limited to the top 30 topics by default to avoid overwhelming the frontend.
    """
    try:
        # Base query for topics
        query = db.query(DailyAnalysis.common_topics).filter(
            DailyAnalysis.common_topics.isnot(None),
            DailyAnalysis.csi_score.isnot(None)  # Only include analyzed conversations
        )
        
        if start_date and end_date:
            if start_date > end_date:
                raise HTTPException(status_code=400, detail="start_date cannot be after end_date")
            query = query.filter(DailyAnalysis.analysis_date.between(start_date, end_date))

        # Aggregate topic frequencies
        topic_results = query.all()
        topic_frequency = {}
        
        for topics_list in topic_results:
            if topics_list[0]:  # Check if topics_list[0] is not None
                for topic in topics_list[0]:
                    if isinstance(topic, str) and topic.strip():  # Ensure topic is a valid string
                        topic_frequency[topic] = topic_frequency.get(topic, 0) + 1
        
        # Sort by frequency and limit to top results
        sorted_topics = sorted(topic_frequency.items(), key=lambda x: x[1], reverse=True)[:limit]
        
        return [{"topic": topic, "frequency": frequency} for topic, frequency in sorted_topics]
        
    except Exception as e:
        logger.error(f"Error calculating topic frequency: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error calculating topic frequency")
