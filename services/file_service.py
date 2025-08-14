import json
import logging
from typing import Dict, List, Any, Tuple
from datetime import datetime
from sqlalchemy.orm import Session

from models import Message, Conversation, ProcessedChat
from services.gpt_service import gpt_service

logger = logging.getLogger(__name__)

class FileService:
    def __init__(self):
        pass
    
    async def process_grouped_chats_json(self, file_content: str, db: Session) -> Tuple[int, int]:
        """
        Process uploaded JSON file with grouped_chats format.
        Returns (conversations_processed, messages_processed)
        """
        try:
            # Parse JSON
            data = json.loads(file_content)
            
            if not isinstance(data, dict):
                raise ValueError("JSON must be an object with chat_id keys")
            
            conversations_processed = 0
            messages_processed = 0
            
            for chat_id, messages in data.items():
                if not isinstance(messages, list):
                    logger.warning(f"Skipping chat_id {chat_id}: messages must be an array")
                    continue
                
                # Check if this chat has already been processed
                if self._is_chat_processed(db, chat_id):
                    logger.info(f"Skipping already processed chat: {chat_id}")
                    continue
                
                # Process this conversation
                processed_messages = await self._process_conversation(db, chat_id, messages)
                
                if processed_messages > 0:
                    conversations_processed += 1
                    messages_processed += processed_messages
                    
                    # Mark chat as processed
                    self._mark_chat_processed(db, chat_id, processed_messages)
            
            db.commit()
            logger.info(f"Processed {conversations_processed} conversations, {messages_processed} messages")
            
            return conversations_processed, messages_processed
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON format: {e}")
            raise ValueError(f"Invalid JSON format: {e}")
        except Exception as e:
            logger.error(f"Error processing file: {e}")
            db.rollback()
            raise
    
    async def _process_conversation(self, db: Session, chat_id: str, messages: List[Dict]) -> int:
        """Process a single conversation and its messages"""
        try:
            if not messages:
                return 0
            
            # Validate and clean messages
            valid_messages = []
            for msg in messages:
                if self._validate_message(msg):
                    valid_messages.append(self._clean_message(msg, chat_id))
            
            if not valid_messages:
                logger.warning(f"No valid messages found for chat {chat_id}")
                return 0
            
            # Sort messages by timestamp
            valid_messages.sort(key=lambda x: x['social_create_time'])
            
            # Analyze with GPT
            message_analyses, conversation_analysis = await gpt_service.analyze_conversation_batch(valid_messages)
            
            # Save messages to database
            saved_messages = self._save_messages(db, valid_messages, message_analyses)
            
            # Calculate conversation metrics
            conversation_metrics = self._calculate_conversation_metrics(valid_messages, conversation_analysis)
            
            # Save conversation record
            self._save_conversation(db, chat_id, conversation_metrics, valid_messages)
            
            return len(saved_messages)
            
        except Exception as e:
            logger.error(f"Error processing conversation {chat_id}: {e}")
            raise
    
    def _validate_message(self, msg: Dict) -> bool:
        """Validate required message fields"""
        required_fields = ['MESSAGE_CONTENT', 'DIRECTION', 'SOCIAL_CREATE_TIME']
        
        for field in required_fields:
            if field not in msg:
                return False
        
        # Validate direction
        if msg['DIRECTION'] not in ['to_company', 'to_client']:
            return False
        
        # Validate content
        if not msg['MESSAGE_CONTENT'] or not isinstance(msg['MESSAGE_CONTENT'], str):
            return False
        
        return True
    
    def _clean_message(self, msg: Dict, chat_id: str) -> Dict:
        """Clean and standardize message data"""
        # Parse timestamp
        timestamp_str = msg['SOCIAL_CREATE_TIME']
        if isinstance(timestamp_str, str):
            # Try different timestamp formats
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
            'agent_info': msg.get('agent_info') or msg.get('AGENT_INFO')
        }
    
    def _save_messages(self, db: Session, messages: List[Dict], analyses: List[Dict]) -> List[Message]:
        """Save messages to database with analysis results"""
        saved_messages = []
        
        # Create analysis lookup
        analysis_lookup = {}
        for analysis in analyses:
            content = analysis.get('message_content', '')
            if content:
                analysis_lookup[content] = analysis
        
        # Calculate response times and first contact flags
        messages_by_direction = {'to_company': [], 'to_client': []}
        for msg in messages:
            messages_by_direction[msg['direction']].append(msg)
        
        for msg in messages:
            # Get analysis results
            analysis = analysis_lookup.get(msg['message_content'], {})
            
            # Calculate response time for agent messages
            response_time = None
            if msg['direction'] == 'to_client':
                response_time = self._calculate_response_time(msg, messages_by_direction['to_company'])
            
            # Determine if this is first contact
            is_first_contact = self._is_first_contact(msg, messages)
            
            message_record = Message(
                fb_chat_id=msg['fb_chat_id'],
                message_content=msg['message_content'],
                direction=msg['direction'],
                social_create_time=msg['social_create_time'],
                agent_info=msg.get('agent_info'),
                sentiment_score=analysis.get('sentiment_score'),
                sentiment_confidence=analysis.get('sentiment_confidence'),
                topics=analysis.get('topics'),
                is_first_contact=is_first_contact,
                response_time_minutes=response_time
            )
            
            db.add(message_record)
            saved_messages.append(message_record)
        
        return saved_messages
    
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
            # Sort by timestamp and check if this is the first message
            sorted_messages = sorted(all_messages, key=lambda x: x['social_create_time'])
            return sorted_messages[0]['message_content'] == message['message_content']
        except:
            return False
    
    def _calculate_conversation_metrics(self, messages: List[Dict], conversation_analysis: Dict) -> Dict:
        """Calculate aggregated metrics for the conversation"""
        customer_messages = [msg for msg in messages if msg['direction'] == 'to_company']
        agent_messages = [msg for msg in messages if msg['direction'] == 'to_client']
        
        # Calculate average sentiment from customer messages
        # This would be set later when we have the sentiment scores from saved messages
        
        # Determine FCR - simplified: if conversation analysis indicates resolution
        fcr = conversation_analysis.get('resolution_achieved', False)
        
        # Calculate average response time from agent messages
        response_times = []
        for agent_msg in agent_messages:
            rt = self._calculate_response_time(agent_msg, customer_messages)
            if rt is not None:
                response_times.append(rt)
        
        avg_response_time = sum(response_times) / len(response_times) if response_times else None
        
        # Get time range
        sorted_messages = sorted(messages, key=lambda x: x['social_create_time'])
        first_time = sorted_messages[0]['social_create_time'] if sorted_messages else None
        last_time = sorted_messages[-1]['social_create_time'] if sorted_messages else None
        
        return {
            'total_messages': len(messages),
            'customer_messages': len(customer_messages),
            'agent_messages': len(agent_messages),
            'satisfaction_score': conversation_analysis.get('satisfaction_score'),
            'satisfaction_confidence': conversation_analysis.get('satisfaction_confidence'),
            'is_satisfied': conversation_analysis.get('is_satisfied'),
            'first_contact_resolution': fcr,
            'avg_response_time_minutes': avg_response_time,
            'first_message_time': first_time,
            'last_message_time': last_time,
            'common_topics': conversation_analysis.get('common_topics', [])
        }
    
    def _save_conversation(self, db: Session, chat_id: str, metrics: Dict, messages: List[Dict]):
        """Save or update conversation record"""
        
        # Check if conversation already exists
        existing = db.query(Conversation).filter(Conversation.fb_chat_id == chat_id).first()
        
        if existing:
            # Update existing conversation
            for key, value in metrics.items():
                setattr(existing, key, value)
            existing.updated_at = datetime.utcnow()
        else:
            # Create new conversation
            conversation = Conversation(
                fb_chat_id=chat_id,
                **metrics
            )
            db.add(conversation)
    
    def _is_chat_processed(self, db: Session, chat_id: str) -> bool:
        """Check if chat has already been processed"""
        return db.query(ProcessedChat).filter(ProcessedChat.fb_chat_id == chat_id).first() is not None
    
    def _mark_chat_processed(self, db: Session, chat_id: str, message_count: int):
        """Mark chat as processed"""
        processed_chat = ProcessedChat(
            fb_chat_id=chat_id,
            message_count=message_count
        )
        db.add(processed_chat)

# Global instance
file_service = FileService()
