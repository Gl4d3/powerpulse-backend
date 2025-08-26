from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date

from database import get_db
from services.analytics_service import analytics_service
from schemas import CSIMetricsResponse, HistoricalMetricsResponse

router = APIRouter()

@router.get("/", response_model=CSIMetricsResponse)
def get_csi_metrics(db: Session = Depends(get_db)):
    """
    Retrieve the latest cached Customer Satisfaction Index (CSI) metrics.
    If the cache is stale or empty, it triggers a recalculation.
    """
    try:
        return analytics_service.get_cached_csi_metrics(db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/recalculate", response_model=CSIMetricsResponse)
def recalculate_csi_metrics(db: Session = Depends(get_db)):
    """
    Force a recalculation of all CSI metrics and update the cache.
    """
    try:
        return analytics_service.calculate_and_cache_csi_metrics(db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/historical", response_model=HistoricalMetricsResponse)
def get_historical_metrics(
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db)
):
    """
    Retrieve daily aggregated CSI metrics over a specified date range.
    The aggregation is based on the `social_create_time` of the messages
    within the conversations.
    """
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date cannot be after end_date")
    
    try:
        return analytics_service.get_historical_csi_metrics(db, start_date, end_date)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
