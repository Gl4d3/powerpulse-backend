"""
Interaction Service for PowerPulse Analytics.

This service detects natural customer service interaction boundaries within conversations,
enabling more accurate CSI analysis by grouping messages into logical issue cycles
rather than arbitrary daily windows.

Key Features:
- Rule-based detection (primary method for cost efficiency)
- AI fallback for complex cases (secondary method)
- Utility-specific pattern recognition (Kenya Power use cases)
- Configurable detection parameters
"""

import logging
import re
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import json
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class InteractionSegment:
    """
    Represents a detected interaction boundary within a conversation.
    
    An interaction is a complete customer service cycle from issue initiation
    to resolution, escalation, or natural conversation end.
    """
    start_message_id: int
    end_message_id: int
    start_time: datetime
    end_time: datetime
    interaction_type: Optional[str] = None  # "outage", "billing", "inquiry", etc.
    boundary_method: str = "rule_based"     # "time_gap", "resolution_keywords", "ai_detected"
    boundary_confidence: float = 1.0        # 0.0-1.0 confidence score
    topic_keywords: List[str] = None        # Detected topic keywords
    
    def __post_init__(self):
        if self.topic_keywords is None:
            self.topic_keywords = []


class InteractionDetectionConfig:
    """Configuration parameters for interaction detection."""
    
    # Time-based detection
    TIME_GAP_HOURS = 4  # Default threshold for interaction boundaries
    BUSINESS_HOURS_START = 8  # 8 AM Kenya time
    BUSINESS_HOURS_END = 18   # 6 PM Kenya time
    
    # AI fallback thresholds
    AI_FALLBACK_MESSAGE_THRESHOLD = 20  # Trigger AI when >20 messages with no rules
    AI_FALLBACK_CONFIDENCE_THRESHOLD = 0.7  # Minimum confidence for AI detection
    
    # Resolution keywords (case-insensitive)
    RESOLUTION_KEYWORDS = [
        "power restored", "thanks", "resolved", "working now", "problem solved",
        "issue fixed", "back on supply", "sorted", "restored", "fixed",
        "working", "ok now", "good now", "power back"
    ]
    
    # Escalation keywords (case-insensitive)
    ESCALATION_KEYWORDS = [
        "attention", "urgent", "again", "still", "not resolved", "escalate",
        "manager", "supervisor", "complaint", "unacceptable", "disappointed"
    ]
    
    # Topic classification keywords
    TOPIC_KEYWORDS = {
        "outage": ["power", "outage", "blackout", "no electricity", "no supply", "darkness", "lights"],
        "billing": ["bill", "payment", "account", "charges", "balance", "statement", "amount"],
        "prepaid": ["prepaid", "token", "vend", "top up", "recharge", "units"],
        "postpaid": ["postpaid", "monthly", "statement", "contract"],
        "meter": ["meter", "reading", "faulty", "replacement", "installation"],
        "technical": ["technical", "repair", "maintenance", "fault", "wiring"]
    }
    
    # Kenya Power reference number pattern
    REFERENCE_NUMBER_PATTERN = r'1\d{7}'  # Pattern: 1 + 7 digits (e.g., 13459714)
    
    # New conversation indicators
    NEW_CONVERSATION_KEYWORDS = [
        "hello", "hi", "good morning", "good afternoon", "good evening",
        "attention", "help", "assist", "support"
    ]


