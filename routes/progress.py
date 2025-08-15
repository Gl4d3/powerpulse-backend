import logging
from fastapi import APIRouter, HTTPException
from typing import Dict, Any

from services.progress_tracker import progress_tracker

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/progress/{upload_id}")
async def get_upload_progress(upload_id: str) -> Dict[str, Any]:
    """Get real-time progress for a specific upload"""
    try:
        progress = progress_tracker.get_progress(upload_id)
        
        if not progress:
            raise HTTPException(status_code=404, detail=f"Upload {upload_id} not found")
        
        # Format response for frontend
        return {
            "upload_id": upload_id,
            "status": progress['status'],
            "progress_percentage": round(progress['progress_percentage'], 1),
            "current_stage": progress['current_stage'],
            "processed_conversations": progress['processed_conversations'],
            "total_conversations": progress['total_conversations'],
            "details": progress.get('details', ''),
            "start_time": progress['start_time'].isoformat(),
            "last_update": progress['last_update'].isoformat(),
            "duration_seconds": (progress['last_update'] - progress['start_time']).total_seconds(),
            "statistics": {
                "filtered_autoresponses": progress.get('filtered_autoresponses', 0),
                "gpt_calls_made": progress.get('gpt_calls_made', 0),
                "errors_count": len(progress.get('errors', []))
            },
            "errors": progress.get('errors', [])[-5:]  # Last 5 errors only
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting progress for upload {upload_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/progress")
async def get_all_active_uploads() -> Dict[str, Any]:
    """Get progress for all currently active uploads"""
    try:
        active_uploads = progress_tracker.get_all_active()
        
        formatted_uploads = {}
        for upload_id, progress in active_uploads.items():
            formatted_uploads[upload_id] = {
                "status": progress['status'],
                "progress_percentage": round(progress['progress_percentage'], 1),
                "current_stage": progress['current_stage'],
                "processed_conversations": progress['processed_conversations'],
                "total_conversations": progress['total_conversations'],
                "start_time": progress['start_time'].isoformat(),
                "duration_seconds": (progress['last_update'] - progress['start_time']).total_seconds()
            }
        
        return {
            "active_uploads": formatted_uploads,
            "total_active": len(formatted_uploads)
        }
        
    except Exception as e:
        logger.error(f"Error getting active uploads: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/progress/{upload_id}")
async def cancel_upload(upload_id: str) -> Dict[str, str]:
    """Cancel an active upload (mark as failed)"""
    try:
        progress = progress_tracker.get_progress(upload_id)
        
        if not progress:
            raise HTTPException(status_code=404, detail=f"Upload {upload_id} not found")
        
        if progress['status'] != 'processing':
            raise HTTPException(status_code=400, detail=f"Upload {upload_id} is not active")
        
        await progress_tracker.complete_upload(upload_id, False)
        
        return {"message": f"Upload {upload_id} has been cancelled"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling upload {upload_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")