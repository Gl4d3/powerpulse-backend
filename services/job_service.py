import asyncio
import logging
from typing import List
from sqlalchemy.orm import Session
from models import Job, Conversation
from schemas import JobCreate
from config import settings
# Import AI services
from services import gemini_service, analytics_service
from services.REDACTED import gpt_service

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

async def process_job(job: Job, db: Session):
    """
    Processes a single job: acquires semaphore, calls AI service, and updates job status.
    """
    async with ai_semaphore:
        logger.info(f"Processing job {job.id}...")
        job.status = "in_progress"
        db.commit()

        try:
            # Determine which AI service to use
            if settings.AI_SERVICE.lower() == "gemini":
                ai_function = gemini_service.get_gemini_service(settings.GEMINI_API_KEY).analyze_conversations_batch
            else: # Assumes "openai"
                ai_function = gpt_service.analyze_conversations_batch

            # Call the AI service with the batch of conversations
            analysis_results = await ai_function(job.conversations)

            # Process and save results
            job.result = {"results": analysis_results}
            job.status = "completed"
            
            # Update the conversations with the new CSI analysis results
            for conv_data in analysis_results:
                conv_id = conv_data.get("id")
                if conv_id:
                    conv_to_update = db.query(Conversation).filter(Conversation.id == conv_id).first()
                    if conv_to_update:
                        # Update the four pillar scores from the AI analysis
                        conv_to_update.effectiveness_score = conv_data.get("effectiveness_score")
                        conv_to_update.efficiency_score = conv_data.get("efficiency_score")
                        conv_to_update.effort_score = conv_data.get("effort_score")
                        conv_to_update.empathy_score = conv_data.get("empathy_score")
                        
                        # Calculate and set the final CSI score
                        analytics_service.calculate_and_set_csi_score(conv_to_update)

        except Exception as e:
            logger.error(f"Job {job.id} failed: {e}")
            job.status = "failed"
            job.result = {"error": str(e)}
        
        finally:
            db.commit()
            logger.info(f"Job {job.id} finished with status: {job.status}")
