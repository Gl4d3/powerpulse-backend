from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, Query
from sqlalchemy.orm import Session
import time
import logging

from database import get_db
from services.file_service_optimized import optimized_file_service
from services.analytics_service import analytics_service
from schemas import UploadResponse, ErrorResponse
from config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/upload-json", response_model=UploadResponse)
async def upload_json(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    force_reprocess: bool = Query(False, description="Force reprocessing of already processed chat_ids"),
    db: Session = Depends(get_db)
):
    """
    Upload and process Facebook chat data in grouped_chats JSON format.
    Triggers parsing, GPT analysis, and metrics calculation.
    """
    try:
        # Validate file
        if not file.filename.endswith('.json'):
            raise HTTPException(status_code=400, detail="File must be a JSON file")
        
        if file.size and file.size > settings.MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail=f"File too large. Maximum size: {settings.MAX_FILE_SIZE} bytes")
        
        # Read file content
        content = await file.read()
        
        if not content:
            raise HTTPException(status_code=400, detail="File is empty")
        
        try:
            file_content = content.decode('utf-8')
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="File must be UTF-8 encoded")
        
        # Start processing
        start_time = time.time()
        logger.info(f"Starting processing of file: {file.filename}")
        
        # Process the file with optimized service
        conversations_processed, messages_processed, upload_id = await optimized_file_service.process_grouped_chats_json(
            file_content, db, force_reprocess=force_reprocess
        )
        
        # Recalculate metrics in background
        background_tasks.add_task(analytics_service.calculate_and_cache_csi_metrics, db)
        
        processing_time = time.time() - start_time
        
        logger.info(f"Successfully processed {conversations_processed} conversations, "
                   f"{messages_processed} messages in {processing_time:.2f}s")
        
        return UploadResponse(
            success=True,
            message=f"Successfully processed {conversations_processed} conversations",
            conversations_processed=conversations_processed,
            messages_processed=messages_processed,
            processing_time_seconds=round(processing_time, 2),
            upload_id=upload_id
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error processing upload: {e}")
        raise HTTPException(status_code=500, detail="Internal server error processing file")

@router.get("/upload-status")
async def upload_status():
    """Get upload service status and limits"""
    return {
        "max_file_size_mb": settings.MAX_FILE_SIZE / (1024 * 1024),
        "accepted_formats": [".json"],
        "status": "ready"
    }
