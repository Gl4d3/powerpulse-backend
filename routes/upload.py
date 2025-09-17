from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
import logging
import uuid
import time

from database import get_db
from services import file_service_optimized, batch_service, job_service
from schemas import UploadResponse
from config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/upload-json", response_model=UploadResponse, status_code=202)
async def upload_json(
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
    force_reprocess: bool = Query(False, description="Force reprocessing of already processed chat_ids")
):
    """
    Accepts a JSON file, creates analysis jobs, and returns a unique ID for tracking.
    The processing now happens via a separate worker process, not a background task.
    """
    if not file.filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="File must be a JSON file")
    
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="File is empty")
        
    try:
        file_content = content.decode('utf-8')
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded")

    upload_id = str(uuid.uuid4())
    logger.info(f"[{upload_id}] Starting file processing...")
    start_time = time.time()

    try:
        conversations_processed, messages_processed, _ = await file_service_optimized.optimized_file_service.process_grouped_chats_json(
            db=db,
            file_content=file_content,
            upload_id=upload_id,
            force_reprocess=force_reprocess
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[{upload_id}] Unhandled error during file processing: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred during file processing.")

    end_time = time.time()
    processing_time_seconds = round(end_time - start_time, 2)

    if conversations_processed == 0:
        return UploadResponse(
            success=True,
            message="File processed. No new conversations or messages found to analyze.",
            upload_id=upload_id,
            conversations_processed=0,
            messages_processed=0,
            processing_time_seconds=processing_time_seconds
        )
    
    return UploadResponse(
        success=True,
        message=f"File upload accepted. Found {conversations_processed} conversations and {messages_processed} new messages to analyze.",
        upload_id=upload_id,
        conversations_processed=conversations_processed,
        messages_processed=messages_processed,
        processing_time_seconds=processing_time_seconds
    )

@router.post("/upload-interaction-json", response_model=UploadResponse, status_code=202)
async def upload_interaction_json(
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
    mode: str = Query("interaction", description="Analysis mode: 'interaction' for AI-enhanced analysis")
):
    """
    Uploads JSON file for AI-enhanced interaction analysis pipeline.
    Triggers CSI analysis with hybrid boundary detection instead of daily analysis.
    """
    if not file.filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="File must be a JSON file")
    
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="File is empty")
        
    try:
        file_content = content.decode('utf-8')
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded")

    upload_id = str(uuid.uuid4())
    logger.info(f"[{upload_id}] Starting interaction analysis for mode: {mode}")
    start_time = time.time()

    try:
        # Parse and create conversations/messages (without daily analysis jobs)
        from services.csi_analysis_pipeline import CSIAnalysisPipeline
        import json
        
        # Parse JSON content
        try:
            data = json.loads(file_content)
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON format: {str(e)}")
        
        # For now, create a job to trigger interaction analysis via worker
        # Note: This is a placeholder - full integration needs worker support for interaction mode
        job_data = {
            "upload_id": upload_id,
            "mode": mode,
            "file_content": file_content,
            "analysis_type": "interaction_analysis"
        }
        
        # Create job for worker to process
        job_service.create_interaction_analysis_job(db, upload_id, job_data)
        
        conversations_processed = len(data) if isinstance(data, dict) else 1
        messages_processed = sum(len(msgs) for msgs in data.values()) if isinstance(data, dict) else 0
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[{upload_id}] Error during interaction analysis setup: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred during interaction analysis setup.")

    end_time = time.time()
    processing_time_seconds = round(end_time - start_time, 2)
    
    return UploadResponse(
        success=True,
        message=f"Interaction analysis accepted. Processing {conversations_processed} conversations with AI-enhanced pipeline.",
        upload_id=upload_id,
        conversations_processed=conversations_processed,
        messages_processed=messages_processed,
        processing_time_seconds=processing_time_seconds
    )

@router.get("/upload-status")
async def upload_status():
    """Get upload service status and limits"""
    return {
        "max_file_size_mb": settings.MAX_FILE_SIZE / (1024 * 1024),
        "accepted_formats": [".json"],
        "status": "ready",
        "analysis_modes": ["daily", "interaction"]
    }
