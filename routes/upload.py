from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
import logging
import uuid

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
    
    # 1. Process file to get or create DailyAnalysis records
    logger.info(f"[{upload_id}] Starting file processing...")
    new_or_updated_analyses = file_service_optimized.get_or_create_daily_analyses(
        db=db,
        file_content=file_content,
        force_reprocess=force_reprocess
    )
    logger.info(f"[{upload_id}] Found or created {len(new_or_updated_analyses)} daily analyses to process.")

    if not new_or_updated_analyses:
        return UploadResponse(
            success=True,
            message="File processed. No new conversations or messages found to analyze.",
            upload_id=upload_id,
            jobs_created=0
        )

    # 2. Create batches from the analyses
    batches = batch_service.create_daily_analysis_batches(new_or_updated_analyses)
    logger.info(f"[{upload_id}] Created {len(batches)} batches from analyses.")

    # 3. Create a job record for each batch
    jobs = job_service.create_jobs_for_upload(upload_id, batches, db)
    
    # 4. Return Immediately
    return UploadResponse(
        success=True,
        message=f"File upload accepted. Created {len(jobs)} analysis jobs.",
        upload_id=upload_id,
        jobs_created=len(jobs)
    )

@router.get("/upload-status")
async def upload_status():
    """Get upload service status and limits"""
    return {
        "max_file_size_mb": settings.MAX_FILE_SIZE / (1024 * 1024),
        "accepted_formats": [".json"],
        "status": "ready"
    }
