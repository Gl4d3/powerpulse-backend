# This file contains the API routes for the Conversation Explorer feature.

import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date

from database import get_db
from services.analytics_service import analytics_service
from schemas import DailyAnalysisResponse, MessageResponse, PaginatedDailyAnalysisResponse

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/explorer/analyses", response_model=PaginatedDailyAnalysisResponse)
async def get_daily_analyses_for_explorer(
    start_date: date = Query(..., description="Start date for the query range."),
    end_date: date = Query(..., description="End date for the query range."),
    page: int = Query(1, ge=1, description="Page number to retrieve."),
    page_size: int = Query(50, ge=1, le=200, description="Number of records per page."),
    db: Session = Depends(get_db)
):
    """
    Provides a paginated list of all daily analyses within a specified date range,
    including key metrics and conversation details for the frontend explorer table.
    """
    try:
        return analytics_service.get_daily_analyses_with_details(
            db=db, 
            start_date=start_date, 
            end_date=end_date, 
            page=page, 
            page_size=page_size
        )
    except Exception as e:
        logger.error(f"Error fetching daily analyses for explorer: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred.")

@router.get("/explorer/transcript/{daily_analysis_id}", response_model=List[MessageResponse])
async def get_transcript_for_daily_analysis(
    daily_analysis_id: int,
    db: Session = Depends(get_db)
):
    """
    Retrieves the full message transcript for a specific daily analysis.
    """
    try:
        messages = analytics_service.get_transcript_for_daily_analysis(db, daily_analysis_id)
        if not messages:
            raise HTTPException(status_code=404, detail=f"No analysis or messages found for ID {daily_analysis_id}")
        return messages
    except Exception as e:
        logger.error(f"Error fetching transcript for daily_analysis_id {daily_analysis_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred.")
