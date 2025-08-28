import asyncio
import logging
from typing import List
from sqlalchemy.orm import Session, joinedload
from models import Job, DailyAnalysis, Conversation
from schemas import JobCreate
from config import settings
# Import AI services
from services import gemini_service, analytics_service
from datetime import datetime
from services.REDACTED import gpt_service
from database import SessionLocal
import traceback

logger = logging.getLogger(__name__)

# Global semaphore to limit concurrency
ai_semaphore = asyncio.Semaphore(settings.AI_CONCURRENCY)

async def create_jobs_for_upload(upload_id: str, batches: List[List[DailyAnalysis]], db: Session) -> List[Job]:
    """
    Creates Job records in the database for each batch of DailyAnalysis objects.
    """
    jobs = []
    for batch in batches:
        job = Job(
            upload_id=upload_id,
            status="pending",
            daily_analyses=batch
        )
        db.add(job)
        jobs.append(job)
    
    db.commit()
    for job in jobs:
        db.refresh(job)
        
    logger.info(f"Created {len(jobs)} jobs for upload {upload_id}")
    return jobs

import traceback

async def process_job(job_id: int):
    """
    Processes a single job: calls the AI service for a batch of DailyAnalysis objects,
    updates them with the results, and calculates their CSI scores.
    """
    async with ai_semaphore:
        with SessionLocal() as db:
            # Eagerly load all necessary relationships to prevent lazy loading issues in the background task
            job = db.query(Job).options(
                joinedload(Job.daily_analyses)
                .joinedload(DailyAnalysis.conversation)
                .joinedload(Conversation.messages)
            ).filter(Job.id == job_id).with_for_update().first()

            if not job:
                logger.error(f"Job with ID {job_id} not found.")
                return

            if job.status != "pending":
                logger.warning(f"Job {job.id} is already in status {job.status}. Skipping.")
                return

            logger.info(f"Starting Job {job.id} for Upload {job.upload_id}...")
            job.status = "in_progress"
            db.commit()

            try:
                if settings.AI_SERVICE.lower() == "gemini":
                    ai_function = gemini_service.get_gemini_service(settings.GEMINI_API_KEY).analyze_daily_analyses_batch
                else:
                    from services.REDACTED import gpt_service
                    ai_function = gpt_service.analyze_daily_analyses_batch

                analysis_results = await ai_function(job.daily_analyses)

                job.result = {"results": analysis_results}
                
                # Check if any of the results were fallbacks
                if any(res.get("error") == "analysis_failed" for res in analysis_results):
                    job.status = "failed"
                    logger.warning(f"Job {job.id} completed with status: FAILED (AI analysis fallback)")
                else:
                    job.status = "completed"
                    logger.info(f"Job {job.id} completed with status: SUCCESS")

                analysis_map = {res.get("daily_analysis_id"): res for res in analysis_results}

                for analysis_obj in job.daily_analyses:
                    result_data = analysis_map.get(analysis_obj.id)
                    if result_data and not result_data.get("error"):
                        # Update metrics only if analysis was successful
                        analysis_obj.sentiment_score = result_data.get("sentiment_score")
                        analysis_obj.sentiment_shift = result_data.get("sentiment_shift")
                        analysis_obj.resolution_achieved = result_data.get("resolution_achieved")
                        analysis_obj.fcr_score = result_data.get("fcr_score")
                        analysis_obj.ces = result_data.get("ces")
                        analysis_obj.first_response_time = result_data.get("first_response_time")
                        analysis_obj.avg_response_time = result_data.get("avg_response_time")
                        analysis_obj.total_handling_time = result_data.get("total_handling_time")
                        
                        analytics_service.calculate_and_set_daily_csi_score(analysis_obj)

            except Exception as e:
                logger.error(f"Job {job.id} failed catastrophically", exc_info=True)
                job.status = "failed"
                # Capture the full traceback in the result for debugging
                job.result = {"error": str(e), "traceback": traceback.format_exc()}
            
            finally:
                job.completed_at = datetime.utcnow()
                db.commit()
                if job.status == 'failed':
                    logger.error(f"Batch (Job {job.id}) finished with status: {job.status}")
                else:
                    logger.info(f"Batch (Job {job.id}) finished with status: {job.status}")
