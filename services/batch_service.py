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

from typing import List
from sqlalchemy.orm import Session
from models import Conversation
from config import settings
import logging

logger = logging.getLogger(__name__)

def create_batches(conversations: List[Conversation], db: Session) -> List[List[Conversation]]:
    """
    Splits a list of conversations into smaller batches based on BATCH_SIZE.
    """
    if not conversations:
        return []
        
    batch_size = settings.BATCH_SIZE
    batches = [conversations[i:i + batch_size] for i in range(0, len(conversations), batch_size)]
    
    logger.info(f"Created {len(batches)} batches from {len(conversations)} conversations with a batch size of {batch_size}.")
    
    return batches
