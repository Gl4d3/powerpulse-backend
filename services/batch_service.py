import logging
from typing import List, Dict
from collections import defaultdict
import json

from models import DailyAnalysis
from config import settings

logger = logging.getLogger(__name__)

def estimate_token_count(analysis: DailyAnalysis) -> int:
    """
    Estimates the token count for a single DailyAnalysis object by mimicking
    the prompt structure. A simple heuristic of len(text) / 4 is used.
    """    
    messages_text = "\n".join([
        f"{m.social_create_time} - {m.direction}: {m.message_content}" 
        for m in analysis.conversation.messages 
        if m.social_create_time.date() == analysis.analysis_date
    ])
    
    analysis_json_text = json.dumps({
        "daily_analysis_id": analysis.id or 0, # Use 0 if ID is not yet assigned
        "messages": messages_text
    }, indent=2)
    
    # A common heuristic for token estimation is ~4 chars per token
    return len(analysis_json_text) // 4

def create_daily_analysis_batches(daily_analyses: List[DailyAnalysis]) -> List[List[DailyAnalysis]]:
    """
    Groups DailyAnalysis objects into batches that are under a token limit,
    ensuring that all analyses for a single conversation remain in the same batch.
    """
    if not daily_analyses:
        return []

    # 1. Group analyses by conversation
    analyses_by_conv = defaultdict(list)
    for analysis in daily_analyses:
        analyses_by_conv[analysis.conversation_id].append(analysis)

    # 2. Estimate token count for each full conversation
    conv_token_estimates = {
        conv_id: sum(estimate_token_count(da) for da in das)
        for conv_id, das in analyses_by_conv.items()
    }

    # 3. Build batches, keeping conversations whole
    batches: List[List[DailyAnalysis]] = []
    current_batch: List[DailyAnalysis] = []
    current_batch_tokens = 0

    for conv_id, conv_analyses in analyses_by_conv.items():
        conv_tokens = conv_token_estimates[conv_id]

        if conv_tokens > settings.MAX_TOKENS_PER_BATCH:
            logger.warning(
                f"Conversation {conv_id} with {conv_tokens} estimated tokens exceeds the max batch size of "
                f"{settings.MAX_TOKENS_PER_BATCH}. Processing as its own oversized batch."
            )
            # If a single conversation is too large, it becomes its own batch
            if current_batch: # Finalize the previous batch first
                batches.append(current_batch)
            batches.append(conv_analyses)
            current_batch = [] # Reset for the next iteration
            current_batch_tokens = 0
            continue

        if current_batch and (current_batch_tokens + conv_tokens > settings.MAX_TOKENS_PER_BATCH):
            # Finalize the current batch
            batches.append(current_batch)
            # Start a new batch
            current_batch = conv_analyses
            current_batch_tokens = conv_tokens
        else:
            # Add to the current batch
            current_batch.extend(conv_analyses)
            current_batch_tokens += conv_tokens

    # Add the last remaining batch if it exists
    if current_batch:
        batches.append(current_batch)

    logger.info(f"Created {len(batches)} batches from {len(daily_analyses)} daily analyses based on a token limit of {settings.MAX_TOKENS_PER_BATCH}.")
    
    return batches

