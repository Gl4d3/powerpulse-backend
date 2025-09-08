import asyncio
import logging
import traceback
import time
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
    
    # Eagerly load all necessary relationships for the job
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
        analysis_results, usage_metadata = await ai_function(job_with_relations.daily_analyses)

        # --- SUCCESS PATH ---
        end_time = time.time()
        _handle_successful_analysis(db, job_with_relations, analysis_results, usage_metadata, end_time - start_time)

    except gemini_service.TransientApiError as e:
        logger.warning(f"Job ID: {job.id} failed with a transient error: {e}")
        _handle_retryable_failure(db, job, e)

    except (gemini_service.PermanentApiError, gemini_service.ParsingError) as e:
        logger.error(f"Job ID: {job.id} failed with a permanent error: {e}", exc_info=True)
        _handle_permanent_failure(db, job, e)

    except Exception as e:
        logger.error(f"Job ID: {job.id} failed with an unexpected catastrophic error: {e}", exc_info=True)
        _handle_permanent_failure(db, job, e) # Treat unexpected errors as permanent


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
