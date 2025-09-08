from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import math

from database import get_db
from models import Job
from schemas import JobDetailsResponse, JobStatusResponse, PaginatedJobResponse, Pagination, JobRetryResponse

router = APIRouter()

@router.get("/", response_model=PaginatedJobResponse)
def list_jobs(
    db: Session = Depends(get_db),
    status: Optional[str] = Query(None, description="Filter jobs by status (e.g., pending, running, failed)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Number of jobs per page")
):
    """List all analysis jobs with pagination and status filtering."""
    query = db.query(Job)
    if status:
        query = query.filter(Job.status == status)

    total_items = query.count()
    total_pages = math.ceil(total_items / page_size)
    offset = (page - 1) * page_size

    jobs = query.order_by(Job.created_at.desc()).limit(page_size).offset(offset).all()

    pagination_data = Pagination(
        page=page,
        page_size=page_size,
        total_items=total_items,
        total_pages=total_pages
    )

    return PaginatedJobResponse(pagination=pagination_data, data=jobs)

@router.get("/{job_id}", response_model=JobDetailsResponse)
def get_job_details(job_id: int, db: Session = Depends(get_db)):
    """Retrieve the detailed status of a single job."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job with ID {job_id} not found")
    return job

@router.post("/{job_id}/retry", response_model=JobRetryResponse)
def retry_failed_job(job_id: int, db: Session = Depends(get_db)):
    """
    Manually retry a job that has the status 'failed'.
    Resets the status to 'pending' and clears error information.
    """
    job = db.query(Job).filter(Job.id == job_id).first()

    if not job:
        raise HTTPException(status_code=404, detail=f"Job with ID {job_id} not found")

    if job.status != 'failed':
        raise HTTPException(status_code=400, detail=f"Job {job_id} cannot be retried. Status is '{job.status}', not 'failed'.")

    job.status = 'pending'
    job.retry_count = 0
    job.last_error = None
    job.run_at = datetime.utcnow()
    db.commit()

    return {
        "job_id": job.id,
        "new_status": "pending",
        "message": f"Job {job.id} has been successfully queued for a retry."
    }
