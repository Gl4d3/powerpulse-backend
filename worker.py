import asyncio
import logging
import time
from sqlalchemy.orm import Session
from database import SessionLocal
from services import job_service

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

POLL_INTERVAL = 5  # Seconds

async def main_loop():
    """The main loop for the worker process."""
    logger.info("--- PowerPulse Worker Process Starting ---")
    while True:
        try:
            with SessionLocal() as db:
                job = job_service.fetch_next_job(db)
            
            if job:
                logger.info(f"Found job {job.id} to process.")
                # We need a new session for the execution context
                with SessionLocal() as execution_db:
                    await job_service.execute_job(job, execution_db)
            else:
                # No job found, wait for a bit
                logger.debug(f"No pending jobs found. Sleeping for {POLL_INTERVAL} seconds.")
                time.sleep(POLL_INTERVAL)

        except Exception as e:
            logger.error(f"An unexpected error occurred in the main worker loop: {e}", exc_info=True)
            logger.error("Loop will restart after a short delay.")
            time.sleep(POLL_INTERVAL * 2) # Wait a bit longer after a major error

if __name__ == "__main__":
    asyncio.run(main_loop())
