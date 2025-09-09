# import logging
# from fastapi import APIRouter, HTTPException, Depends
# from typing import Dict, Any, List
# from sqlalchemy.orm import Session

# from services.progress_tracker import progress_tracker
# from database import get_db

# logger = logging.getLogger(__name__)
# router = APIRouter()

# def format_progress_response(progress) -> Dict[str, Any]:
#     """Helper to format a ProgressUpdate model object into a JSON response."""
#     if not progress:
#         return {}

#     duration = (progress.last_update - progress.start_time).total_seconds()
#     if progress.end_time:
#         duration = (progress.end_time - progress.start_time).total_seconds()

#     return {
#         "upload_id": progress.upload_id,
#         "filename": progress.filename,
#         "status": progress.status,
#         "progress_percentage": round(progress.progress_percentage, 1),
#         "current_stage": progress.current_stage,
#         "total_conversations": progress.total_conversations,
#         "processed_conversations": progress.processed_conversations,
#         "start_time": progress.start_time.isoformat(),
#         "last_update": progress.last_update.isoformat(),
#         "duration_seconds": round(duration, 1),
#         "last_error": progress.last_error
#     }

# @router.get("/progress/{upload_id}", response_model=Dict[str, Any])
# async def get_upload_progress(upload_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
#     """Get real-time progress for a specific upload"""
#     try:
#         progress = progress_tracker.get_progress(db, upload_id)
#         if not progress:
#             raise HTTPException(status_code=404, detail=f"Upload {upload_id} not found")
        
#         return format_progress_response(progress)
        
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Error getting progress for upload {upload_id}: {e}", exc_info=True)
#         raise HTTPException(status_code=500, detail="Internal server error")

# @router.get("/progress", response_model=Dict[str, Any])
# async def get_all_active_uploads(db: Session = Depends(get_db)) -> Dict[str, Any]:
#     """Get progress for all currently active uploads"""
#     try:
#         active_uploads = progress_tracker.get_all_active(db)
#         return {
#             "active_uploads": [format_progress_response(p) for p in active_uploads],
#             "total_active": len(active_uploads)
#         }
        
#     except Exception as e:
#         logger.error(f"Error getting active uploads: {e}", exc_info=True)
#         raise HTTPException(status_code=500, detail="Internal server error")

# @router.delete("/progress/{upload_id}")
# async def cancel_upload(upload_id: str, db: Session = Depends(get_db)) -> Dict[str, str]:
#     """Cancel an active upload (mark as failed)"""
#     try:
#         progress = progress_tracker.get_progress(db, upload_id)
#         if not progress:
#             raise HTTPException(status_code=404, detail=f"Upload {upload_id} not found")
        
#         if progress.status != 'processing':
#             raise HTTPException(status_code=400, detail=f"Upload {upload_id} is not active")
        
#         progress_tracker.complete_upload(db, upload_id, False)
        
#         return {"message": f"Upload {upload_id} has been cancelled"}
        
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Error cancelling upload {upload_id}: {e}", exc_info=True)
#         raise HTTPException(status_code=500, detail="Internal server error")