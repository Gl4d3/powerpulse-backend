import asyncio
import logging
from typing import List
from sqlalchemy.orm import Session
from models import Job, Conversation
from schemas import JobCreate
from config import settings
# Import AI services
from services import gemini_service, analytics_service
from datetime import datetime
from services.REDACTED import gpt_service
from database import SessionLocal

logger = logging.getLogger(__name__)

# Global semaphore to limit concurrency
ai_semaphore = asyncio.Semaphore(settings.AI_CONCURRENCY)

async def create_jobs_for_upload(upload_id: str, batches: List[List[Conversation]], db: Session) -> List[Job]:
    """
    Creates Job records in the database for each batch of conversations.
    """
    jobs = []
    for batch in batches:
        job = Job(
            upload_id=upload_id,
            status="pending",
            conversations=batch
        )
        db.add(job)
        jobs.append(job)
    
    db.commit()
    for job in jobs:
        db.refresh(job)
        
    logger.info(f"Created {len(jobs)} jobs for upload {upload_id}")
    return jobs

async def process_job(job_id: int):
    """
    Processes a single job: creates a new DB session, calls AI service, and updates job status.
    """
    async with ai_semaphore:
        with SessionLocal() as db:
            # Use with_for_update to lock the job row during processing
            job = db.query(Job).filter(Job.id == job_id).with_for_update().first()
            if not job:
                logger.error(f"Job with ID {job_id} not found.")
                return

            if job.status != "pending":
                logger.warning(f"Job {job.id} is already in status {job.status}. Skipping.")
                return

            logger.info(f"Processing job {job.id}...")
            job.status = "in_progress"
            db.commit()

            try:
                # Determine which AI service to use
                if settings.AI_SERVICE.lower() == "gemini":
                    ai_function = gemini_service.get_gemini_service(settings.GEMINI_API_KEY).analyze_conversations_batch
                else: # Assumes "openai"
                    from services.REDACTED import gpt_service
                    ai_function = gpt_service.analyze_conversations_batch

                # The job.conversations relationship should load within the new session
                analysis_results = await ai_function(job.conversations)

                # Process and save results
                job.result = {"results": analysis_results}
                job.status = "completed"
                
                # Create a mapping of fb_chat_id to conversation object for efficient updates
                conv_map = {conv.fb_chat_id: conv for conv in job.conversations}

                for conv_data in analysis_results:
                    fb_chat_id = conv_data.get("fb_chat_id")
                    if fb_chat_id and fb_chat_id in conv_map:
                        conv_to_update = conv_map[fb_chat_id]
                        
                        # Update the five micro-metric scores from the AI analysis
                        conv_to_update.resolution_achieved = conv_data.get("resolution_achieved")
                        conv_to_update.fcr_score = conv_data.get("fcr_score")
                        conv_to_update.response_time_score = conv_data.get("response_time_score")
                        conv_to_update.customer_effort_score = conv_data.get("customer_effort_score")
                        conv_to_update.empathy_score = conv_data.get("empathy_score")
                        
                        # Calculate and set the pillar scores and the final CSI score
                        analytics_service.calculate_and_set_csi_score(conv_to_update)

            except Exception as e:
                logger.error(f"Job {job.id} failed: {e}", exc_info=True)
                job.status = "failed"
                job.result = {"error": str(e)}
            
            finally:
                job.completed_at = datetime.utcnow()
                db.commit()
                logger.info(f"Job {job.id} finished with status: {job.status}")
