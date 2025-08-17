import json
import logging
import asyncio
import uuid
from typing import Dict, List, Any, Tuple
from datetime import datetime
from sqlalchemy.orm import Session

from models import Message, Conversation, ProcessedChat
from services.gpt_service_optimized import get_optimized_gpt_service
from services.gemini_service import get_gemini_service
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
        Optimized processing of uploaded JSON file with real-time progress tracking.
        Returns (conversations_processed, messages_processed, upload_id)
        """
        upload_id = str(uuid.uuid4())
        
        try:
            # Parse JSON
            data = json.loads(file_content)
            
            if not isinstance(data, dict):
                raise ValueError("JSON must be an object with chat_id keys")
            
            # Start progress tracking
            total_conversations = len(data)
            await progress_tracker.start_upload(upload_id, total_conversations)
            
            # Pre-filter conversations and prepare for batch processing
            conversations_to_process = []
            conversations_processed = 0
            messages_processed = 0
            
            await progress_tracker.update_progress(upload_id, 0, "filtering_conversations", 
                                                 "Filtering conversations and autoresponses...")
            
            for chat_id, messages in data.items():
                if not isinstance(messages, list):
                    logger.warning(f"Skipping chat_id {chat_id}: messages must be an array")
                    continue
                
                # Check if this chat has already been processed
                if not force_reprocess and self._is_chat_processed(db, chat_id):
                    logger.info(f"Skipping already processed chat: {chat_id}")
                    continue
                
                # Validate and clean messages
                valid_messages = []
                for msg in messages:
                    if self._validate_message(msg):
                        valid_messages.append(self._clean_message(msg, chat_id))
                    elif "*977#" in str(msg.get('MESSAGE_CONTENT', '')):
                        await progress_tracker.increment_filtered(upload_id)
                
                if valid_messages:
                    conversations_to_process.append({
                        'chat_id': chat_id,
                        'messages': valid_messages
                    })
            
            if not conversations_to_process:
                await progress_tracker.complete_upload(upload_id, True)
                return 0, 0, upload_id
            
            # Update progress after filtering
            await progress_tracker.update_progress(
                upload_id, 0, "gpt_analysis", 
                f"Starting GPT analysis of {len(conversations_to_process)} conversations..."
            )
            
            # Create progress callback for GPT processing
            async def gpt_progress_callback(progress_pct: float, details: str):
                await progress_tracker.update_progress(
                    upload_id, 
                    int((progress_pct / 100) * len(conversations_to_process)),
                    "gpt_analysis",
                    details
                )
                await progress_tracker.increment_gpt_calls(upload_id)
            
            # Get AI service based on configuration
            if settings.AI_SERVICE.lower() == "gemini":
                from services.gemini_service import get_gemini_service
                ai_service = get_gemini_service(settings.GEMINI_API_KEY)
                logger.info("Using Google Gemini for AI analysis")
            else:
                from services.gpt_service_optimized import get_optimized_gpt_service
                ai_service = get_optimized_gpt_service(settings.OPENAI_API_KEY)
                logger.info("Using OpenAI GPT for AI analysis")
            
            # Batch analyze all conversations with AI service
            analysis_results = await ai_service.batch_analyze_conversations(
                conversations_to_process, 
                gpt_progress_callback
            )
            
            # Save results to database
            await progress_tracker.update_progress(upload_id, len(conversations_to_process), 
                                                 "saving_to_database", "Saving results to database...")
            
            for i, (conversation, analysis) in enumerate(zip(conversations_to_process, analysis_results)):
                try:
                    chat_id = conversation['chat_id']
                    messages = conversation['messages']
                    
                    # Save messages with analysis
                    saved_messages = await self._save_messages_optimized(db, messages, analysis)
                    
                    # Calculate and save conversation metrics
                    metrics = self._calculate_conversation_metrics_optimized(messages, analysis)
                    await self._save_conversation_optimized(db, chat_id, metrics)
                    
                    # Mark as processed
                    self._mark_chat_processed(db, chat_id, len(saved_messages))
                    
                    conversations_processed += 1
                    messages_processed += len(saved_messages)
                    
                    # Update progress
                    if i % 10 == 0:  # Update every 10 conversations
                        await progress_tracker.update_progress(
                            upload_id, conversations_processed, "saving_to_database",
                            f"Saved {conversations_processed}/{len(conversations_to_process)} conversations"
                        )
                
                except Exception as e:
                    logger.error(f"Error saving conversation {conversation['chat_id']}: {e}")
                    await progress_tracker.add_error(upload_id, f"Error saving {conversation['chat_id']}: {str(e)}")
            
            # Commit all changes
            db.commit()
            
            # Complete progress tracking
            await progress_tracker.complete_upload(upload_id, True)
            
            logger.info(f"Optimized processing completed: {conversations_processed} conversations, {messages_processed} messages")
            
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
    
    async def _save_messages_optimized(self, db: Session, messages: List[Dict], analysis: Dict) -> List[Message]:
        """Save messages with optimized analysis results"""
        saved_messages = []
        
        # Get message analyses from the comprehensive analysis
        message_analyses = analysis.get('message_analyses', [])
        
        # Create lookup for fast matching
        analysis_lookup = {}
        for msg_analysis in message_analyses:
            content = msg_analysis.get('message_content', '').strip()
            if content:
                analysis_lookup[content] = msg_analysis
        
        # Calculate response times
        customer_messages = [m for m in messages if m['direction'] == 'to_company']
        
        for msg in messages:
            # Get analysis results
            content = msg['message_content']
            msg_analysis = analysis_lookup.get(content, {})
            
            # Calculate response time for agent messages
            response_time = None
            if msg['direction'] == 'to_client':
                response_time = self._calculate_response_time(msg, customer_messages)
            
            # Determine if this is first contact
            is_first_contact = self._is_first_contact(msg, messages)
            
            message_record = Message(
                fb_chat_id=msg['fb_chat_id'],
                message_content=content,
                direction=msg['direction'],
                social_create_time=msg['social_create_time'],
                agent_info=msg.get('agent_info'),
                sentiment_score=msg_analysis.get('sentiment_score'),
                sentiment_confidence=msg_analysis.get('sentiment_confidence'),
                topics=msg_analysis.get('topics'),
                is_first_contact=is_first_contact,
                response_time_minutes=response_time
            )
            
            db.add(message_record)
            saved_messages.append(message_record)
        
        return saved_messages
    
    def _calculate_conversation_metrics_optimized(self, messages: List[Dict], analysis: Dict) -> Dict:
        """Calculate conversation-level metrics using optimized analysis"""
        try:
            # Basic counts
            total_messages = len(messages)
            customer_messages = len([m for m in messages if m['direction'] == 'to_company'])
            agent_messages = len([m for m in messages if m['direction'] == 'to_client'])
            
            # Time bounds
            timestamps = [m['social_create_time'] for m in messages]
            first_message_time = min(timestamps) if timestamps else None
            last_message_time = max(timestamps) if timestamps else None
            
            # Response time calculation
            avg_response_time = self._calculate_avg_response_time(messages)
            
            # Calculate average sentiment from customer messages
            customer_msgs_analysis = [
                analysis['message_analyses'][i] 
                for i, msg in enumerate(messages) 
                if msg['direction'] == 'to_company' and i < len(analysis.get('message_analyses', []))
            ]
            
            sentiments = [
                msg.get('sentiment_score', 0.0) 
                for msg in customer_msgs_analysis 
                if msg.get('sentiment_score') is not None
            ]
            
            avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0.0
            
            return {
                'total_messages': total_messages,
                'customer_messages': customer_messages,
                'agent_messages': agent_messages,
                'satisfaction_score': analysis.get('satisfaction_score', 3),
                'satisfaction_confidence': analysis.get('satisfaction_confidence', 0.5),
                'is_satisfied': analysis.get('is_satisfied', False),
                'avg_sentiment': avg_sentiment,
                'first_contact_resolution': analysis.get('resolution_achieved', False),
                'avg_response_time_minutes': avg_response_time,
                'first_message_time': first_message_time,
                'last_message_time': last_message_time,
                'common_topics': analysis.get('common_topics', [])
            }
            
        except Exception as e:
            logger.error(f"Error calculating conversation metrics: {e}")
            raise
    
    async def _save_conversation_optimized(self, db: Session, chat_id: str, metrics: Dict):
        """Save conversation record to database"""
        try:
            # Check if conversation already exists
            existing = db.query(Conversation).filter(Conversation.fb_chat_id == chat_id).first()
            
            if existing:
                # Update existing conversation
                for key, value in metrics.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
            else:
                # Create new conversation
                conversation = Conversation(
                    fb_chat_id=chat_id,
                    **metrics
                )
                db.add(conversation)
            
        except Exception as e:
            logger.error(f"Error saving conversation {chat_id}: {e}")
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