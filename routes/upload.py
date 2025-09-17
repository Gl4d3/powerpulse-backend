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
        # COMPLETE INTERACTION ANALYSIS PIPELINE IMPLEMENTATION
        import json
        from services.file_service_optimized import OptimizedFileService
        from services.csi_analysis_pipeline import CSIAnalysisPipeline
        
        logger.info(f"[{upload_id}] Starting complete interaction analysis pipeline")
        
        # Step 1: Parse and create conversations/messages 
        try:
            data = json.loads(file_content)
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON format: {str(e)}")
        
        # Step 2: Process file to create conversations (without daily analysis)
        file_service = OptimizedFileService()
        conversations_created, messages_processed, upload_summary = await file_service.process_grouped_chats_json(
            file_content=file_content,
            db=db,
            upload_id=upload_id,
            force_reprocess=True
        )
        
        logger.info(f"[{upload_id}] Created {conversations_created} conversations, {messages_processed} messages")
        
        # Step 3: Get conversation IDs for interaction analysis
        from models import Conversation
        conversations = db.query(Conversation).all()
        conversation_ids = [c.id for c in conversations[-conversations_created:]]  # Get newly created conversations
        
        logger.info(f"[{upload_id}] Starting interaction analysis for {len(conversation_ids)} conversations")
        
        # Step 4: Run complete CSI analysis pipeline with dual CSI
        pipeline = CSIAnalysisPipeline(db)
        batch_result = await pipeline.process_batch(conversation_ids)
        
        logger.info(f"[{upload_id}] Pipeline completed: {batch_result.successful_conversations} successful, {batch_result.total_interactions} interactions analyzed")
        
        # Prepare response data
        conversations_processed = batch_result.total_conversations
        interactions_created = batch_result.total_interactions
        avg_csi = batch_result.avg_csi_score
        
        logger.info(f"[{upload_id}] DUAL CSI ANALYSIS COMPLETE - Conversations: {conversations_processed}, Interactions: {interactions_created}, Avg CSI: {avg_csi:.2f}")
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[{upload_id}] Error during interaction analysis: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred during interaction analysis.")

    end_time = time.time()
    processing_time_seconds = round(end_time - start_time, 2)
    
    return UploadResponse(
        success=True,
        message=f"Interaction analysis completed! {conversations_processed} conversations → {interactions_created} interactions analyzed with dual CSI (avg: {avg_csi:.2f})",
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
