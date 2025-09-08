#!/usr/bin/env python3
"""
Utility script to fix conversation statistics and time metrics for existing data.
This script will:
1. Update conversation message counts for all conversations
2. Recalculate time metrics for daily analyses that are missing them
3. Update conversation first/last message timestamps

Run this after the code fixes to populate missing data.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from sqlalchemy.orm import Session
from database import get_db
from models import Conversation, DailyAnalysis, Message
from services.time_metric_service import calculate_time_metrics_for_daily_analysis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_conversation_statistics(db: Session):
    """Update conversation-level statistics based on actual messages."""
    logger.info("Starting conversation statistics fix...")
    
    conversations = db.query(Conversation).all()
    fixed_count = 0
    
    for conversation in conversations:
        try:
            # Count messages by direction
            total_messages = len(conversation.messages)
            customer_messages = len([m for m in conversation.messages if m.direction == 'to_company'])
            agent_messages = len([m for m in conversation.messages if m.direction == 'to_client'])
            
            # Find first and last message times
            if conversation.messages:
                sorted_messages = sorted(conversation.messages, key=lambda m: m.social_create_time)
                first_message_time = sorted_messages[0].social_create_time
                last_message_time = sorted_messages[-1].social_create_time
            else:
                first_message_time = None
                last_message_time = None
            
            # Check if update is needed
            needs_update = (
                conversation.total_messages != total_messages or
                conversation.customer_messages != customer_messages or
                conversation.agent_messages != agent_messages or
                conversation.first_message_time != first_message_time or
                conversation.last_message_time != last_message_time
            )
            
            if needs_update:
                conversation.total_messages = total_messages
                conversation.customer_messages = customer_messages
                conversation.agent_messages = agent_messages
                conversation.first_message_time = first_message_time
                conversation.last_message_time = last_message_time
                fixed_count += 1
                
                if fixed_count % 100 == 0:
                    logger.info(f"Fixed {fixed_count} conversations so far...")
                    
        except Exception as e:
            logger.error(f"Error fixing conversation {conversation.fb_chat_id}: {e}")
            continue
    
    db.commit()
    logger.info(f"Fixed statistics for {fixed_count} conversations")
    return fixed_count

def fix_time_metrics(db: Session):
    """Recalculate time metrics for daily analyses that are missing them."""
    logger.info("Starting time metrics fix...")
    
    # Find daily analyses with missing time metrics
    analyses_to_fix = db.query(DailyAnalysis).filter(
        (DailyAnalysis.first_response_time.is_(None)) |
        (DailyAnalysis.avg_response_time.is_(None)) |
        (DailyAnalysis.total_handling_time.is_(None))
    ).all()
    
    logger.info(f"Found {len(analyses_to_fix)} daily analyses with missing time metrics")
    fixed_count = 0
    
    for analysis in analyses_to_fix:
        try:
            # Calculate time metrics
            time_metrics = calculate_time_metrics_for_daily_analysis(analysis)
            
            # Update the analysis
            updated = False
            if analysis.first_response_time is None and time_metrics.get("first_response_time") is not None:
                analysis.first_response_time = time_metrics.get("first_response_time")
                updated = True
            if analysis.avg_response_time is None and time_metrics.get("avg_response_time") is not None:
                analysis.avg_response_time = time_metrics.get("avg_response_time")
                updated = True
            if analysis.total_handling_time is None and time_metrics.get("total_handling_time") is not None:
                analysis.total_handling_time = time_metrics.get("total_handling_time")
                updated = True
                
            if updated:
                fixed_count += 1
                if fixed_count % 100 == 0:
                    logger.info(f"Fixed time metrics for {fixed_count} daily analyses so far...")
                    
        except Exception as e:
            logger.error(f"Error fixing time metrics for daily analysis {analysis.id}: {e}")
            continue
    
    db.commit()
    logger.info(f"Fixed time metrics for {fixed_count} daily analyses")
    return fixed_count

def main():
    """Run the fix script."""
    logger.info("Starting database fix script...")
    
    db = next(get_db())
    
    try:
        # Fix conversation statistics
        conv_fixed = fix_conversation_statistics(db)
        
        # Fix time metrics
        time_fixed = fix_time_metrics(db)
        
        logger.info(f"Fix completed successfully!")
        logger.info(f"- Fixed statistics for {conv_fixed} conversations")
        logger.info(f"- Fixed time metrics for {time_fixed} daily analyses")
        
    except Exception as e:
        logger.error(f"Error during fix: {e}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()
