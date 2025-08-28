"""
API endpoints for providing data specifically formatted for frontend charts.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date
import logging

from database import get_db
from services.analytics_service import analytics_service

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
