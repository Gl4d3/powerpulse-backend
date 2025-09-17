"""
API endpoints for interaction-based Customer Satisfaction Index (CSI) metrics.
These endpoints provide interaction-level analytics as an alternative to daily analysis.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import date
from typing import Optional
import logging

from database import get_db
from services.enhanced_analytics_service import enhanced_analytics_service
from schemas import (
    CSIMetricsResponse, 
    HistoricalMetricsResponse, 
    InteractionMetricsResponse,
    InteractionHistoricalMetricsResponse
)

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/", response_model=InteractionMetricsResponse)
def get_interaction_csi_metrics(db: Session = Depends(get_db)):
    """
    Retrieve the latest cached interaction-based Customer Satisfaction Index (CSI) metrics.
    If the cache is stale or empty, it triggers a recalculation.
    """
    try:
        return enhanced_analytics_service.get_cached_csi_metrics(db, mode="interaction")
    except Exception as e:
        logger.error(f"Error retrieving interaction CSI metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/recalculate", response_model=InteractionMetricsResponse)
def recalculate_interaction_csi_metrics(db: Session = Depends(get_db)):
    """
    Force a recalculation of all interaction-based CSI metrics and update the cache.
    """
    try:
        return enhanced_analytics_service.calculate_and_cache_csi_metrics(db, mode="interaction")
    except Exception as e:
        logger.error(f"Error recalculating interaction CSI metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/historical", response_model=InteractionHistoricalMetricsResponse)
def get_interaction_historical_metrics(
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db)
):
    """
    Retrieve interaction-level aggregated CSI metrics over a specified date range.
    """
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date cannot be after end_date")
    
    try:
        return enhanced_analytics_service.get_historical_csi_metrics(
            db, start_date, end_date, mode="interaction"
        )
    except Exception as e:
        logger.error(f"Error retrieving historical interaction metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/interaction/{interaction_id}")
def get_interaction_details(
    interaction_id: int,
    db: Session = Depends(get_db)
):
    """
    Get detailed metrics and analysis for a specific interaction.
    """
    try:
        return enhanced_analytics_service.get_interaction_details(db, interaction_id)
    except Exception as e:
        logger.error(f"Error retrieving interaction {interaction_id} details: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/compare")
def compare_modes(
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db)
):
    """
    Compare CSI metrics between daily and interaction modes over a date range.
    Useful for understanding the differences between analysis approaches.
    """
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date cannot be after end_date")
    
    try:
        daily_metrics = enhanced_analytics_service.get_historical_csi_metrics(
            db, start_date, end_date, mode="daily"
        )
        interaction_metrics = enhanced_analytics_service.get_historical_csi_metrics(
            db, start_date, end_date, mode="interaction"
        )
        
        return {
            "daily_analysis": daily_metrics,
            "interaction_analysis": interaction_metrics,
            "comparison_period": {
                "start_date": start_date,
                "end_date": end_date
            }
        }
    except Exception as e:
        logger.error(f"Error comparing analysis modes: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))