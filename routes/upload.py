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

import uuid
from services.file_service_optimized import process_uploaded_file

@router.post("/upload-json", response_model=UploadResponse, status_code=202)
async def upload_json(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    force_reprocess: bool = Query(False, description="Force reprocessing of already processed chat_ids")
):
    """
    Accepts a JSON file, returns a unique ID for tracking, and starts the
    processing in the background.
    """
    # --- 1. Immediate Validation and Response ---
    if not file.filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="File must be a JSON file")
    
    if file.size and file.size > settings.MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail=f"File too large. Maximum size: {settings.MAX_FILE_SIZE} bytes")
    
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="File is empty")
        
    try:
        file_content = content.decode('utf-8')
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded")

    upload_id = str(uuid.uuid4())
    
    # --- 2. Delegate Processing to Background Task ---
    background_tasks.add_task(
        process_uploaded_file,
        file_content=file_content,
        upload_id=upload_id,
        force_reprocess=force_reprocess
    )
    
    # --- 3. Return Immediately ---
    return UploadResponse(
        success=True,
        message="File upload accepted. Processing has started in the background.",
        upload_id=upload_id,
        conversations_processed=0, # These values are now tracked by the progress system
        messages_processed=0,
        processing_time_seconds=0
    )

@router.get("/upload-status")
async def upload_status():
    """Get upload service status and limits"""
    return {
        "max_file_size_mb": settings.MAX_FILE_SIZE / (1024 * 1024),
        "accepted_formats": [".json"],
        "status": "ready"
    }
