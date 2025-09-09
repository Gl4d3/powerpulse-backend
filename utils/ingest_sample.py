import asyncio
import json
import uuid
import logging
import sys
from pathlib import Path

# Add project root to the Python path to allow for module imports
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from services.file_service_optimized import process_uploaded_file
from services.progress_tracker import progress_tracker

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def ingest_sample_data():
    """
    Reads the curated sample data and uses the file service to ingest it.
    """
    sample_file_path = "attached_assets/curated_sample.json"
    logging.info(f"Reading sample data from {sample_file_path}...")

    try:
        with open(sample_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # The ingestion service expects a flat string of a list of messages
            messages_list = data.get("messages", [])
            file_content = json.dumps(messages_list)
        
        upload_id = str(uuid.uuid4())
        logging.info(f"Starting ingestion with upload_id: {upload_id}")
        
        # Manually start the progress tracker
        await progress_tracker.start_upload(upload_id, "curated_sample.json")

        # Call the service function directly
        await process_uploaded_file(file_content, upload_id, force_reprocess=True)
        
        logging.info("Ingestion process completed.")
        print(f"Successfully submitted sample data for processing with upload_id: {upload_id}")

    except FileNotFoundError:
        logging.error(f"Sample data file not found at: {sample_file_path}")
    except Exception as e:
        logging.error(f"An error occurred during sample ingestion: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(ingest_sample_data())
