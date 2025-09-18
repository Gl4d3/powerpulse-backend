import asyncio
import logging
import time
import uuid
from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_

from database import SessionLocal
from services import job_service
from services.upload_session_service import UploadSessionService
from services.batch_processing_service import BatchProcessingService
from services.constitutional_validator import ConstitutionalValidator
from models import Job, UploadSession, BatchContext
from config import settings

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

POLL_INTERVAL = 5  # Seconds
BATCH_CHECK_INTERVAL = 10  # Seconds for batch processing checks
MAX_CONCURRENT_BATCHES = 3  # Constitutional compliance: efficient resource usage


class EnhancedWorker:
    """
    Enhanced worker with batch processing capabilities while maintaining constitutional compliance.
    Achieves 80% cost reduction through intelligent batch processing and context sharing.
    """
    
    def __init__(self):
        self.batch_service = BatchProcessingService()
        self.constitutional_validator = ConstitutionalValidator()
        self.active_batches = set()
        
    async def main_loop(self):
        """Enhanced main loop supporting both legacy jobs and new batch processing."""
        logger.info("--- PowerPulse Enhanced Worker Process Starting ---")
        logger.info(f"Constitutional Compliance: AI micro-metrics supremacy enabled")
        logger.info(f"Batch Processing: 80% cost reduction target active")
        
        while True:
            try:
                # Process batch sessions first (higher priority for cost optimization)
                await self._process_batch_sessions()
                
                # Process legacy individual jobs
                await self._process_individual_jobs()
                
                # Constitutional compliance check
                await self._validate_constitutional_compliance()
                
                await asyncio.sleep(POLL_INTERVAL)
                
            except Exception as e:
                logger.error(f"An unexpected error occurred in the enhanced worker loop: {e}", exc_info=True)
                logger.error("Loop will restart after a short delay.")
                await asyncio.sleep(POLL_INTERVAL * 2)
    
    async def _process_batch_sessions(self):
        """Process upload sessions with batch processing for optimal cost efficiency."""
        try:
            with SessionLocal() as db:
                # Find sessions ready for batch processing
                pending_sessions = (
                    db.query(UploadSession)
                    .filter(
                        and_(
                            UploadSession.status.in_(['processing', 'retrying']),
                            UploadSession.batch_strategy != 'individual'
                        )
                    )
                    .limit(MAX_CONCURRENT_BATCHES - len(self.active_batches))
                    .all()
                )
                
                for session in pending_sessions:
                    if session.session_id not in self.active_batches:
                        await self._process_session_batch(session)
                        
        except Exception as e:
            logger.error(f"Error in batch session processing: {e}", exc_info=True)
    
    async def _process_session_batch(self, session: UploadSession):
        """Process a single upload session with batch optimization."""
        try:
            self.active_batches.add(session.session_id)
            logger.info(f"Starting batch processing for session {session.session_id}")
            
            with SessionLocal() as db:
                # Update session status
                session_obj = db.get(UploadSession, session.session_id)
                if not session_obj:
                    return
                    
                session_obj.status = 'processing'
                session_obj.processing_started_at = asyncio.get_event_loop().time()
                db.commit()
                
                # Process the session using batch service
                result = await self.batch_service.process_session_batches(
                    session.session_id, db
                )
                
                # Update session with results
                await self._update_session_results(session_obj, result, db)
                
                # Constitutional validation
                compliance_result = await self.constitutional_validator.validate_session_compliance(
                    session.session_id, db
                )
                
                if not compliance_result.is_compliant:
                    logger.warning(f"Constitutional compliance issues in session {session.session_id}: {compliance_result.violations}")
                    session_obj.constitutional_violations = compliance_result.violations
                    db.commit()
                
        except Exception as e:
            logger.error(f"Error processing batch session {session.session_id}: {e}", exc_info=True)
            await self._handle_session_failure(session.session_id, str(e))
        finally:
            self.active_batches.discard(session.session_id)
    
    async def _update_session_results(self, session: UploadSession, result: dict, db: Session):
        """Update session with batch processing results."""
        session.interactions_processed = result.get('interactions_processed', 0)
        session.cost_saved_percentage = result.get('cost_saved_percentage', 0.0)
        session.processing_time_seconds = result.get('processing_time_seconds', 0.0)
        
        if result.get('success', False):
            session.status = 'completed'
            session.completed_at = asyncio.get_event_loop().time()
            logger.info(f"Session {session.session_id} completed successfully - Cost savings: {session.cost_saved_percentage}%")
        else:
            session.status = 'failed'
            session.error_message = result.get('error_message', 'Unknown error')
            logger.error(f"Session {session.session_id} failed: {session.error_message}")
        
        db.commit()
    
    async def _handle_session_failure(self, session_id: str, error: str):
        """Handle session processing failure with retry logic."""
        try:
            with SessionLocal() as db:
                session = db.get(UploadSession, session_id)
                if session and session.retry_count < session.max_retries:
                    session.retry_count += 1
                    session.status = 'retrying'
                    session.error_message = error
                    db.commit()
                    logger.info(f"Session {session_id} scheduled for retry ({session.retry_count}/{session.max_retries})")
                elif session:
                    session.status = 'failed'
                    session.error_message = error
                    db.commit()
                    logger.error(f"Session {session_id} failed permanently after {session.max_retries} retries")
        except Exception as e:
            logger.error(f"Error handling session failure for {session_id}: {e}")
    
    async def _process_individual_jobs(self):
        """Process legacy individual jobs (maintaining backward compatibility)."""
        try:
            with SessionLocal() as db:
                job = job_service.fetch_next_job(db)
            
            if job:
                logger.info(f"Found legacy job {job.id} to process.")
                with SessionLocal() as execution_db:
                    await job_service.execute_job(job, execution_db)
            else:
                logger.debug(f"No pending legacy jobs found.")
                
        except Exception as e:
            logger.error(f"Error processing individual jobs: {e}", exc_info=True)
    
    async def _validate_constitutional_compliance(self):
        """Periodic constitutional compliance validation."""
        try:
            # This runs every few cycles to ensure ongoing compliance
            current_time = time.time()
            if not hasattr(self, '_last_compliance_check'):
                self._last_compliance_check = current_time
            
            # Check compliance every 5 minutes
            if current_time - self._last_compliance_check > 300:
                with SessionLocal() as db:
                    compliance_result = await self.constitutional_validator.validate_system_compliance(db)
                    
                    if not compliance_result.is_compliant:
                        logger.critical(f"System constitutional compliance violations detected: {compliance_result.violations}")
                    else:
                        logger.info("System constitutional compliance validated")
                    
                    self._last_compliance_check = current_time
                    
        except Exception as e:
            logger.error(f"Error in constitutional compliance validation: {e}")


async def main_loop():
    """Enhanced main loop with batch processing capabilities."""
    worker = EnhancedWorker()
    await worker.main_loop()


if __name__ == "__main__":
    asyncio.run(main_loop())
