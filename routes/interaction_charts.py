"""
API endpoints for providing interaction-based chart data.
Charts showing trends and patterns from interaction analysis rather than daily analysis.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date
import logging
from typing import List, Dict, Any

from database import get_db
from services.enhanced_analytics_service import enhanced_analytics_service
from models import InteractionAnalysis

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/sentiment-trend")
async def get_interaction_sentiment_trend(
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db)
):
    """
    Provides daily average sentiment scores over a date range from interaction analyses,
    formatted for charts.
    """
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date cannot be after end_date")
        
    try:
        return await enhanced_analytics_service.get_sentiment_trend(db, start_date, end_date, mode="interaction")
    except Exception as e:
        logger.error(f"Error getting interaction sentiment trend data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error getting sentiment trend data")

@router.get("/csi-trend")
async def get_interaction_csi_trend(
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db)
):
    """
    Provides daily average CSI and pillar scores over a date range from interaction analyses,
    formatted for charts.
    """
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date cannot be after end_date")
        
    try:
        return await enhanced_analytics_service.get_csi_trend(db, start_date, end_date, mode="interaction")
    except Exception as e:
        logger.error(f"Error getting interaction CSI trend data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error getting CSI trend data")

@router.get("/interaction-distribution")
async def get_interaction_distribution(
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db)
):
    """
    Provides distribution of interaction types and complexities over a date range.
    """
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date cannot be after end_date")
        
    try:
        # Get interaction type distribution
        type_distribution = db.query(
            InteractionAnalysis.interaction_type,
            func.count(InteractionAnalysis.id).label("count")
        ).filter(
            InteractionAnalysis.interaction_start >= start_date,
            InteractionAnalysis.interaction_end <= end_date,
            InteractionAnalysis.interaction_type.isnot(None)
        ).group_by(InteractionAnalysis.interaction_type).all()
        
        # Get complexity distribution  
        complexity_distribution = db.query(
            InteractionAnalysis.interaction_complexity,
            func.count(InteractionAnalysis.id).label("count")
        ).filter(
            InteractionAnalysis.interaction_start >= start_date,
            InteractionAnalysis.interaction_end <= end_date,
            InteractionAnalysis.interaction_complexity.isnot(None)
        ).group_by(InteractionAnalysis.interaction_complexity).all()
        
        return {
            "interaction_types": [
                {"type": type_name, "count": count} 
                for type_name, count in type_distribution
            ],
            "complexity_levels": [
                {"complexity": complexity, "count": count}
                for complexity, count in complexity_distribution
            ],
            "date_range": {
                "start_date": start_date,
                "end_date": end_date
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting interaction distribution data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error getting interaction distribution data")

@router.get("/interaction-duration-trend")
async def get_interaction_duration_trend(
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db)
):
    """
    Shows trends in interaction duration over time.
    """
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date cannot be after end_date")
        
    try:
        # Group by date and calculate average duration
        duration_trend = db.query(
            func.date(InteractionAnalysis.interaction_start).label("date"),
            func.avg(InteractionAnalysis.interaction_duration).label("avg_duration"),
            func.count(InteractionAnalysis.id).label("interaction_count")
        ).filter(
            InteractionAnalysis.interaction_start >= start_date,
            InteractionAnalysis.interaction_end <= end_date,
            InteractionAnalysis.interaction_duration.isnot(None)
        ).group_by(func.date(InteractionAnalysis.interaction_start)).order_by("date").all()
        
        return {
            "duration_trend": [
                {
                    "date": str(date_val),
                    "avg_duration_minutes": round(avg_duration, 2) if avg_duration else 0,
                    "interaction_count": interaction_count
                }
                for date_val, avg_duration, interaction_count in duration_trend
            ],
            "date_range": {
                "start_date": start_date,
                "end_date": end_date
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting interaction duration trend data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error getting duration trend data")

@router.get("/csi-by-complexity")
async def get_csi_by_interaction_complexity(
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db)
):
    """
    Shows CSI scores grouped by interaction complexity levels.
    """
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date cannot be after end_date")
        
    try:
        complexity_csi = db.query(
            InteractionAnalysis.interaction_complexity,
            func.avg(InteractionAnalysis.csi_score).label("avg_csi"),
            func.avg(InteractionAnalysis.effectiveness_score).label("avg_effectiveness"),
            func.avg(InteractionAnalysis.efficiency_score).label("avg_efficiency"),
            func.avg(InteractionAnalysis.effort_score).label("avg_effort"),
            func.avg(InteractionAnalysis.empathy_score).label("avg_empathy"),
            func.count(InteractionAnalysis.id).label("count")
        ).filter(
            InteractionAnalysis.interaction_start >= start_date,
            InteractionAnalysis.interaction_end <= end_date,
            InteractionAnalysis.interaction_complexity.isnot(None),
            InteractionAnalysis.csi_score.isnot(None)
        ).group_by(InteractionAnalysis.interaction_complexity).all()
        
        return {
            "csi_by_complexity": [
                {
                    "complexity": complexity,
                    "avg_csi_score": round(avg_csi, 2) if avg_csi else 0,
                    "avg_effectiveness_score": round(avg_effectiveness, 2) if avg_effectiveness else 0,
                    "avg_efficiency_score": round(avg_efficiency, 2) if avg_efficiency else 0,
                    "avg_effort_score": round(avg_effort, 2) if avg_effort else 0,
                    "avg_empathy_score": round(avg_empathy, 2) if avg_empathy else 0,
                    "sample_count": count
                }
                for complexity, avg_csi, avg_effectiveness, avg_efficiency, avg_effort, avg_empathy, count in complexity_csi
            ],
            "date_range": {
                "start_date": start_date,
                "end_date": end_date
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting CSI by complexity data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error getting CSI by complexity data")

@router.get("/interaction-efficiency")
async def get_interaction_efficiency_metrics(
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db)
):
    """
    Shows efficiency metrics specific to interactions: duration vs message count,
    response times, turns per interaction, etc.
    """
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date cannot be after end_date")
        
    try:
        efficiency_data = db.query(
            func.date(InteractionAnalysis.interaction_start).label("date"),
            func.avg(InteractionAnalysis.interaction_duration).label("avg_duration"),
            func.avg(InteractionAnalysis.message_count).label("avg_messages"),
            func.avg(InteractionAnalysis.turns_count).label("avg_turns"),
            func.avg(InteractionAnalysis.first_response_time).label("avg_first_response"),
            func.avg(InteractionAnalysis.avg_response_time).label("avg_response_time"),
            func.count(InteractionAnalysis.id).label("interaction_count")
        ).filter(
            InteractionAnalysis.interaction_start >= start_date,
            InteractionAnalysis.interaction_end <= end_date
        ).group_by(func.date(InteractionAnalysis.interaction_start)).order_by("date").all()
        
        return {
            "efficiency_metrics": [
                {
                    "date": str(date_val),
                    "avg_duration_minutes": round(avg_duration, 2) if avg_duration else 0,
                    "avg_message_count": round(avg_messages, 1) if avg_messages else 0,
                    "avg_turns_count": round(avg_turns, 1) if avg_turns else 0,
                    "avg_first_response_seconds": round(avg_first_response, 1) if avg_first_response else 0,
                    "avg_response_time_seconds": round(avg_response_time, 1) if avg_response_time else 0,
                    "interaction_count": interaction_count
                }
                for date_val, avg_duration, avg_messages, avg_turns, avg_first_response, avg_response_time, interaction_count in efficiency_data
            ],
            "date_range": {
                "start_date": start_date,
                "end_date": end_date
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting interaction efficiency metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error getting efficiency metrics")