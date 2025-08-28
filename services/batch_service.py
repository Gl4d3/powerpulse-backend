import logging
from typing import List
from models import Conversation, DailyAnalysis
from config import settings
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

def create_daily_analysis_batches(conversations: List[Conversation], db: Session) -> List[List[DailyAnalysis]]:
    """
    Extracts pending DailyAnalysis objects from conversations and splits them 
    into smaller batches based on BATCH_SIZE for AI processing.
    """
    if not conversations:
        return []
    
    # Extract all pending DailyAnalysis objects from the conversations
    pending_analyses = []
    for conv in conversations:
        for analysis in conv.daily_analyses:
            # Assuming new DailyAnalysis objects don't have an ID yet
            if analysis.id is None:
                pending_analyses.append(analysis)

    if not pending_analyses:
        return []
        
    batch_size = settings.BATCH_SIZE
    batches = [pending_analyses[i:i + batch_size] for i in range(0, len(pending_analyses), batch_size)]
    
    logger.info(f"Created {len(batches)} batches from {len(pending_analyses)} daily analysis objects with a batch size of {batch_size}.")
    
    return batches
