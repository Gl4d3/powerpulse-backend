"""
Simple worker for processing jobs
"""
import asyncio
import logging
from database import SessionLocal
from services import job_service

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

POLL_INTERVAL = 5  # Seconds

async def simple_worker():
    """Simple worker loop to process pending jobs."""
    logger.info("--- PowerPulse Simple Worker Process Starting ---")
    
    while True:
        try:
            # Process individual jobs
            with SessionLocal() as db:
                job = job_service.fetch_next_job(db)
            
            if job:
                logger.info(f"Found job {job.id} to process - Status: {job.status}")
                with SessionLocal() as execution_db:
                    await job_service.execute_job(job, execution_db)
                    logger.info(f"Completed job {job.id}")
            else:
                logger.debug("No pending jobs found.")
                
            await asyncio.sleep(POLL_INTERVAL)
                
        except Exception as e:
            logger.error(f"Error in worker loop: {e}", exc_info=True)
            await asyncio.sleep(POLL_INTERVAL * 2)

if __name__ == "__main__":
    asyncio.run(simple_worker())