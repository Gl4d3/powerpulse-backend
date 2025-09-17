import asyncio
import logging
import traceback
import time
import os
from pathlib import Path
from datetime import datetime, timedelta

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_

from database import SessionLocal
from models import Job, DailyAnalysis, Conversation, JobMetric
from config import settings
from services import gemini_service, analytics_service, time_metric_service

logger = logging.getLogger(__name__)


def create_jobs_for_upload(upload_id: str, batches: list[list[DailyAnalysis]], db: Session) -> list[Job]:
    """
    Creates Job records in the database for each batch of DailyAnalysis objects.
    """
    jobs = []
    for batch in batches:
        job = Job(
            upload_id=upload_id,
            status="pending",
            run_at=datetime.utcnow(),
            daily_analyses=batch
        )
        db.add(job)
        jobs.append(job)
    
    db.commit()
    for job in jobs:
        db.refresh(job)
        
    logger.info(f"Created {len(jobs)} jobs for upload {upload_id}")
    return jobs


def create_interaction_analysis_job(db: Session, upload_id: str, job_data: dict) -> Job:
    """
    Creates a Job record for interaction analysis pipeline processing.
    
    Args:
        db: Database session
        upload_id: Unique upload identifier
        job_data: Dictionary containing analysis parameters and file content
        
    Returns:
        Created Job instance
    """
    job = Job(
        upload_id=upload_id,
        task_name="interaction_analysis",
        status="pending",
        run_at=datetime.utcnow(),
        result=job_data  # Store job data in result field for worker processing
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    
    logger.info(f"Created interaction analysis job {job.id} for upload {upload_id}")
    return job


def fetch_next_job(db: Session) -> Job | None:
    """
    Atomically fetches the next available job that is ready to run.
    It locks the selected job row to prevent race conditions with other workers.
    """
    now = datetime.utcnow()
    job = db.query(Job).filter(
        and_(
            or_(Job.status == 'pending', Job.status == 'retryable_failure'),
            Job.run_at <= now
        )
    ).order_by(Job.run_at).with_for_update(skip_locked=True).first()
    
    if job:
        job.status = 'running'
        job.started_at = now
        db.commit()
        logger.info(f"Worker picked up and locked Job ID: {job.id}")
        return job
    return None

async def execute_job(job: Job, db: Session):
    """
    Processes a single job: calls the AI service, and upon success, updates
    all related analyses with the new data and calculates CSI scores.
    """
    logger.info(f"Executing Job ID: {job.id} (Retry: {job.retry_count}/{job.max_retries})")
    response_text = None  # Initialize in case of early failure

    job_with_relations = db.query(Job).options(
        joinedload(Job.daily_analyses)
        .joinedload(DailyAnalysis.conversation)
        .joinedload(Conversation.messages)
    ).filter(Job.id == job.id).first()

    if not job_with_relations:
        logger.error(f"Could not find Job ID {job.id} in the database for execution.")
        return

    start_time = time.time()
    try:
        ai_function = gemini_service.get_gemini_service(settings.GEMINI_API_KEY).analyze_daily_analyses_batch
        analysis_results, missed_ids, usage_metadata, response_text = await ai_function(job_with_relations.daily_analyses)
        end_time = time.time()

        if missed_ids:
            _save_gemini_response(job.id, response_text, 'partial_success')
            _handle_partial_success(db, job_with_relations, analysis_results, missed_ids, usage_metadata, end_time - start_time)
        else:
            _save_gemini_response(job.id, response_text, 'successful')
            _handle_successful_analysis(db, job_with_relations, analysis_results, usage_metadata, end_time - start_time)

    except gemini_service.TransientApiError as e:
        logger.warning(f"Job ID: {job.id} failed with a transient error: {e}")
        _save_gemini_response(job.id, response_text, 'failed')
        _handle_retryable_failure(db, job, e)

    except (gemini_service.PermanentApiError, gemini_service.ParsingError) as e:
        logger.error(f"Job ID: {job.id} failed with a permanent error: {e}", exc_info=True)
        _save_gemini_response(job.id, response_text, 'failed')
        _handle_permanent_failure(db, job, e)

    except Exception as e:
        logger.error(f"Job ID: {job.id} failed with an unexpected catastrophic error: {e}", exc_info=True)
        _save_gemini_response(job.id, str(e), 'failed')
        _handle_permanent_failure(db, job, e)


def _handle_successful_analysis(db: Session, job: Job, analysis_results: list, usage_metadata: dict, processing_time: float):
    """
    Handles the logic for a successfully completed AI analysis.
    """
    analysis_map = {res.get("daily_analysis_id"): res for res in analysis_results}

    for analysis_obj in job.daily_analyses:
        try:
            # Always calculate time-based metrics
            time_metrics = time_metric_service.calculate_time_metrics_for_daily_analysis(analysis_obj)
            analysis_obj.first_response_time = time_metrics.get("first_response_time")
            analysis_obj.avg_response_time = time_metrics.get("avg_response_time")
            analysis_obj.total_handling_time = time_metrics.get("total_handling_time")

            # Update with AI-generated metrics
            result_data = analysis_map.get(analysis_obj.id)
            if result_data:
                analysis_obj.sentiment_score = result_data.get("sentiment_score")
                analysis_obj.sentiment_shift = result_data.get("sentiment_shift")
                analysis_obj.resolution_achieved = result_data.get("resolution_achieved")
                analysis_obj.fcr_score = result_data.get("fcr_score")
                analysis_obj.ces = result_data.get("ces")
                analysis_obj.common_topics = result_data.get("common_topics")
                analytics_service.calculate_and_set_daily_csi_score(analysis_obj)
            else:
                logger.warning(f"Could not find AI results for daily_analysis {analysis_obj.id} in successful job {job.id}")

        except Exception as metric_error:
            logger.error(f"Failed to calculate metrics for daily_analysis {analysis_obj.id} in job {job.id}: {metric_error}", exc_info=True)

    job_metric = JobMetric(
        job_id=job.id,
        token_usage=usage_metadata.get("total_token_count"),
        processing_time_seconds=processing_time,
        api_calls_made=1 # This could be enhanced to track retries
    )
    db.add(job_metric)

    job.status = "completed"
    job.result = {"results_count": len(analysis_results)}
    job.completed_at = datetime.utcnow()
    db.commit()
    logger.info(f"Successfully completed Job ID: {job.id}")


def _handle_retryable_failure(db: Session, job: Job, error: Exception):
    """
    Handles the logic for a failure that can be retried.
    """
    job.retry_count += 1
    if job.retry_count > job.max_retries:
        _handle_permanent_failure(db, job, error, reason="Max retries exceeded.")
    else:
        job.status = "retryable_failure"
        # Exponential backoff for the next run
        wait_seconds = (2 ** job.retry_count) * 5
        job.run_at = datetime.utcnow() + timedelta(seconds=wait_seconds)
        job.last_error = str(error)
        db.commit()
        logger.info(f"Scheduled Job ID: {job.id} for retry at {job.run_at}")


def _handle_permanent_failure(db: Session, job: Job, error: Exception, reason: str = None):
    """
    Handles the logic for a failure that should not be retried.
    """
    final_error = f"{reason} {str(error)}" if reason else str(error)
    job.status = "failed"
    job.last_error = final_error
    job.result = {"error": str(error), "traceback": traceback.format_exc()}
    job.completed_at = datetime.utcnow()
    db.commit()
    logger.error(f"Job ID: {job.id} failed permanently.")

def _create_retry_job(db: Session, original_job: Job, missed_analyses: list[DailyAnalysis], reason: str):
    """
    Creates a new job for analyses that were missed, often due to truncation.
    """
    if not missed_analyses:
        return

    new_job = Job(
        upload_id=original_job.upload_id,
        status="pending",
        run_at=datetime.utcnow(),
        daily_analyses=missed_analyses,
        task_name=f"retry_for_job_{original_job.id}",
        max_retries=original_job.max_retries - original_job.retry_count # Inherit remaining retries
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
    logger.info(f"Created new retry Job ID: {new_job.id} for {len(missed_analyses)} missed analyses from original Job ID: {original_job.id}. Reason: {reason}")


def _handle_partial_success(db: Session, job: Job, analysis_results: list, missed_ids: list[int], usage_metadata: dict, processing_time: float):
    """
    Handles a job that was partially successful due to a recoverable error like truncation.
    """
    logger.warning(f"Job ID: {job.id} was partially successful. {len(analysis_results)} analyses processed, {len(missed_ids)} missed.")
    
    # 1. Process the successful parts
    _handle_successful_analysis(db, job, analysis_results, usage_metadata, processing_time)
    
    # 2. Create a new job for the missed parts
    missed_analyses = db.query(DailyAnalysis).filter(DailyAnalysis.id.in_(missed_ids)).all()
    _create_retry_job(db, job, missed_analyses, reason="Truncated response from previous attempt")
    
    # 3. Mark the original job as completed with errors
    job.status = "completed_with_errors"
    job.result["missed_count"] = len(missed_ids)
    job.last_error = "Response was truncated. A new job was created for missed items."
    db.commit()

def _save_gemini_response(job_id: int, response_text: str, status: str):
    """
    Saves the raw text from a Gemini API response to a structured log directory.
    """
    if response_text is None:
        return
    try:
        run_timestamp = datetime.now().strftime("%Y%m%d")
        log_dir = Path("logs") / "gemini_responses" / f"run_{run_timestamp}" / status
        log_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = log_dir / f"job_{job_id}.txt"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(response_text)
        logger.info(f"Saved Gemini response for Job ID {job_id} to {file_path}")
    except Exception as e:
        logger.error(f"Failed to save Gemini response for Job ID {job_id}: {e}")
