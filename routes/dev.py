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


@router.post("/create-sample")
async def create_sample_dataset():
    """
    Triggers the create_data_sample.py script to generate a new curated sample file.
    """
    import subprocess
    import sys
    try:
        script_path = "utils/create_data_sample.py"
        # Ensure we use the same python interpreter that is running the app
        python_executable = sys.executable
        
        logging.info("Starting execution of create_data_sample.py script...")
        result = subprocess.run(
            [python_executable, script_path],
            capture_output=True,
            text=True,
            check=True  # Raises CalledProcessError if the script returns a non-zero exit code
        )
        logging.info("Script execution successful.")
        return {
            "message": "Successfully created curated data sample.",
            "output": result.stdout,
            "errors": result.stderr
        }
    except FileNotFoundError:
        logger.error(f"Error: The script at {script_path} was not found.")
        raise HTTPException(status_code=500, detail=f"Script not found at {script_path}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Error executing create_data_sample.py script: {e}")
        logger.error(f"Script stderr: {e.stderr}")
        raise HTTPException(status_code=500, detail=f"Error executing sampling script: {e.stderr}")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")


@router.post("/setup-test-db")
async def setup_test_database(db: Session = Depends(get_db)):
    """
    Resets the entire database and populates it using the curated sample data file.
    This creates a clean, consistent, and small environment for testing.
    """
    import subprocess
    import sys
    import json
    import uuid
    from services.file_service_optimized import process_uploaded_file

    try:
        # 1. Reset the database
        logging.info("Step 1/2: Resetting database...")
        python_executable = sys.executable
        reset_script_path = "utils/reset_database.py"
        subprocess.run(
            [python_executable, reset_script_path, "--force"],
            check=True, capture_output=True, text=True
        )
        logging.info("Database reset successfully.")

        # 2. Ingest the curated sample file
        logging.info("Step 2/2: Ingesting curated sample data...")
        sample_file_path = "attached_assets/curated_sample.json"
        with open(sample_file_path, 'r', encoding='utf-8') as f:
            # The sample file has a root key, we need the messages list
            data = json.load(f)
            messages_list = data.get("messages", [])
            # The ingestion service expects a flat string of the list
            file_content = json.dumps(messages_list)

        upload_id = str(uuid.uuid4())
        # Call the underlying service function to process the file
        # Using force_reprocess=True to ensure it always processes the sample
        await process_uploaded_file(file_content, upload_id, force_reprocess=True)
        logging.info(f"Successfully submitted sample data for processing with upload_id: {upload_id}")

        return {
            "message": "Test database setup complete. Ingestion of sample data has started.",
            "upload_id": upload_id
        }

    except FileNotFoundError as e:
        logger.error(f"A required file was not found: {e}")
        raise HTTPException(status_code=500, detail=f"A required file was not found: {e.filename}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Error resetting the database: {e.stderr}")
        raise HTTPException(status_code=500, detail=f"Error resetting database: {e.stderr}")
    except Exception as e:
        logger.error(f"An unexpected error occurred during test DB setup: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred during test DB setup.")


@router.post("/proxy")
async def proxy_request(request: dict):
    """
    Acts as a proxy to make requests to other internal API endpoints.
    Useful for scripting and verification.
    Expects a JSON body like:
    {
        "method": "GET",
        "path": "/api/explorer/analyses",
        "params": {"start_date": "2025-08-17", "end_date": "2025-08-23"},
        "json_body": null
    }
    """
    import httpx
    
    method = request.get("method")
    path = request.get("path")
    params = request.get("params")
    json_body = request.get("json_body")

    if not method or not path:
        raise HTTPException(status_code=400, detail="'method' and 'path' are required.")

    # Assuming the app runs on localhost:8000
    base_url = "http://localhost:8000"
    url = f"{base_url}{path}"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=url,
                params=params,
                json=json_body,
                timeout=60.0 # Set a reasonable timeout
            )
            try:
                response_body = response.json()
            except json.JSONDecodeError:
                response_body = response.text

            return {
                "status_code": response.status_code,
                "body": response_body
            }
    except httpx.RequestError as e:
        logger.error(f"Error making proxy request to {e.request.url!r}: {e}")
        raise HTTPException(status_code=500, detail=f"Error making proxy request: {e}")