class InteractionService:
    """
    Service for detecting customer service interaction boundaries.
    
    Uses a multi-tiered approach:
    1. Rule-based detection (fast, cost-effective)
    2. AI-powered detection (for complex ambiguous cases)
    """
    
    def __init__(self, config: Optional[InteractionDetectionConfig] = None):
        """Initialize the interaction service with optional custom configuration."""
        self.config = config or InteractionDetectionConfig()
        
    def detect_interactions(self, messages: List[Dict[str, Any]]) -> List[InteractionSegment]:
        """
        Main entry point for interaction detection.
        
        Args:
            messages: List of message dictionaries with keys:
                     - id, social_create_time, message_content, direction
        
        Returns:
            List of InteractionSegment objects representing detected interactions
        """
        if not messages:
            return []
        
        # Sort messages by timestamp to ensure chronological order
        sorted_messages = sorted(messages, key=lambda m: m['social_create_time'])
        
        logger.info(f"Starting interaction detection for {len(sorted_messages)} messages")
        
        # Try rule-based detection first
        interactions = self._detect_rule_based_interactions(sorted_messages)
        
        # If no clear interactions found and message count is high, try AI fallback
        if (len(interactions) <= 1 and 
            len(sorted_messages) > self.config.AI_FALLBACK_MESSAGE_THRESHOLD):
            logger.info(f"Triggering AI fallback for {len(sorted_messages)} messages with {len(interactions)} rule-based interactions")
            ai_interactions = self._detect_ai_interactions(sorted_messages)
            if ai_interactions and len(ai_interactions) > len(interactions):
                interactions = ai_interactions
        
        logger.info(f"Detected {len(interactions)} interactions using {'AI' if interactions and interactions[0].boundary_method == 'ai_detected' else 'rule-based'} method")
        
        return interactions
    
    def _detect_rule_based_interactions(self, messages: List[Dict[str, Any]]) -> List[InteractionSegment]:
        """
        Detect interactions using rule-based logic with conservative approach.
        
        Strategy: Look for strong boundary signals, not every possible split.
        Primary signals:
        1. Large time gaps (>4 hours)  
        2. Customer closure followed by new issue
        3. Strong escalation signals
        """
        if not messages:
            return []
        
        # If only 1-2 messages, treat as single interaction
        if len(messages) <= 2:
            return [self._create_interaction_segment(messages, 0, len(messages) - 1, "single_interaction")]
        
        interactions = []
        current_interaction_start = 0
        
        for i in range(1, len(messages)):
            should_split = False
            split_reason = ""
            
            current_msg = messages[i]
            prev_msg = messages[i-1]
            
            # Rule 1: Major time gap (>4 hours) - BUT only if previous interaction had closure 
            # AND current message is not resolution of same issue
            time_gap = self._calculate_time_gap_hours(prev_msg['social_create_time'], 
                                                    current_msg['social_create_time'])
            if (time_gap >= self.config.TIME_GAP_HOURS and 
                self._previous_interaction_had_closure(messages[current_interaction_start:i]) and
                not self._is_customer_satisfaction_closure(current_msg)):
                should_split = True
                split_reason = "time_gap_after_closure"
                logger.debug(f"Major time gap after closure detected: {time_gap:.2f} hours between messages {i-1} and {i}")
            
            # Rule 1b: Very large time gap (>24 hours) - Always split regardless of closure
            elif time_gap >= 24.0:  # 1+ day gap always creates new interaction
                should_split = True
                split_reason = "large_time_gap"
                logger.debug(f"Very large time gap detected: {time_gap:.2f} hours between messages {i-1} and {i}")
            
            # Rule 2: Customer satisfaction closure followed by new conversation start
            elif (self._is_customer_satisfaction_closure(prev_msg) and 
                  self._is_new_conversation_start(current_msg) and
                  time_gap > 0.5):  # At least 30 minutes gap after closure
                should_split = True
                split_reason = "closure_and_new_start"
                logger.debug(f"Customer closure + new start detected between messages {i-1} and {i}")
            
            # Rule 3: Strong escalation signals (complaints about ongoing issues)
            elif (self._is_strong_escalation(current_msg, messages[current_interaction_start:i])):
                should_split = True
                split_reason = "escalation_signal"
                logger.debug(f"Strong escalation signal detected at message {i}")
            
            # Rule 4: Different complaint reference numbers
            elif self._has_reference_number_change(messages[current_interaction_start:i], current_msg):
                should_split = True
                split_reason = "reference_number_change"
                logger.debug(f"Reference number change detected at message {i}")
            
            # Create interaction segment if split condition met
            if should_split:
                interaction = self._create_interaction_segment(
                    messages[current_interaction_start:i],
                    current_interaction_start,
                    i - 1,
                    split_reason
                )
                interactions.append(interaction)
                current_interaction_start = i
        
        # Add final interaction segment
        if current_interaction_start < len(messages):
            final_interaction = self._create_interaction_segment(
                messages[current_interaction_start:],
                current_interaction_start,
                len(messages) - 1,
                "conversation_end"
            )
            interactions.append(final_interaction)
        
        return interactions
    
    def _calculate_time_gap_hours(self, time1: datetime, time2: datetime) -> float:
        """Calculate time gap in hours between two timestamps."""
        if isinstance(time1, str):
            time1 = datetime.fromisoformat(time1.replace('Z', '+00:00')).replace(tzinfo=None)
        if isinstance(time2, str):
            time2 = datetime.fromisoformat(time2.replace('Z', '+00:00')).replace(tzinfo=None)
        
        gap = abs((time2 - time1).total_seconds() / 3600.0)
        return gap
    
    def _is_resolution_closure(self, message: Dict[str, Any]) -> bool:
        """
        Check if message indicates resolution closure.
        
        Looks for resolution keywords, especially in customer messages,
        and typical closure patterns like "thanks" after resolution.
        """
        content = message['message_content'].lower()
        
        # Check for resolution keywords
        for keyword in self.config.RESOLUTION_KEYWORDS:
            if keyword in content:
                logger.debug(f"Resolution keyword '{keyword}' found in: {content[:100]}")
                return True
        
        # Special pattern: "thanks" from customer after agent response
        if (message['direction'] == 'to_company' and 
            any(word in content for word in ['thanks', 'thank you', 'appreciate'])):
            return True
        
        return False
    
    def _is_customer_satisfaction_closure(self, message: Dict[str, Any]) -> bool:
        """
        Check if message indicates customer satisfaction and issue closure.
        
        Looks for resolution confirmation + gratitude from customer.
        """
        if message['direction'] != 'to_company':
            return False
            
        content = message['message_content'].lower()
        
        # Strong closure indicators (resolution + thanks)
        resolution_terms = ['restored', 'back', 'working', 'fixed', 'resolved', 'sorted']
        gratitude_terms = ['thanks', 'thank you', 'appreciate']
        
        has_resolution = any(term in content for term in resolution_terms)
        has_gratitude = any(term in content for term in gratitude_terms)
        
        # Consider it closure if either:
        # 1. Both resolution and gratitude present
        # 2. Just gratitude (customer saying thanks)
        return has_gratitude or (has_resolution and len(content.split()) <= 6)  # Short resolution statements
    
    def _is_administrative_closure(self, message: Dict[str, Any]) -> bool:
        """
        Check if agent message provides administrative closure (reference number, etc).
        
        This indicates the complaint has been formally logged/processed.
        """
        if message['direction'] != 'to_client':
            return False
            
        content = message['message_content'].lower()
        
        # Administrative closure indicators
        administrative_terms = [
            'complaint has been logged',
            'reference number',
            'ticket number', 
            'case number',
            'logged under',
            'recorded under',
            'your complaint',
            'your report'
        ]
        
        return any(term in content for term in administrative_terms)
    
    def _is_new_conversation_start(self, message: Dict[str, Any]) -> bool:
        """
        Check if message indicates start of new conversation/issue.
        """
        if message['direction'] != 'to_company':
            return False
            
        content = message['message_content'].lower()
        
        # Greeting patterns
        greetings = ['hello', 'hi', 'good morning', 'good afternoon', 'good evening']
        if any(greeting in content for greeting in greetings):
            return True
        
        # New issue indicators
        new_issue_patterns = ['attention', 'help', 'another', 'we have', 'there is']
        if any(pattern in content for pattern in new_issue_patterns):
            return True
            
        return False
    
    def _is_strong_escalation(self, message: Dict[str, Any], previous_messages: List[Dict[str, Any]]) -> bool:
        """
        Check for strong escalation signals that warrant new interaction.
        
        More conservative than general escalation - needs clear "again"/"another" pattern
        with significant complaint history.
        """
        if message['direction'] != 'to_company':
            return False
            
        content = message['message_content'].lower()
        
        # Must have "again", "another", "still" to indicate recurring issue
        recurring_indicators = ['again', 'another', 'still no', 'same place', 'same problem']
        if not any(indicator in content for indicator in recurring_indicators):
            return False
        
        # Must have some previous message history (not just starting conversation)
        if len(previous_messages) < 2:
            return False
        
        # Strong escalation if explicit complaint language
        escalation_terms = ['attention', 'unacceptable', 'disappointed', 'fed up', 'always']
        has_escalation_language = any(term in content for term in escalation_terms)
        
        return has_escalation_language or len(previous_messages) >= 3  # Or if long conversation
    
    def _previous_interaction_had_closure(self, messages: List[Dict[str, Any]]) -> bool:
        """
        Check if the current interaction sequence had proper closure.
        
        Returns True if there's evidence of resolution/satisfaction in the messages.
        """
        if not messages:
            return False
        
        # Look for customer satisfaction closure in customer messages
        customer_messages = [msg for msg in messages if msg['direction'] == 'to_company']
        if customer_messages:
            last_customer_msg = customer_messages[-1]
            if self._is_customer_satisfaction_closure(last_customer_msg):
                return True
        
        # Look for administrative closure in agent messages (reference number provided, etc.)
        agent_messages = [msg for msg in messages if msg['direction'] == 'to_client']
        if agent_messages:
            last_agent_msg = agent_messages[-1]
            if self._is_administrative_closure(last_agent_msg):
                return True
        
        return False
    
    def _has_reference_number_change(self, previous_messages: List[Dict[str, Any]], 
                                   current_message: Dict[str, Any]) -> bool:
        """
        Check if current message introduces a new reference number,
        indicating a separate complaint/interaction.
        
        Only considers customer messages introducing new references,
        not agent responses providing reference numbers.
        """
        # Only customer messages can indicate new complaints
        if current_message['direction'] != 'to_company':
            return False
        
        # Extract reference numbers from previous messages
        previous_refs = set()
        for msg in previous_messages:
            refs = re.findall(self.config.REFERENCE_NUMBER_PATTERN, msg['message_content'])
            previous_refs.update(refs)
        
        # Check if current message has new reference number
        current_refs = set(re.findall(self.config.REFERENCE_NUMBER_PATTERN, 
                                    current_message['message_content']))
        
        # New reference number from customer indicates new interaction
        new_refs = current_refs - previous_refs
        if new_refs:
            logger.debug(f"New customer reference number(s) found: {new_refs}")
            return True
        
        return False
    
    def _has_topic_shift(self, previous_messages: List[Dict[str, Any]], 
                        current_message: Dict[str, Any]) -> bool:
        """
        Check if current message represents a significant topic shift
        from the previous interaction context.
        """
        # Get dominant topic from previous messages
        previous_topic = self._classify_topic_from_messages(previous_messages)
        
        # Get topic from current message
        current_topic = self._classify_topic(current_message['message_content'])
        
        # Topic shift detected if different and both are specific (not "unknown")
        if (previous_topic and current_topic and 
            previous_topic != current_topic and
            previous_topic != "unknown" and current_topic != "unknown"):
            logger.debug(f"Topic shift detected: {previous_topic} → {current_topic}")
            return True
        
        return False
    
    def _classify_topic(self, message_content: str) -> Optional[str]:
        """
        Classify message topic based on keyword matching.
        
        Returns the topic with the highest keyword match count.
        """
        content = message_content.lower()
        topic_scores = {}
        
        for topic, keywords in self.config.TOPIC_KEYWORDS.items():
            score = sum(1 for keyword in keywords if keyword in content)
            if score > 0:
                topic_scores[topic] = score
        
        if topic_scores:
            # Return topic with highest score
            return max(topic_scores, key=topic_scores.get)
        
        return "unknown"
    
    def _classify_topic_from_messages(self, messages: List[Dict[str, Any]]) -> Optional[str]:
        """Get dominant topic from a series of messages."""
        if not messages:
            return None
        
        topic_counts = {}
        for msg in messages:
            topic = self._classify_topic(msg['message_content'])
            if topic != "unknown":
                topic_counts[topic] = topic_counts.get(topic, 0) + 1
        
        if topic_counts:
            return max(topic_counts, key=topic_counts.get)
        
        return "unknown"
    
    def _create_interaction_segment(self, messages: List[Dict[str, Any]], 
                                  start_index: int, end_index: int, 
                                  boundary_method: str) -> InteractionSegment:
        """
        Create an InteractionSegment from a group of messages.
        """
        if not messages:
            raise ValueError("Cannot create interaction segment from empty messages")
        
        # Extract topic keywords from all messages
        topic_keywords = []
        for msg in messages:
            topic = self._classify_topic(msg['message_content'])
            if topic != "unknown":
                topic_keywords.append(topic)
        
        # Get dominant interaction type
        interaction_type = None
        if topic_keywords:
            # Most common topic becomes interaction type
            from collections import Counter
            topic_counter = Counter(topic_keywords)
            interaction_type = topic_counter.most_common(1)[0][0]
        
        return InteractionSegment(
            start_message_id=messages[0]['id'],
            end_message_id=messages[-1]['id'],
            start_time=messages[0]['social_create_time'],
            end_time=messages[-1]['social_create_time'],
            interaction_type=interaction_type,
            boundary_method=boundary_method,
            boundary_confidence=1.0,  # Rule-based detection has high confidence
            topic_keywords=list(set(topic_keywords))  # Unique topics
        )
    
    def _detect_ai_interactions(self, messages: List[Dict[str, Any]]) -> List[InteractionSegment]:
        """
        AI fallback detection for complex interaction patterns.
        
        This method will be implemented to call Gemini API for interaction
        segmentation when rule-based detection is insufficient.
        
        For now, returns empty list as placeholder.
        """
        logger.info("AI fallback detection triggered - not yet implemented")
        
        # TODO: Implement AI-based interaction detection
        # This would involve:
        # 1. Format messages for Gemini prompt
        # 2. Call Gemini API with segmentation prompt
        # 3. Parse JSON response for interaction boundaries
        # 4. Create InteractionSegment objects with boundary_method="ai_detected"
        
        return []


# Global service instance
interaction_service = InteractionService()


def get_interaction_service(config: Optional[InteractionDetectionConfig] = None) -> InteractionService:
    """Get interaction service instance with optional custom configuration."""
    if config:
        return InteractionService(config)
    return interaction_service