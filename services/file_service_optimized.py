import json
import logging
import asyncio
import uuid
from typing import Dict, List, Any, Tuple
from datetime import datetime
from sqlalchemy.orm import Session

from models import Message, Conversation, ProcessedChat
from services import batch_service, job_service
from services.progress_tracker import progress_tracker
from config import settings

logger = logging.getLogger(__name__)

class OptimizedFileService:
    def __init__(self):
        pass
    
    async def process_grouped_chats_json(
        self, 
        file_content: str, 
        db: Session, 
        force_reprocess: bool = False
    ) -> Tuple[int, int, str]:
        """
        Optimized processing of uploaded JSON file with a job-based system.
        Returns (conversations_processed, messages_processed, upload_id)
        """
        upload_id = str(uuid.uuid4())
        
        try:
            data = json.loads(file_content)
            if not isinstance(data, dict):
                raise ValueError("JSON must be an object with chat_id keys")
            
            await progress_tracker.start_upload(upload_id, len(data))
            
            conversations_to_process = []
            await progress_tracker.update_progress(upload_id, 0, "filtering_conversations", "Filtering conversations...")
            
            for chat_id, messages in data.items():
                if not isinstance(messages, list):
                    logger.warning(f"Skipping chat_id {chat_id}: messages must be an array")
                    continue
                
                if not force_reprocess and self._is_chat_processed(db, chat_id):
                    logger.info(f"Skipping already processed chat: {chat_id}")
                    continue
                
                valid_messages = [self._clean_message(msg, chat_id) for msg in messages if self._validate_message(msg)]
                
                if valid_messages:
                    conversations_to_process.append({
                        'chat_id': chat_id,
                        'messages': valid_messages
                    })

            if not conversations_to_process:
                await progress_tracker.complete_upload(upload_id, True)
                return 0, 0, upload_id

            # 1. Create Conversation and Message objects in memory
            new_conversations = []
            for conv_data in conversations_to_process:
                conversation = Conversation(fb_chat_id=conv_data['chat_id'])
                for msg_data in conv_data['messages']:
                    message = Message(
                        fb_chat_id=conv_data['chat_id'],
                        message_content=msg_data['message_content'],
                        direction=msg_data['direction'],
                        social_create_time=msg_data['social_create_time'],
                        agent_info=msg_data.get('agent_info')
                    )
                    conversation.messages.append(message)
                new_conversations.append(conversation)

            # 2. Create batches
            await progress_tracker.update_progress(upload_id, 0, "batching", "Creating analysis jobs...")
            batches = batch_service.create_batches(new_conversations, db)

            # 3. Create jobs
            jobs = await job_service.create_jobs_for_upload(upload_id, batches, db)
            
            # 4. Process jobs
            await progress_tracker.update_progress(upload_id, 0, "ai_analysis", f"Processing {len(jobs)} analysis jobs...")
            
            tasks = [job_service.process_job(job, db) for job in jobs]
            await asyncio.gather(*tasks)

            conversations_processed = len(new_conversations)
            messages_processed = sum(len(conv.messages) for conv in new_conversations)

            for conv in new_conversations:
                self._mark_chat_processed(db, conv.fb_chat_id, len(conv.messages))
            
            db.commit()

            await progress_tracker.complete_upload(upload_id, True)
            
            return conversations_processed, messages_processed, upload_id

        except json.JSONDecodeError as e:
            await progress_tracker.add_error(upload_id, f"Invalid JSON format: {str(e)}")
            await progress_tracker.complete_upload(upload_id, False)
            raise ValueError(f"Invalid JSON format: {e}")
        except Exception as e:
            logger.error(f"Error processing file: {e}")
            await progress_tracker.add_error(upload_id, str(e))
            await progress_tracker.complete_upload(upload_id, False)
            db.rollback()
            raise
    
    
    
    def _validate_message(self, msg: Dict) -> bool:
        """Validate required message fields and filter autoresponses"""
        required_fields = ['MESSAGE_CONTENT', 'DIRECTION', 'SOCIAL_CREATE_TIME']
        
        for field in required_fields:
            if field not in msg:
                return False
        
        # Validate direction
        if msg['DIRECTION'] not in ['to_company', 'to_client']:
            return False
        
        # Validate content exists and is string
        message_content = msg['MESSAGE_CONTENT']
        if not message_content or not isinstance(message_content, str):
            return False
        
        # Filter out autoresponse messages containing "*977#"
        if "*977#" in message_content:
            logger.info(f"Filtering autoresponse message containing '*977#': {message_content[:100]}...")
            return False
        
        return True
    
    def _clean_message(self, msg: Dict, chat_id: str) -> Dict:
        """Clean and standardize message data"""
        # Parse timestamp
        timestamp_str = msg['SOCIAL_CREATE_TIME']
        if isinstance(timestamp_str, str):
            try:
                social_create_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            except:
                try:
                    social_create_time = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                except:
                    social_create_time = datetime.utcnow()
        else:
            social_create_time = datetime.utcnow()
        
        return {
            'fb_chat_id': chat_id,
            'message_content': msg['MESSAGE_CONTENT'].strip(),
            'direction': msg['DIRECTION'],
            'social_create_time': social_create_time,
            'agent_info': msg.get('AGENT_USERNAME') or msg.get('AGENT_EMAIL')
        }
    
    def _calculate_response_time(self, agent_message: Dict, customer_messages: List[Dict]) -> float:
        """Calculate response time in minutes for an agent message"""
        try:
            agent_time = agent_message['social_create_time']
            
            # Find the most recent customer message before this agent message
            preceding_customer_msgs = [
                msg for msg in customer_messages
                if msg['social_create_time'] < agent_time
            ]
            
            if not preceding_customer_msgs:
                return None
            
            latest_customer_msg = max(preceding_customer_msgs, key=lambda x: x['social_create_time'])
            time_diff = agent_time - latest_customer_msg['social_create_time']
            
            return time_diff.total_seconds() / 60  # Convert to minutes
            
        except Exception as e:
            logger.error(f"Error calculating response time: {e}")
            return None
    
    def _is_first_contact(self, message: Dict, all_messages: List[Dict]) -> bool:
        """Determine if this is the first message in the conversation"""
        try:
            sorted_messages = sorted(all_messages, key=lambda x: x['social_create_time'])
            return sorted_messages[0]['message_content'] == message['message_content']
        except:
            return False
    
    def _calculate_avg_response_time(self, messages: List[Dict]) -> float:
        """Calculate average response time for agent messages in the conversation"""
        try:
            customer_messages = [m for m in messages if m['direction'] == 'to_company']
            agent_messages = [m for m in messages if m['direction'] == 'to_client']
            
            if not customer_messages or not agent_messages:
                return 0.0
            
            response_times = []
            
            for agent_msg in agent_messages:
                response_time = self._calculate_response_time(agent_msg, customer_messages)
                if response_time is not None:
                    response_times.append(response_time)
            
            return sum(response_times) / len(response_times) if response_times else 0.0
            
        except Exception as e:
            logger.error(f"Error calculating average response time: {e}")
            return 0.0
    
    def _is_chat_processed(self, db: Session, chat_id: str) -> bool:
        """Check if a chat has already been processed"""
        try:
            return db.query(ProcessedChat).filter(ProcessedChat.fb_chat_id == chat_id).first() is not None
        except Exception as e:
            logger.error(f"Error checking processed status for {chat_id}: {e}")
            return False
    
    def _mark_chat_processed(self, db: Session, chat_id: str, message_count: int):
        """Mark a chat as processed"""
        try:
            # Remove existing record if it exists (for force reprocess)
            existing = db.query(ProcessedChat).filter(ProcessedChat.fb_chat_id == chat_id).first()
            if existing:
                db.delete(existing)
            
            # Add new record
            processed_chat = ProcessedChat(
                fb_chat_id=chat_id,
                message_count=message_count
            )
            db.add(processed_chat)
            
        except Exception as e:
            logger.error(f"Error marking chat {chat_id} as processed: {e}")
            raise

# Global optimized service instance
optimized_file_service = OptimizedFileService()