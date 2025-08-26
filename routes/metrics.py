"""
API endpoints for retrieving Customer Satisfaction Index (CSI) metrics.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import logging

from database import get_db
from services.analytics_service import analytics_service
from schemas import CSIMetricsResponse

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/metrics", response_model=CSIMetricsResponse)
async def get_csi_metrics(db: Session = Depends(get_db)):
    """
    Get aggregated Customer Satisfaction Index (CSI) metrics.
    Provides a holistic view of customer satisfaction based on the four pillars:
    - Effectiveness
    - Efficiency
    - Effort
    - Empathy
    """
    try:
        # Return cached CSI metrics
        metrics = analytics_service.get_cached_csi_metrics(db)
        return metrics
        
    except Exception as e:
        logger.error(f"Error retrieving CSI metrics: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving CSI metrics")

@router.post("/metrics/recalculate", response_model=CSIMetricsResponse)
async def recalculate_csi_metrics(db: Session = Depends(get_db)):
    """
    Force recalculation of all CSI metrics.
    Use this endpoint to refresh metrics after data changes or reprocessing.
    """
    try:
        logger.info("Forcing CSI metrics recalculation")
        metrics = analytics_service.calculate_and_cache_csi_metrics(db)
        return CSIMetricsResponse(**metrics)
        
    except Exception as e:
        logger.error(f"Error recalculating CSI metrics: {e}")
        raise HTTPException(status_code=500, detail="Error recalculating CSI metrics")