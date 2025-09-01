import logging
from typing import List
from models import Conversation, DailyAnalysis
from config import settings
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

def create_daily_analysis_batches(daily_analyses: List[DailyAnalysis], db: Session) -> List[List[DailyAnalysis]]:
    """
    Extracts pending DailyAnalysis objects from conversations and splits them 
    into smaller batches based on BATCH_SIZE for AI processing.
    """
    if not daily_analyses:
        return []
        
    batch_size = settings.BATCH_SIZE
    batches = [daily_analyses[i:i + batch_size] for i in range(0, len(daily_analyses), batch_size)]
    
    logger.info(f"Created {len(batches)} batches from {len(daily_analyses)} daily analysis objects with a batch size of {batch_size}.")
    
    return batches
