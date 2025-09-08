"""
Development-only endpoints for inspecting the in-memory database.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import inspect
from database import get_db, Base
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# A mapping of table names to their SQLAlchemy model classes
# This is safer than using getattr() with user input.
TABLE_MODEL_MAP = {
    "conversations": "Conversation",
    "daily_analyses": "DailyAnalysis",
    "messages": "Message",
    "jobs": "Job",
    "metrics": "Metric",
    "processed_chats": "ProcessedChat",
}

@router.get("/view-table/{table_name}")
async def view_table(table_name: str, db: Session = Depends(get_db)):
    """
    Returns all rows from a specified table in the in-memory database.
    This endpoint is for development and debugging purposes only.
    """
    if table_name not in TABLE_MODEL_MAP:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found or not accessible.")

    try:
        model_name = TABLE_MODEL_MAP[table_name]
        
        # Find the model class in the SQLAlchemy Base metadata
        model_class = next((c for c in Base.registry.mappers if c.class_.__name__ == model_name), None)
        
        if model_class is None:
             raise HTTPException(status_code=404, detail=f"Model for table '{table_name}' not found.")

        # Query all records from the table
        records = db.query(model_class.class_).all()
        
        # A simple way to serialize the SQLAlchemy objects to dicts
        inspector = inspect(model_class.class_)
        result = []
        for record in records:
            record_dict = {c.key: getattr(record, c.key) for c in inspector.mapper.column_attrs}
            result.append(record_dict)
            
        return result

    except Exception as e:
        logger.error(f"Error viewing table {table_name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An error occurred while trying to view table '{table_name}'.")


# DEV: Inspect daily analyses for a given date (to debug explorer endpoint)
@router.get("/daily-analyses-for-date/{analysis_date}")
async def dev_daily_analyses_for_date(analysis_date: str, db: Session = Depends(get_db)):
    """
    Returns the count and a sample of daily analyses for a given analysis_date (YYYY-MM-DD).
    Helps debug why /api/explorer/analyses may return 0 results for a date.
    """
    from models import DailyAnalysis
    from sqlalchemy import func
    try:
        # Parse date
        from datetime import datetime
        try:
            date_obj = datetime.strptime(analysis_date, "%Y-%m-%d").date()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

        # Query count and sample
        count = db.query(func.count(DailyAnalysis.id)).filter(DailyAnalysis.analysis_date == date_obj).scalar()
        sample = db.query(DailyAnalysis).filter(DailyAnalysis.analysis_date == date_obj).limit(5).all()
        # Serialize sample
        def serialize(obj):
            return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
        sample_serialized = [serialize(a) for a in sample]
        return {"date": analysis_date, "count": count, "sample": sample_serialized}
    except Exception as e:
        logger.error(f"Error in dev_daily_analyses_for_date: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error inspecting daily analyses for date.")
