import json
import logging
import asyncio
import uuid
from typing import Dict, List, Any, Tuple
from datetime import datetime
from sqlalchemy.orm import Session

from models import Message, Conversation, ProcessedChat, DailyAnalysis
from services import batch_service, job_service
from services.progress_tracker import progress_tracker
from config import settings

logger = logging.getLogger(__name__)

from database import SessionLocal
from services.analytics_service import analytics_service

async def process_uploaded_file(file_content: str, upload_id: str, force_reprocess: bool):
    """
    This function runs in the background to process the uploaded file.
    It creates its own database session.
    """
    with SessionLocal() as db:
        await optimized_file_service.process_grouped_chats_json(
            file_content=file_content,
            db=db,
            force_reprocess=force_reprocess,
            upload_id=upload_id
        )
        # After processing, trigger the global metrics recalculation
        analytics_service.calculate_and_cache_csi_metrics(db)

class OptimizedFileService:
    async def process_grouped_chats_json(
        self, 
        file_content: str, 
        db: Session, 
        upload_id: str,
        force_reprocess: bool = False
    ) -> Tuple[int, int, str]:
        """
        Universal handler for processing uploaded JSON files. It detects the format
        (raw flat array vs. pre-grouped dictionary) and processes it accordingly.
        """
        try:
            logger.info(f"Starting universal processing for upload_id: {upload_id}...")
            # The new universal parser detects the format and returns a consistent structure
            grouped_data, customer_names = self._parse_and_normalize_input(file_content)
            
            await progress_tracker.start_upload(upload_id, len(grouped_data))
            
            conversations_to_process = []
            await progress_tracker.update_progress(upload_id, 0, "filtering_conversations", "Filtering conversations...")
            
            for chat_id, messages in grouped_data.items():
                # The rest of the pipeline remains the same, as the data is now in a consistent format
                if not isinstance(messages, list):
                    logger.warning(f"Skipping chat_id {chat_id}: messages must be an array")
                    continue
                
                if force_reprocess:
                    existing_conv = db.query(Conversation).filter(Conversation.fb_chat_id == chat_id).first()
                    if existing_conv:
                        logger.info(f"Force reprocess: Deleting existing conversation data for {chat_id}...")
                        db.delete(existing_conv)
                        db.commit()
                
                elif self._is_chat_processed(db, chat_id):
                    logger.info(f"Skipping already processed chat: {chat_id}")
                    continue
                
                valid_messages = [self._clean_message(msg, chat_id) for msg in messages if self._validate_message(msg)]
                
                if valid_messages:
                    conversations_to_process.append({
                        'chat_id': chat_id,
                        'messages': valid_messages,
                        'customer_name': customer_names.get(chat_id)
                    })

            if not conversations_to_process:
                logger.info("No new conversations to process.")
                await progress_tracker.complete_upload(upload_id, True)
                return 0, 0, upload_id

            logger.info(f"Creating records for {len(conversations_to_process)} conversations in memory...")
            new_conversations = []
            for conv_data in conversations_to_process:
                conversation = Conversation(
                    fb_chat_id=conv_data['chat_id'],
                    customer_name=conv_data['customer_name']
                )
                
                messages_by_day = self._group_messages_by_day(conv_data['messages'])
                
                for date, day_messages in messages_by_day.items():
                    daily_analysis = DailyAnalysis(analysis_date=date)
                    for msg_data in day_messages:
                        message = Message(
                            fb_chat_id=conv_data['chat_id'],
                            message_content=msg_data['message_content'],
                            direction=msg_data['direction'],
                            social_create_time=msg_data['social_create_time'],
                            agent_info=msg_data.get('agent_info')
                        )
                        conversation.messages.append(message)
                    conversation.daily_analyses.append(daily_analysis)

                conversation.total_messages = len(conversation.messages)
                conversation.customer_messages = sum(1 for m in conversation.messages if m.direction == 'to_company')
                conversation.agent_messages = sum(1 for m in conversation.messages if m.direction == 'to_client')
                
                new_conversations.append(conversation)

            batches = batch_service.create_daily_analysis_batches(new_conversations, db)
            logger.info(f"Splitting work into {len(batches)} batches.")

            jobs = await job_service.create_jobs_for_upload(upload_id, batches, db)
            
            logger.info(f"Starting AI analysis for {len(jobs)} jobs...")
            tasks = [job_service.process_job(job.id) for job in jobs]
            await asyncio.gather(*tasks)

            conversations_processed = len(new_conversations)
            messages_processed = sum(len(conv.messages) for conv in new_conversations)

            for conv in new_conversations:
                self._mark_chat_processed(db, conv.fb_chat_id, len(conv.messages))
            
            db.commit()

            logger.info(f"Upload process {upload_id} completed successfully.")
            await progress_tracker.complete_upload(upload_id, True)
            
            return conversations_processed, messages_processed, upload_id

        except json.JSONDecodeError as e:
            await progress_tracker.add_error(upload_id, f"Invalid JSON format: {str(e)}")
            await progress_tracker.complete_upload(upload_id, False)
            raise ValueError(f"Invalid JSON format: {e}")
        except Exception as e:
            logger.error(f"Error processing file: {e}", exc_info=True)
            await progress_tracker.add_error(upload_id, str(e))
            await progress_tracker.complete_upload(upload_id, False)
            db.rollback()
            raise

    def _parse_and_normalize_input(self, file_content: str) -> Tuple[Dict[str, List[Dict]], Dict[str, str]]:
        """
        Detects the JSON format (raw array, pre-grouped dict, or single-key raw dict) and normalizes it.
        """
        # Clean the input by stripping leading non-JSON text (like SQL comments)
        first_char_index = -1
        for i, char in enumerate(file_content):
            if char in ['{', '[']:
                first_char_index = i
                break
        
        if first_char_index == -1:
            raise ValueError("Could not find a valid JSON object or array in the file.")
            
        json_text = file_content[first_char_index:]
        
        # Parse the text into a Python object first
        parsed_data = json.loads(json_text)

        # Now, sniff the format based on the *type* and *structure* of the parsed data
        if isinstance(parsed_data, list):
            logger.info("Detected raw JSON array format.")
            return self._preprocess_and_group_raw_data(parsed_data)
        
        elif isinstance(parsed_data, dict):
            # Check for the single-key raw format (like FB17-23.json)
            if len(parsed_data.keys()) == 1:
                logger.info("Detected single-key object format. Extracting value.")
                # The value is the list of messages
                raw_messages = next(iter(parsed_data.values()))
                if isinstance(raw_messages, list):
                    return self._preprocess_and_group_raw_data(raw_messages)
            
            # Otherwise, assume it's the pre-grouped format
            logger.info("Detected pre-grouped JSON object format.")
            return self._normalize_grouped_data(parsed_data)
        
        else:
            raise ValueError("Unsupported JSON format. Must be an object or an array.")

    def _preprocess_and_group_raw_data(self, raw_messages: List[Dict]) -> Tuple[Dict[str, List[Dict]], Dict[str, str]]:
        """
        Parses a raw flat array, groups messages by conversation, and normalizes fields.
        """
        grouped_messages = {}
        customer_names = {}

        for msg in raw_messages:
            # Normalize field names from the raw format
            chat_id = msg.get("FB_ID") or msg.get("fb_chat_id") # Handle both old and new field names
            if not chat_id:
                continue

            if chat_id not in grouped_messages:
                grouped_messages[chat_id] = []
            
            # Normalize message fields into the standard format the application expects
            normalized_msg = {
                "MESSAGE_CONTENT": msg.get("MESSAGE") or msg.get("MESSAGE_CONTENT"),
                "DIRECTION": msg.get("DIRECTION"),
                "SOCIAL_CREATE_TIME": msg.get("SOCIAL_CREATE_TIME"),
                "agent_name": msg.get("AGENT_FIRSTNAME") or msg.get("AGENT_USERNAME"),
                "agent_email": msg.get("AGENT_EMAIL"),
            }
            grouped_messages[chat_id].append(normalized_msg)

            if chat_id not in customer_names and (msg.get("FB_USERNAME") or msg.get("facebook_username")):
                customer_names[chat_id] = msg.get("FB_USERNAME") or msg.get("facebook_username")
        
        return grouped_messages, customer_names

    def _normalize_grouped_data(self, grouped_data: Dict[str, List[Dict]]) -> Tuple[Dict[str, List[Dict]], Dict[str, str]]:
        """
        Parses a pre-grouped dictionary and ensures its fields are normalized.
        """
        # Customer names are not available in this format
        customer_names = {}
        
        # The structure is already grouped, so we just need to ensure field names are consistent.
        # This is a pass-through for now, but could contain normalization logic if the grouped format changes.
        return grouped_data, customer_names
    
    def _group_messages_by_day(self, messages: List[Dict]) -> Dict[datetime.date, List[Dict]]:
        """Groups a list of messages by their creation date."""
        grouped = {}
        for msg in messages:
            msg_date = msg['social_create_time'].date()
            if msg_date not in grouped:
                grouped[msg_date] = []
            grouped[msg_date].append(msg)
        return grouped
    
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
        
        # Filter out the exact autoresponse message
        auto_reply_text = "Thank you for reaching out! Did you know that you can now dial *977# to report a power outage or get your last three tokens instantly?"
        if message_content == auto_reply_text:
            logger.info(f"Filtering exact autoresponse message: {message_content[:100]}...")
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
            'agent_info': {
                "name": msg.get("agent_name"),
                "email": msg.get("agent_email")
            }
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