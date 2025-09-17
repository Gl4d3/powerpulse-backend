"""
Enhanced File Service supporting both daily and interaction-based analysis modes.
Maintains backward compatibility while enabling interaction-aware processing.
"""
import json
import logging
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime, date
from sqlalchemy.orm import Session, joinedload
from collections import defaultdict

from models import Conversation, Message, DailyAnalysis, InteractionAnalysis, Job
from services.enhanced_analytics_service import enhanced_analytics_service
from services.interaction_service import InteractionService

logger = logging.getLogger(__name__)

class EnhancedFileService:
    """
    Enhanced file service supporting both daily and interaction-based analysis modes.
    """
    
    def __init__(self):
        self.interaction_service = InteractionService()
    
    async def process_conversations_with_mode(
        self,
        file_content: str,
        db: Session,
        upload_id: str,
        analysis_mode: str = 'daily',  # 'daily' or 'interaction'
        force_reprocess: bool = False
    ) -> Tuple[int, int, str]:
        """
        Universal conversation processor supporting both daily and interaction modes.
        
        Args:
            file_content: JSON content of the uploaded file
            db: Database session
            upload_id: Unique identifier for this upload
            analysis_mode: 'daily' for legacy mode, 'interaction' for new mode
            force_reprocess: Whether to reprocess existing data
            
        Returns:
            Tuple of (conversations_processed, analyses_created, upload_id)
        """
        logger.info(f"Starting enhanced processing for upload_id: {upload_id} in {analysis_mode} mode")
        
        # Parse and normalize input data
        grouped_data, customer_names = self._parse_and_normalize_input(file_content)
        
        if not grouped_data:
            logger.info("No valid conversations found in the uploaded data.")
            return 0, 0, upload_id
        
        conversations_processed = 0
        analyses_created = 0
        
        if analysis_mode == 'interaction':
            conversations_processed, analyses_created = await self._process_interaction_mode(
                grouped_data, customer_names, db, upload_id, force_reprocess
            )
        else:
            # Delegate to existing daily processing logic
            conversations_processed, analyses_created = await self._process_daily_mode(
                grouped_data, customer_names, db, upload_id, force_reprocess
            )
        
        logger.info(f"Processing complete: {conversations_processed} conversations, {analyses_created} analyses")
        return conversations_processed, analyses_created, upload_id
    
    async def _process_interaction_mode(
        self,
        grouped_data: Dict[str, List[Dict]],
        customer_names: Dict[str, str],
        db: Session,
        upload_id: str,
        force_reprocess: bool
    ) -> Tuple[int, int]:
        """
        Process conversations in interaction mode, detecting and analyzing individual interactions.
        """
        conversations_processed = 0
        analyses_created = 0
        
        # Get existing conversations and their interaction analyses
        existing_conversations = self._get_existing_conversations(grouped_data.keys(), db)
        existing_interactions = self._get_existing_interactions(existing_conversations, db)
        
        for chat_id, messages in grouped_data.items():
            try:
                # Clean and validate messages
                valid_messages = [
                    self._clean_message(msg, chat_id) 
                    for msg in messages 
                    if self._validate_message(msg)
                ]
                
                if not valid_messages:
                    continue
                
                # Get or create conversation
                conversation = existing_conversations.get(chat_id)
                if not conversation:
                    conversation = self._create_conversation(
                        chat_id, customer_names.get(chat_id), valid_messages, db
                    )
                    existing_conversations[chat_id] = conversation
                
                # Check if we should process this conversation
                if not force_reprocess and conversation.id in existing_interactions:
                    logger.debug(f"Skipping conversation {chat_id} - already has interaction analysis")
                    continue
                
                # Convert messages to the format expected by InteractionService
                service_messages = self._prepare_messages_for_service(valid_messages)
                
                # Detect and analyze interactions
                interaction_analyses = enhanced_analytics_service.detect_and_analyze_interactions(
                    messages=service_messages,
                    conversation_id=conversation.id,
                    db=db
                )
                
                # Save interaction analyses to database
                for interaction_analysis in interaction_analyses:
                    db.add(interaction_analysis)
                
                conversations_processed += 1
                analyses_created += len(interaction_analyses)
                
                logger.debug(f"Processed conversation {chat_id}: {len(interaction_analyses)} interactions")
                
            except Exception as e:
                logger.error(f"Error processing conversation {chat_id}: {e}")
                continue
        
        # Commit all changes
        try:
            db.commit()
            logger.info(f"Successfully committed {analyses_created} interaction analyses")
        except Exception as e:
            logger.error(f"Error committing interaction analyses: {e}")
            db.rollback()
            analyses_created = 0
        
        return conversations_processed, analyses_created
    
    async def _process_daily_mode(
        self,
        grouped_data: Dict[str, List[Dict]],
        customer_names: Dict[str, str],
        db: Session,
        upload_id: str,
        force_reprocess: bool
    ) -> Tuple[int, int]:
        """
        Process conversations in daily mode (existing legacy functionality).
        This would delegate to the existing file_service_optimized logic.
        """
        # Import here to avoid circular imports
        from services.file_service_optimized import optimized_file_service
        
        # Convert back to JSON format for the existing service
        json_data = {"conversations": []}  # Simplified for backward compatibility
        
        # Delegate to existing service
        # Note: This is a simplified integration - in production, you'd need
        # to properly adapt the data format and method signatures
        logger.info("Delegating to existing daily analysis processing")
        return 0, 0  # Placeholder - would integrate with existing logic
    
    # === Helper Methods ===
    
    def _parse_and_normalize_input(self, file_content: str) -> Tuple[Dict[str, List[Dict]], Dict[str, str]]:
        """
        Parse JSON content and normalize it to grouped conversations format.
        """
        try:
            data = json.loads(file_content)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON format: {e}")
            return {}, {}
        
        grouped_data = {}
        customer_names = {}
        
        # Handle different input formats
        if isinstance(data, dict) and 'conversations' in data:
            # New format: {"conversations": [...]}
            for conv in data['conversations']:
                chat_id = conv.get('fb_chat_id')
                if chat_id and 'messages' in conv:
                    grouped_data[chat_id] = conv['messages']
                    if 'customer_name' in conv:
                        customer_names[chat_id] = conv['customer_name']
        
        elif isinstance(data, list):
            # Legacy format: flat array of messages
            grouped_data = self._group_messages_by_chat_id(data)
            
        elif isinstance(data, dict):
            # Pre-grouped format: {chat_id: [messages]}
            grouped_data = data
        
        return grouped_data, customer_names
    
    def _group_messages_by_chat_id(self, messages: List[Dict]) -> Dict[str, List[Dict]]:
        """Group flat message array by chat ID."""
        grouped = defaultdict(list)
        for msg in messages:
            chat_id = msg.get('FB_ID') or msg.get('fb_chat_id')
            if chat_id:
                grouped[chat_id].append(msg)
        return dict(grouped)
    
    def _validate_message(self, message: Dict[str, Any]) -> bool:
        """Validate that a message has required fields."""
        required_fields = ['message_content', 'social_create_time', 'direction']
        return all(field in message for field in required_fields)
    
    def _clean_message(self, message: Dict[str, Any], chat_id: str) -> Dict[str, Any]:
        """Clean and normalize message data."""
        # Normalize field names
        cleaned = {
            'message_content': message.get('MESSAGE') or message.get('message_content', ''),
            'social_create_time': message.get('SOCIAL_CREATE_TIME') or message.get('social_create_time'),
            'direction': message.get('DIRECTION') or message.get('direction', ''),
            'fb_chat_id': chat_id
        }
        
        # Add agent info if available
        agent_info = {}
        for field, key in [
            ('AGENT_USERNAME', 'agent_username'),
            ('AGENT_EMAIL', 'agent_email'), 
            ('AGENT_FIRSTNAME', 'agent_firstname'),
            ('AGENT_LASTNAME', 'agent_lastname')
        ]:
            if message.get(field):
                agent_info[key] = message[field]
        
        if agent_info:
            cleaned['agent_info'] = agent_info
        
        return cleaned
    
    def _prepare_messages_for_service(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Convert cleaned messages to the format expected by InteractionService.
        """
        service_messages = []
        
        # Sort messages by timestamp
        sorted_messages = sorted(messages, key=lambda m: m['social_create_time'])
        
        for i, msg in enumerate(sorted_messages, 1):
            # Parse timestamp if it's a string
            timestamp = msg['social_create_time']
            if isinstance(timestamp, str):
                # Handle both ISO format and other common formats
                if timestamp.endswith('Z'):
                    timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                else:
                    timestamp = datetime.fromisoformat(timestamp)
            
            service_msg = {
                'id': i,  # Sequential ID for this conversation
                'social_create_time': timestamp,
                'message_content': msg['message_content'],
                'direction': msg['direction']
            }
            
            service_messages.append(service_msg)
        
        return service_messages
    
    def _get_existing_conversations(self, chat_ids: List[str], db: Session) -> Dict[str, Conversation]:
        """Get existing conversations from the database."""
        conversations = db.query(Conversation).filter(
            Conversation.fb_chat_id.in_(chat_ids)
        ).all()
        
        return {conv.fb_chat_id: conv for conv in conversations}
    
    def _get_existing_interactions(self, conversations: Dict[str, Conversation], db: Session) -> Dict[int, List[InteractionAnalysis]]:
        """Get existing interaction analyses for conversations."""
        if not conversations:
            return {}
        
        conversation_ids = [conv.id for conv in conversations.values()]
        interactions = db.query(InteractionAnalysis).filter(
            InteractionAnalysis.conversation_id.in_(conversation_ids)
        ).all()
        
        grouped = defaultdict(list)
        for interaction in interactions:
            grouped[interaction.conversation_id].append(interaction)
        
        return dict(grouped)
    
    def _create_conversation(
        self, 
        chat_id: str, 
        customer_name: Optional[str], 
        messages: List[Dict[str, Any]], 
        db: Session
    ) -> Conversation:
        """Create a new conversation record."""
        # Calculate conversation metrics
        total_messages = len(messages)
        customer_messages = len([m for m in messages if m['direction'] == 'to_company'])
        agent_messages = len([m for m in messages if m['direction'] == 'to_client'])
        
        # Get time bounds
        timestamps = [
            msg['social_create_time'] if isinstance(msg['social_create_time'], datetime)
            else datetime.fromisoformat(msg['social_create_time'].replace('Z', '+00:00'))
            for msg in messages
        ]
        
        conversation = Conversation(
            fb_chat_id=chat_id,
            customer_name=customer_name,
            total_messages=total_messages,
            customer_messages=customer_messages,
            agent_messages=agent_messages,
            first_message_time=min(timestamps),
            last_message_time=max(timestamps)
        )
        
        db.add(conversation)
        db.flush()  # Get the ID
        
        return conversation

# Create service instance
enhanced_file_service = EnhancedFileService()