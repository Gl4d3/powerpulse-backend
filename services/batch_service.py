import logging
from typing import List
from models import Conversation, Message
from config import settings
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

def estimate_token_count(conversation: Conversation, db: Session) -> int:
    """
    Estimates the token count of a conversation.
    A simple proxy is len(text) / 4.
    """
    # This is a very rough estimation. A more accurate method would be to use a real tokenizer.
    # For now, we'll concatenate the content of all messages in the conversation.
    
    # Query messages for the conversation
    messages = db.query(Message).filter(Message.fb_chat_id == conversation.fb_chat_id).all()
    if not messages:
        return 0
        
    text_content = " ".join([message.message_content for message in messages])
    return len(text_content) // 4

def create_batches(conversations: List[Conversation], db: Session) -> List[List[Conversation]]:
    """
    Groups conversations into batches based on token limits.
    """
    if not conversations:
        return []

    batches = []
    current_batch = []
    current_batch_tokens = 0

    for conv in conversations:
        conv_tokens = estimate_token_count(conv, db)

        if conv_tokens > settings.MAX_TOKENS_PER_JOB:
            logger.warning(f"Conversation {conv.id} is too large ({conv_tokens} tokens) to fit in a job. Skipping.")
            # TODO: Implement logic to handle conversations that are too large.
            # For now, we just skip them.
            continue

        if current_batch_tokens + conv_tokens > settings.MAX_TOKENS_PER_JOB:
            if current_batch:
                batches.append(current_batch)
            current_batch = [conv]
            current_batch_tokens = conv_tokens
        else:
            current_batch.append(conv)
            current_batch_tokens += conv_tokens

    if current_batch:
        batches.append(current_batch)

    logger.info(f"Created {len(batches)} batches from {len(conversations)} conversations.")
    return batches
