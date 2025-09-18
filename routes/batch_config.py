"""
Batch configuration routes for PowerPulse.
Provides batch processing configuration and performance metrics.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import logging
from datetime import datetime
from typing import Dict, Any

from database import get_db
from schemas import BatchConfig
from config import settings
from services.batch_processing_service import BatchProcessingService

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/batch-config", response_model=BatchConfig)
async def get_batch_configuration(db: Session = Depends(get_db)):
    """
    Get current batch processing configuration and performance metrics.
    Provides optimization status and constitutional compliance targets.
    """
    try:
        # Get current configuration from BatchProcessingService
        batch_service = BatchProcessingService(db)
        config = batch_service.config
        
        # Calculate current performance metrics
        current_performance = await _get_current_performance_metrics(db)
        
        # Build response
        batch_config = BatchConfig(
            context_window_size=config.context_window_size,
            batch_size_interactions=config.batch_size_optimal,
            max_concurrent_batches=config.max_concurrent_batches,
            timeout_seconds=int(config.timeout_per_batch),
            performance_targets={
                "interactions_per_second": config.target_processing_speed,
                "api_cost_reduction_percentage": config.target_cost_reduction,
                "success_rate_minimum": 0.95  # 95% success rate target
            },
            current_performance=current_performance,
            optimization_enabled=True,
            last_updated=datetime.utcnow().isoformat()
        )
        
        return batch_config
        
    except Exception as e:
        logger.error(f"Error getting batch configuration: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal error retrieving batch configuration")

async def _get_current_performance_metrics(db: Session) -> Dict[str, Any]:
    """Get current performance metrics from recent batch processing."""
    try:
        # Query recent batch processing performance
        from models import BatchContext
        from sqlalchemy import func, desc
        
        # Get performance from recent completed batches
        recent_batches = db.query(BatchContext).filter(
            BatchContext.status == "completed"
        ).order_by(desc(BatchContext.completed_at)).limit(50).all()
        
        if not recent_batches:
            return {
                "avg_processing_speed": None,
                "actual_cost_reduction": None,
                "recent_success_rate": None
            }
        
        # Calculate average processing speed
        processing_speeds = []
        cost_reductions = []
        
        for batch in recent_batches:
            if batch.processing_time and batch.interactions_count:
                speed = batch.interactions_count / batch.processing_time
                processing_speeds.append(speed)
            
            # Extract cost reduction from result data
            if batch.result_data and "optimization_data" in batch.result_data:
                opt_data = batch.result_data["optimization_data"]
                if "estimated_cost_reduction" in opt_data:
                    cost_reductions.append(opt_data["estimated_cost_reduction"])
        
        # Calculate success rate from all recent batches
        total_recent = len(recent_batches)
        successful_recent = len([b for b in recent_batches if b.status == "completed"])
        success_rate = successful_recent / total_recent if total_recent > 0 else None
        
        return {
            "avg_processing_speed": sum(processing_speeds) / len(processing_speeds) if processing_speeds else None,
            "actual_cost_reduction": sum(cost_reductions) / len(cost_reductions) if cost_reductions else None,
            "recent_success_rate": success_rate
        }
        
    except Exception as e:
        logger.error(f"Error calculating performance metrics: {str(e)}")
        return {
            "avg_processing_speed": None,
            "actual_cost_reduction": None,
            "recent_success_rate": None
        }