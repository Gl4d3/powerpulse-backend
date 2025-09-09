import json
import logging
import asyncio
import uuid
from typing import Dict, List, Any, Tuple
from datetime import datetime, date
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import tuple_, func
from database import SessionLocal

from config import settings
from services import batch_service, job_service
# from services.progress_tracker import progress_tracker
from services.analytics_service import analytics_service
from models import Conversation, Message, DailyAnalysis, Job, job_daily_analyses

logger = logging.getLogger(__name__)

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
            grouped_data, customer_names = self._parse_and_normalize_input(file_content)
            
            all_possible_analyses: Dict[Tuple[str, date], List[Dict]] = {}
            for chat_id, messages in grouped_data.items():
                valid_messages = [self._clean_message(msg, chat_id) for msg in messages if self._validate_message(msg)]
                if not valid_messages:
                    continue
                
                messages_by_day = self._group_messages_by_day(valid_messages)
                for day, day_messages in messages_by_day.items():
                    all_possible_analyses[(chat_id, day)] = day_messages

            if not all_possible_analyses:
                logger.info("No valid daily conversations to process.")
                return 0, 0, upload_id

            # If force_reprocess is True, we process everything.
            if force_reprocess:
                new_analyses_to_process = all_possible_analyses
                logger.info("force_reprocess is True. Processing all daily analyses from the file.")
            else:
                # Query for analyses that are part of a COMPLETED job.
                completed_keys_query = db.query(Conversation.fb_chat_id, DailyAnalysis.analysis_date)\
                    .join(DailyAnalysis, Conversation.id == DailyAnalysis.conversation_id)\
                    .join(job_daily_analyses, DailyAnalysis.id == job_daily_analyses.c.daily_analysis_id)\
                    .join(Job, Job.id == job_daily_analyses.c.job_id)\
                    .filter(Job.status == 'completed')
                
                completed_keys_raw = completed_keys_query.all()
                completed_keys = set((row[0], row[1].date()) for row in completed_keys_raw)
                
                new_analyses_to_process = {k: v for k, v in all_possible_analyses.items() if k not in completed_keys}
                
                logger.info(f"Found {len(new_analyses_to_process)} daily analyses to process out of {len(all_possible_analyses)} total.")
                logger.info(f"Skipping {len(completed_keys)} analyses that were part of already completed jobs.")

            if not new_analyses_to_process:
                logger.info("No new daily analyses to process.")
                return 0, 0, upload_id

            # Phase 3: Fetch existing objects and create new ones
            all_convo_ids_to_process = {k[0] for k in new_analyses_to_process.keys()}

            conversations_in_db = db.query(Conversation).filter(Conversation.fb_chat_id.in_(all_convo_ids_to_process)).all()
            conversation_map = {c.fb_chat_id: c for c in conversations_in_db}

            q_existing_da = db.query(DailyAnalysis).options(joinedload(DailyAnalysis.conversation)).filter(
                DailyAnalysis.conversation_id.in_([c.id for c in conversations_in_db])
            )
            existing_daily_analyses = q_existing_da.all()
            existing_analysis_map = {(da.conversation.fb_chat_id, da.analysis_date.date()): da for da in existing_daily_analyses}

            logger.info(f"Found {len(existing_analysis_map)} existing daily analyses to re-process.")

            daily_analyses_for_jobs: List[DailyAnalysis] = []

            for (chat_id, day), messages in new_analyses_to_process.items():
                conversation = conversation_map.get(chat_id)
                if not conversation:
                    conversation = Conversation(fb_chat_id=chat_id, customer_name=customer_names.get(chat_id))
                    db.add(conversation)
                    conversation_map[chat_id] = conversation
                
                daily_analysis = existing_analysis_map.get((chat_id, day))
                if not daily_analysis:
                    daily_analysis = DailyAnalysis(analysis_date=day)
                    conversation.daily_analyses.append(daily_analysis)

                # --- FIXED LOGIC ---
                # Process messages regardless of whether DailyAnalysis is new, but prevent duplicates.
                existing_timestamps_query = db.query(Message.social_create_time).filter(
                    Message.conversation_id == conversation.id,
                    func.date(Message.social_create_time) == day
                )
                existing_timestamps = {ts[0] for ts in existing_timestamps_query.all()}

                for msg_data in messages:
                    # Only add the message if its timestamp doesn't already exist for this day.
                    if msg_data['social_create_time'] not in existing_timestamps:
                        message = Message(
                            fb_chat_id=chat_id,
                            message_content=msg_data['message_content'],
                            direction=msg_data['direction'],
                            social_create_time=msg_data['social_create_time'],
                            agent_info=msg_data.get('agent_info')
                        )
                        conversation.messages.append(message)
                        # Add the new timestamp to the set to handle duplicates within the same file
                        existing_timestamps.add(msg_data['social_create_time'])
                
                daily_analyses_for_jobs.append(daily_analysis)

            db.commit()
            
            self._update_conversation_statistics(db, list(conversation_map.values()))

            # Phase 4: Create and process jobs
            batches = batch_service.create_daily_analysis_batches(daily_analyses_for_jobs)
            logger.info(f"Splitting work into {len(batches)} batches.")

            jobs = job_service.create_jobs_for_upload(upload_id, batches, db)
            
            logger.info(f"Created {len(jobs)} jobs for upload {upload_id}. The worker will process them asynchronously.")

            conversations_processed = len(conversation_map)
            messages_processed = sum(len(v) for v in new_analyses_to_process.values())

            logger.info(f"Upload process {upload_id} completed successfully.")
            # progress_tracker.complete_upload(db, upload_id, True)
            
            return conversations_processed, messages_processed, upload_id

        except json.JSONDecodeError as e:
            # progress_tracker.add_error(db, upload_id, f"Invalid JSON format: {str(e)}")
            # progress_tracker.complete_upload(db, upload_id, False)
            raise ValueError(f"Invalid JSON format: {e}")
        except Exception as e:
            logger.error(f"Error processing file: {e}", exc_info=True)
            # progress_tracker.add_error(db, upload_id, str(e))
            # progress_tracker.complete_upload(db, upload_id, False)
            db.rollback()
            raise

    def _parse_and_normalize_input(self, file_content: str) -> Tuple[Dict[str, List[Dict]], Dict[str, str]]:
        """
        Detects the JSON format (raw array, pre-grouped dict, or single-key raw dict) and normalizes it.
        """
        first_char_index = -1
        for i, char in enumerate(file_content):
            if char in ['{', '[']:
                first_char_index = i
                break
        
        if first_char_index == -1:
            raise ValueError("Could not find a valid JSON object or array in the file.")
            
        json_text = file_content[first_char_index:]
        parsed_data = json.loads(json_text)

        if isinstance(parsed_data, list):
            logger.info("Detected raw JSON array format.")
            return self._preprocess_and_group_raw_data(parsed_data)
        
        elif isinstance(parsed_data, dict):
            if len(parsed_data.keys()) == 1:
                logger.info("Detected single-key object format. Extracting value.")
                raw_messages = next(iter(parsed_data.values()))
                if isinstance(raw_messages, list):
                    return self._preprocess_and_group_raw_data(raw_messages)
            
            logger.info("Detected pre-grouped JSON object format.")
            return self._normalize_grouped_data(parsed_data)
        
        else:
            raise ValueError("Unsupported JSON format. Must be an object or an array.")

    def _preprocess_and_group_raw_data(self, raw_messages: List[Dict]) -> Tuple[Dict[str, List[Dict]], Dict[str, str]]:
        grouped_messages = {}
        customer_names = {}

        for msg in raw_messages:
            chat_id = msg.get("FB_ID") or msg.get("fb_chat_id")
            if not chat_id:
                continue

            if chat_id not in grouped_messages:
                grouped_messages[chat_id] = []
            
            normalized_msg = {
                "MESSAGE_CONTENT": msg.get("MESSAGE") or msg.get("MESSAGE_CONTENT"),
                "DIRECTION": msg.get("DIRECTION"),
                "SOCIAL_CREATE_TIME": msg.get("SOCIAL_CREATE_TIME"),
                "agent_name": msg.get("AGENT_USERNAME") or msg.get("agent_username"),
                "agent_email": msg.get("AGENT_EMAIL") or msg.get("agent_email")
            }
            grouped_messages[chat_id].append(normalized_msg)

            if chat_id not in customer_names and (msg.get("FB_USERNAME") or msg.get("facebook_username")):
                customer_names[chat_id] = msg.get("FB_USERNAME") or msg.get("facebook_username")
        
        return grouped_messages, customer_names

    def _normalize_grouped_data(self, grouped_data: Dict[str, List[Dict]]) -> Tuple[Dict[str, List[Dict]], Dict[str, str]]:
        customer_names = {}
        return grouped_data, customer_names
    
    def _group_messages_by_day(self, messages: List[Dict]) -> Dict[datetime.date, List[Dict]]:
        grouped = {}
        for msg in messages:
            msg_date = msg['social_create_time'].date()
            if msg_date not in grouped:
                grouped[msg_date] = []
            grouped[msg_date].append(msg)
        return grouped
    
    def _validate_message(self, msg: Dict) -> bool:
        required_fields = ['MESSAGE_CONTENT', 'DIRECTION', 'SOCIAL_CREATE_TIME']
        if not all(field in msg for field in required_fields):
            return False
        
        if msg['DIRECTION'] not in ['to_company', 'to_client']:
            return False
        
        message_content = msg['MESSAGE_CONTENT']
        if not message_content or not isinstance(message_content, str):
            return False
        
        auto_reply_text = "Thank you for reaching out! Did you know that you can now dial *977# to report a power outage or get your last three tokens instantly?"
        if message_content == auto_reply_text:
            return False
        
        return True
    
    def _clean_message(self, msg: Dict, chat_id: str) -> Dict:
        timestamp_str = msg['SOCIAL_CREATE_TIME']
        social_create_time = None
        if isinstance(timestamp_str, str):
            try:
                # Handles ISO format like "2025-08-18T10:55:25.000Z"
                aware_dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                social_create_time = aware_dt.replace(tzinfo=None) # Convert to naive
            except ValueError:
                try:
                    # Handles string format like "2025-08-18 10:55:25"
                    social_create_time = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    social_create_time = datetime.utcnow() # Fallback to naive UTC time
        else:
            social_create_time = datetime.utcnow() # Fallback to naive UTC time
        
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
    
    def _update_conversation_statistics(self, db: Session, conversations: List[Conversation]) -> None:
        try:
            for conversation in conversations:
                if not conversation.messages:
                    continue
                
                total_messages = len(conversation.messages)
                customer_messages = len([m for m in conversation.messages if m.direction == 'to_company'])
                agent_messages = total_messages - customer_messages
                
                sorted_messages = sorted(conversation.messages, key=lambda m: m.social_create_time)
                first_message_time = sorted_messages[0].social_create_time
                last_message_time = sorted_messages[-1].social_create_time
                
                conversation.total_messages = total_messages
                conversation.customer_messages = customer_messages
                conversation.agent_messages = agent_messages
                conversation.first_message_time = first_message_time
                conversation.last_message_time = last_message_time
                
            logger.info(f"Updated statistics for {len(conversations)} conversations")
                
        except Exception as e:
            logger.error(f"Error updating conversation statistics: {e}", exc_info=True)

# Global optimized service instance
optimized_file_service = OptimizedFileService()
