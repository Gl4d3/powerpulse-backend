"""
Interaction Detection Service

This service implements hybrid interaction boundary detection for customer service conversations:
1. Rule-based detection using time gaps and utility-specific keywords
2. AI fallback for complex cases where rules are insufficient
3. Configurable parameters for different conversation patterns

The goal is to identify natural interaction boundaries within conversations,
enabling more granular CSI analysis compared to daily aggregation.

"""

import logging
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import re

from models import Message, Conversation
from services.gemini_service import GeminiService
from config import settings

logger = logging.getLogger(__name__)


class DetectionMethod(Enum):
    """Method used to detect interaction boundary."""
    TIME_GAP = "time_gap"
    KEYWORD_PATTERN = "keyword_pattern"
    AI_FALLBACK = "ai_fallback"
    CONVERSATION_START = "conversation_start"
    CONVERSATION_END = "conversation_end"


@dataclass
class InteractionBoundary:
    """Represents a detected interaction boundary."""
    message_index: int
    timestamp: datetime
    method: DetectionMethod
    confidence: float
    reason: str
    

@dataclass 
class DetectedInteraction:
    """Represents a detected customer service interaction."""
    start_message_index: int
    end_message_index: int
    start_time: datetime
    end_time: datetime
    messages: List[Message]
    detection_methods: List[DetectionMethod]
    confidence: float
    interaction_id: str


class InteractionDetectionService:
    """
    Hybrid service for detecting interaction boundaries in customer conversations.
    
    Detection Strategy:
    1. Time Gap Detection: >4 hour gaps indicate new interactions
    2. Keyword Pattern Detection: Resolution/closure keywords + customer acknowledgment
    3. AI Fallback: Complex cases where rules are insufficient
    """
    
    def __init__(self, gemini_service: Optional[GeminiService] = None):
        self.gemini_service = gemini_service or GeminiService(settings.GEMINI_API_KEY)
        
        # Configurable parameters
        self.config = {
            'time_gap_threshold_hours': 4.0,
            'min_interaction_messages': 1,  # Allow single-message interactions
            'max_interaction_duration_hours': 24.0,
            'keyword_confidence_threshold': 0.3,  # Lower threshold for testing
            'ai_fallback_enabled': True,
            'ai_fallback_threshold': 0.6,
            'ai_enhancement_enabled': True,  # Enable AI boundary enhancement
            'ai_enhancement_confidence_threshold': 0.7  # Minimum confidence for AI suggestions
        }
        
        # Utility-specific resolution patterns
        self.resolution_patterns = self._compile_resolution_patterns()
        self.acknowledgment_patterns = self._compile_acknowledgment_patterns()
    
    def _compile_resolution_patterns(self) -> List[re.Pattern]:
        """Compile regex patterns for resolution indicators."""
        patterns = [
            # Power restoration
            r'power\s+(has\s+been\s+)?(restored|back|returned)',
            r'electricity\s+(is\s+)?(back|restored|working)',
            r'(issue|problem|outage)\s+(has\s+been\s+)?(resolved|fixed|cleared)',
            
            # Billing resolution  
            r'bill\s+(has\s+been\s+)?(corrected|adjusted|updated)',
            r'payment\s+(has\s+been\s+)?(processed|received|confirmed)',
            r'account\s+(has\s+been\s+)?(updated|corrected)',
            
            # Service completion
            r'(technician|team)\s+will\s+(visit|arrive|come)',
            r'(work|repair|maintenance)\s+(is\s+)?(complete|completed|finished)',
            r'(token|units)\s+(sent|delivered|dispatched)',
            
            # Case closure
            r'(case|ticket|complaint)\s+(has\s+been\s+)?(closed|resolved|completed)',
            r'(matter|issue)\s+(has\s+been\s+)?(attended\s+to|handled|resolved)'
        ]
        
        return [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
    
    def _compile_acknowledgment_patterns(self) -> List[re.Pattern]:
        """Compile regex patterns for customer acknowledgment."""
        patterns = [
            r'^(thank\s+you|thanks|appreciate)',
            r'^(ok|okay|alright|good)',
            r'^(yes|yeah|confirmed|received)',
            r'(problem\s+solved|issue\s+resolved|working\s+now)',
            r'(satisfied|happy)\s+with',
            r'no\s+(more|other|further)\s+(issues|problems|questions)'
        ]
        
        return [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
    
    async def detect_interactions(self, conversation: Conversation) -> List[DetectedInteraction]:
        """
        Detect all interactions within a conversation using hybrid approach.
        
        Args:
            conversation: The conversation to analyze
            
        Returns:
            List of detected interactions with boundary information
        """
        if not conversation.messages:
            logger.warning(f"No messages found for conversation {conversation.id}")
            return []
        
        # Sort messages by timestamp
        messages = sorted(conversation.messages, key=lambda m: m.social_create_time)
        logger.info(f"Analyzing {len(messages)} messages for interaction boundaries")
        
        # Step 1: Detect boundaries using rules
        rule_boundaries = await self._detect_rule_based_boundaries(messages)
        
        # Step 2: AI enhancement of rule-based boundaries (NEW)
        if self.config['ai_enhancement_enabled'] and self.gemini_service:
            enhanced_boundaries = await self._apply_ai_enhancements(conversation, rule_boundaries)
        else:
            enhanced_boundaries = rule_boundaries
        
        # Step 3: AI fallback for remaining ambiguous cases
        if self.config['ai_fallback_enabled']:
            ai_boundaries = await self._detect_ai_boundaries(messages, enhanced_boundaries)
            enhanced_boundaries.extend(ai_boundaries)
        
        # Step 4: Convert boundaries to interactions
        interactions = self._boundaries_to_interactions(messages, enhanced_boundaries, conversation)
        
        logger.info(f"Detected {len(interactions)} interactions using {len(enhanced_boundaries)} boundaries")
        return interactions
    
    async def detect_interactions_batch(self, conversations: List[Conversation]) -> Dict[int, List[DetectedInteraction]]:
        """
        Batch detection of interactions across multiple conversations.
        Uses batch AI enhancement for cost efficiency and rate limit compliance.
        
        Args:
            conversations: List of conversations to analyze
            
        Returns:
            Dictionary mapping conversation.id to list of detected interactions
        """
        if not conversations:
            logger.info("No conversations to process in batch")
            return {}
        
        logger.info(f"Starting batch interaction detection for {len(conversations)} conversations")
        
        # Step 1: Detect rule-based boundaries for all conversations
        conversations_with_boundaries = []
        for conversation in conversations:
            if not conversation.messages:
                logger.warning(f"Skipping conversation {conversation.id} - no messages")
                continue
                
            messages = sorted(conversation.messages, key=lambda m: m.social_create_time)
            rule_boundaries = await self._detect_rule_based_boundaries(messages)
            conversations_with_boundaries.append((conversation, rule_boundaries))
        
        # Step 2: Batch AI enhancement (NEW - single API call for all conversations)
        batch_enhancements = {}
        if self.config['ai_enhancement_enabled'] and self.gemini_service and conversations_with_boundaries:
            logger.info(f"Applying batch AI enhancement to {len(conversations_with_boundaries)} conversations")
            batch_enhancements = await self.gemini_service.enhance_interaction_boundaries_batch(conversations_with_boundaries)
        
        # Step 3: Process each conversation with its enhancements
        results = {}
        for conversation, rule_boundaries in conversations_with_boundaries:
            try:
                # Apply AI enhancements for this conversation
                enhancements = batch_enhancements.get(conversation.id, [])
                if enhancements:
                    enhanced_boundaries = self._merge_ai_enhancements(rule_boundaries, enhancements)
                else:
                    enhanced_boundaries = rule_boundaries
                
                # AI fallback for remaining ambiguous cases (individual per conversation)
                if self.config['ai_fallback_enabled']:
                    messages = sorted(conversation.messages, key=lambda m: m.social_create_time)
                    ai_boundaries = await self._detect_ai_boundaries(messages, enhanced_boundaries)
                    enhanced_boundaries.extend(ai_boundaries)
                
                # Convert boundaries to interactions
                interactions = self._boundaries_to_interactions(
                    sorted(conversation.messages, key=lambda m: m.social_create_time), 
                    enhanced_boundaries, 
                    conversation
                )
                
                results[conversation.id] = interactions
                logger.info(f"Conversation {conversation.id}: {len(interactions)} interactions detected")
                
            except Exception as e:
                logger.error(f"Error processing conversation {conversation.id}: {e}")
                results[conversation.id] = []
        
        logger.info(f"Batch detection completed: {len(results)} conversations processed")
        return results
    
    async def _detect_rule_based_boundaries(self, messages: List[Message]) -> List[InteractionBoundary]:
        """Detect interaction boundaries using time gaps and keyword patterns."""
        boundaries = []
        
        # Always start with conversation beginning
        if messages:
            boundaries.append(InteractionBoundary(
                message_index=0,
                timestamp=messages[0].social_create_time,
                method=DetectionMethod.CONVERSATION_START,
                confidence=1.0,
                reason="Conversation start"
            ))
        
        # Time gap detection
        time_boundaries = self._detect_time_gaps(messages)
        boundaries.extend(time_boundaries)
        
        # Keyword pattern detection
        keyword_boundaries = self._detect_keyword_patterns(messages)
        boundaries.extend(keyword_boundaries)
        
        # Always end with conversation end
        if messages:
            boundaries.append(InteractionBoundary(
                message_index=len(messages) - 1,
                timestamp=messages[-1].social_create_time,
                method=DetectionMethod.CONVERSATION_END,
                confidence=1.0,
                reason="Conversation end"
            ))
        
        return sorted(boundaries, key=lambda b: b.message_index)
    
    def _detect_time_gaps(self, messages: List[Message]) -> List[InteractionBoundary]:
        """Detect boundaries based on time gaps between messages."""
        boundaries = []
        threshold = timedelta(hours=self.config['time_gap_threshold_hours'])
        
        for i in range(1, len(messages)):
            prev_msg = messages[i-1]
            curr_msg = messages[i]
            
            time_gap = curr_msg.social_create_time - prev_msg.social_create_time
            
            if time_gap > threshold:
                boundaries.append(InteractionBoundary(
                    message_index=i,
                    timestamp=curr_msg.social_create_time,
                    method=DetectionMethod.TIME_GAP,
                    confidence=min(1.0, time_gap.total_seconds() / (threshold.total_seconds() * 2)),
                    reason=f"Time gap of {time_gap} > {self.config['time_gap_threshold_hours']}h threshold"
                ))
        
        return boundaries
    
    def _detect_keyword_patterns(self, messages: List[Message]) -> List[InteractionBoundary]:
        """Detect boundaries based on resolution + acknowledgment patterns."""
        boundaries = []
        
        for i in range(len(messages) - 1):
            current_msg = messages[i]
            next_msg = messages[i + 1] if i + 1 < len(messages) else None
            
            # Look for agent resolution followed by customer acknowledgment
            if (current_msg.direction == 'to_client' and 
                next_msg and next_msg.direction == 'to_company'):
                
                resolution_score = self._calculate_resolution_score(current_msg.message_content)
                acknowledgment_score = self._calculate_acknowledgment_score(next_msg.message_content)
                
                # Combined confidence score
                combined_confidence = (resolution_score + acknowledgment_score) / 2
                
                logger.debug(f"Keyword check at msg {i}: resolution={resolution_score:.2f}, ack={acknowledgment_score:.2f}, combined={combined_confidence:.2f}")
                
                if combined_confidence >= self.config['keyword_confidence_threshold']:
                    # Boundary is after the acknowledgment message
                    boundary_index = i + 2 if i + 2 < len(messages) else len(messages)
                    
                    boundaries.append(InteractionBoundary(
                        message_index=boundary_index,
                        timestamp=next_msg.social_create_time,
                        method=DetectionMethod.KEYWORD_PATTERN,
                        confidence=combined_confidence,
                        reason=f"Resolution pattern (conf: {resolution_score:.2f}) + acknowledgment (conf: {acknowledgment_score:.2f})"
                    ))
        
        return boundaries
    
    def _calculate_resolution_score(self, text: str) -> float:
        """Calculate confidence that message contains resolution indicator."""
        if not text:
            return 0.0
        
        matches = 0
        total_patterns = len(self.resolution_patterns)
        
        for pattern in self.resolution_patterns:
            if pattern.search(text):
                matches += 1
        
        # Give higher weight to any match since resolution language is strong signal
        return min(1.0, matches * 0.8) if matches > 0 else 0.0
    
    def _calculate_acknowledgment_score(self, text: str) -> float:
        """Calculate confidence that message contains acknowledgment."""
        if not text:
            return 0.0
        
        matches = 0
        total_patterns = len(self.acknowledgment_patterns)
        
        for pattern in self.acknowledgment_patterns:
            if pattern.search(text):
                matches += 1
        
        # Give higher weight to any match since acknowledgment language is strong signal
        return min(1.0, matches * 0.8) if matches > 0 else 0.0
    
    async def _detect_ai_boundaries(self, messages: List[Message], existing_boundaries: List[InteractionBoundary]) -> List[InteractionBoundary]:
        """Use AI to detect boundaries in ambiguous cases."""
        if not self.gemini_service:
            return []
        
        # Identify gaps where AI analysis might help
        # For now, implement a simple version - can be enhanced later
        potential_boundaries = []
        
        # Look for message sequences that might be missed by rules
        for i in range(1, len(messages) - 1):
            # Check if this area is already covered by existing boundaries
            covered = any(
                abs(b.message_index - i) <= 2 
                for b in existing_boundaries
            )
            
            if not covered:
                # Analyze context around this message for interaction boundary
                context_start = max(0, i - 3)
                context_end = min(len(messages), i + 4)
                context_messages = messages[context_start:context_end]
                
                # Simple heuristic: if there's a topic shift, consider AI analysis
                if self._has_potential_topic_shift(context_messages, i - context_start):
                    ai_confidence = await self._analyze_boundary_with_ai(context_messages, i - context_start)
                    
                    if ai_confidence >= self.config['ai_fallback_threshold']:
                        potential_boundaries.append(InteractionBoundary(
                            message_index=i,
                            timestamp=messages[i].social_create_time,
                            method=DetectionMethod.AI_FALLBACK,
                            confidence=ai_confidence,
                            reason=f"AI detected topic/interaction boundary (conf: {ai_confidence:.2f})"
                        ))
        
        return potential_boundaries
    
    async def _apply_ai_enhancements(self, conversation: Conversation, rule_boundaries: List[InteractionBoundary]) -> List[InteractionBoundary]:
        """
        Apply AI enhancements to rule-based boundaries.
        
        Args:
            conversation: The conversation being analyzed
            rule_boundaries: List of boundaries detected by rules
            
        Returns:
            Enhanced list of boundaries with AI suggestions applied
        """
        try:
            logger.info(f"Requesting AI enhancement for {len(rule_boundaries)} rule-based boundaries")
            
            # Get AI enhancement suggestions
            enhancements = await self.gemini_service.enhance_interaction_boundaries(conversation, rule_boundaries)
            
            if not enhancements:
                logger.info("No AI enhancement suggestions received, using rule-based boundaries")
                return rule_boundaries
            
            # Apply AI enhancements
            enhanced_boundaries = self._merge_ai_enhancements(rule_boundaries, enhancements)
            
            logger.info(f"Applied {len(enhancements)} AI suggestions, resulting in {len(enhanced_boundaries)} boundaries")
            return enhanced_boundaries
            
        except Exception as e:
            logger.error(f"AI enhancement failed: {e}")
            logger.info("Falling back to rule-based boundaries")
            return rule_boundaries
    
    def _merge_ai_enhancements(self, rule_boundaries: List[InteractionBoundary], enhancements: List[Dict[str, Any]]) -> List[InteractionBoundary]:
        """
        Merge AI enhancement suggestions with rule-based boundaries.
        
        Args:
            rule_boundaries: Original rule-based boundaries
            enhancements: AI suggestions for boundary modifications
            
        Returns:
            Enhanced boundary list
        """
        # Start with copy of rule boundaries
        enhanced_boundaries = rule_boundaries.copy()
        
        # Apply AI suggestions in order of confidence (highest first)
        sorted_enhancements = sorted(enhancements, key=lambda x: x.get('confidence', 0), reverse=True)
        
        for enhancement in sorted_enhancements:
            confidence = enhancement.get('confidence', 0)
            
            # Only apply high-confidence suggestions
            if confidence < self.config['ai_enhancement_confidence_threshold']:
                logger.debug(f"Skipping low-confidence AI suggestion: {confidence:.2f}")
                continue
            
            action = enhancement['action']
            reason = enhancement.get('reason', 'AI suggestion')
            
            try:
                if action == 'add_boundary':
                    self._apply_add_boundary(enhanced_boundaries, enhancement)
                elif action == 'remove_boundary':
                    self._apply_remove_boundary(enhanced_boundaries, enhancement)
                elif action == 'merge_interactions':
                    self._apply_merge_interactions(enhanced_boundaries, enhancement)
                
                logger.info(f"Applied AI {action}: {reason} (conf: {confidence:.2f})")
                
            except Exception as e:
                logger.warning(f"Failed to apply AI enhancement {action}: {e}")
        
        # Sort by message index and return
        return sorted(enhanced_boundaries, key=lambda b: b.message_index)
    
    def _apply_add_boundary(self, boundaries: List[InteractionBoundary], enhancement: Dict[str, Any]):
        """Apply AI suggestion to add a new boundary."""
        message_index = enhancement['after_message_index']
        reason = enhancement.get('reason', 'AI suggested boundary')
        confidence = enhancement.get('confidence', 0.8)
        
        # Create new boundary
        new_boundary = InteractionBoundary(
            message_index=message_index + 1,  # After the specified message
            timestamp=None,  # Will be set when converting to interactions
            method=DetectionMethod.AI_FALLBACK,
            confidence=confidence,
            reason=f"AI Enhancement: {reason}"
        )
        
        # Insert in correct position
        boundaries.append(new_boundary)
    
    def _apply_remove_boundary(self, boundaries: List[InteractionBoundary], enhancement: Dict[str, Any]):
        """Apply AI suggestion to remove a boundary."""
        boundary_index = enhancement['boundary_index']
        
        # Find and remove boundary (skip conversation start/end)
        boundaries_to_remove = []
        for i, boundary in enumerate(boundaries):
            if (i == boundary_index and 
                boundary.method not in [DetectionMethod.CONVERSATION_START, DetectionMethod.CONVERSATION_END]):
                boundaries_to_remove.append(boundary)
                break
        
        for boundary in boundaries_to_remove:
            boundaries.remove(boundary)
    
    def _apply_merge_interactions(self, boundaries: List[InteractionBoundary], enhancement: Dict[str, Any]):
        """Apply AI suggestion to merge interactions by removing intermediate boundaries."""
        boundary_indices = enhancement.get('boundary_indices', [])
        
        # Remove boundaries between interactions to merge them
        boundaries_to_remove = []
        for i, boundary_idx in enumerate(boundary_indices[:-1]):  # All but last
            next_idx = boundary_indices[i + 1]
            
            # Find boundaries between these indices and mark for removal
            for boundary in boundaries:
                if (boundary_idx < boundaries.index(boundary) < next_idx and
                    boundary.method not in [DetectionMethod.CONVERSATION_START, DetectionMethod.CONVERSATION_END]):
                    boundaries_to_remove.append(boundary)
        
        for boundary in boundaries_to_remove:
            if boundary in boundaries:
                boundaries.remove(boundary)
    
    def _has_potential_topic_shift(self, messages: List[Message], focus_index: int) -> bool:
        """Quick heuristic to identify potential topic shifts for AI analysis."""
        if focus_index <= 0 or focus_index >= len(messages) - 1:
            return False
        
        # Simple keyword-based topic shift detection
        utility_topics = ['power', 'electricity', 'bill', 'payment', 'meter', 'token', 'outage']
        
        before_msg = messages[focus_index - 1].message_content.lower()
        after_msg = messages[focus_index + 1].message_content.lower()
        
        before_topics = set(topic for topic in utility_topics if topic in before_msg)
        after_topics = set(topic for topic in utility_topics if topic in after_msg)
        
        # If topics change significantly, consider AI analysis
        topic_overlap = len(before_topics & after_topics) / max(len(before_topics | after_topics), 1)
        
        return topic_overlap < 0.5  # Less than 50% topic overlap
    
    async def _analyze_boundary_with_ai(self, context_messages: List[Message], focus_index: int) -> float:
        """Use AI to analyze if there's an interaction boundary at focus_index."""
        # Simplified AI boundary detection - can be enhanced with specific prompts
        try:
            # Format messages for AI analysis
            context_text = []
            for i, msg in enumerate(context_messages):
                marker = " <-- BOUNDARY?" if i == focus_index else ""
                direction = "Customer" if msg.direction == 'to_company' else "Agent"
                context_text.append(f"[{msg.social_create_time}] {direction}: {msg.message_content}{marker}")
            
            formatted_context = "\n".join(context_text)
            
            # Simple prompt for boundary detection
            prompt = f"""
Analyze this customer service conversation context and determine if there's a natural interaction boundary at the marked location.

Context:
{formatted_context}

Consider:
- Topic changes
- Problem resolution followed by new issues
- Natural conversation flow breaks
- Customer satisfaction closure

Return a confidence score between 0.0 and 1.0 for boundary likelihood:
- 0.0-0.3: No boundary 
- 0.4-0.6: Possible boundary
- 0.7-1.0: Strong boundary

Response format: {{"boundary_confidence": 0.X, "reasoning": "brief explanation"}}
"""

            # This would call Gemini - for now return moderate confidence
            # In full implementation, would use self.gemini_service
            return 0.5  # Placeholder - implement full AI call
            
        except Exception as e:
            logger.warning(f"AI boundary detection failed: {e}")
            return 0.0
    
    def _boundaries_to_interactions(self, messages: List[Message], boundaries: List[InteractionBoundary], conversation: Conversation) -> List[DetectedInteraction]:
        """Convert detected boundaries into interaction objects."""
        if len(boundaries) < 2:
            # Single interaction covering entire conversation
            if messages:  # Make sure we have messages
                return [DetectedInteraction(
                    start_message_index=0,
                    end_message_index=len(messages) - 1,
                    start_time=messages[0].social_create_time,
                    end_time=messages[-1].social_create_time,
                    messages=messages,
                    detection_methods=[DetectionMethod.CONVERSATION_START],
                    confidence=1.0,
                    interaction_id=f"{conversation.fb_chat_id}_interaction_1"
                )]
            else:
                return []
        
        interactions = []
        sorted_boundaries = sorted(boundaries, key=lambda b: b.message_index)
        
        for i in range(len(sorted_boundaries) - 1):
            start_boundary = sorted_boundaries[i]
            end_boundary = sorted_boundaries[i + 1]
            
            start_idx = start_boundary.message_index
            # End at the message before the next boundary (not inclusive of boundary message)
            end_idx = end_boundary.message_index - 1 if end_boundary.method != DetectionMethod.CONVERSATION_END else end_boundary.message_index
            end_idx = max(start_idx, min(end_idx, len(messages) - 1))  # Ensure valid range
            
            # Skip too-small interactions
            if end_idx - start_idx + 1 < self.config['min_interaction_messages']:
                logger.debug(f"Skipping small interaction: {end_idx - start_idx + 1} messages < {self.config['min_interaction_messages']}")
                continue
            
            interaction_messages = messages[start_idx:end_idx + 1]
            detection_methods = [start_boundary.method, end_boundary.method]
            avg_confidence = (start_boundary.confidence + end_boundary.confidence) / 2
            
            interactions.append(DetectedInteraction(
                start_message_index=start_idx,
                end_message_index=end_idx,
                start_time=messages[start_idx].social_create_time,
                end_time=messages[end_idx].social_create_time,
                messages=interaction_messages,
                detection_methods=detection_methods,
                confidence=avg_confidence,
                interaction_id=f"{conversation.fb_chat_id}_interaction_{len(interactions) + 1}"
            ))
        
        logger.info(f"Created {len(interactions)} interactions from {len(boundaries)} boundaries")
        return interactions
    
    def update_config(self, config_updates: Dict[str, Any]) -> None:
        """Update detection configuration parameters."""
        for key, value in config_updates.items():
            if key in self.config:
                self.config[key] = value
                logger.info(f"Updated config: {key} = {value}")
            else:
                logger.warning(f"Unknown config key: {key}")
    
    def get_detection_stats(self, interactions: List[DetectedInteraction]) -> Dict[str, Any]:
        """Generate statistics about detection results."""
        if not interactions:
            return {"total_interactions": 0}
        
        method_counts = {}
        confidence_scores = []
        
        for interaction in interactions:
            confidence_scores.append(interaction.confidence)
            for method in interaction.detection_methods:
                method_counts[method.value] = method_counts.get(method.value, 0) + 1
        
        return {
            "total_interactions": len(interactions),
            "avg_confidence": sum(confidence_scores) / len(confidence_scores),
            "min_confidence": min(confidence_scores),
            "max_confidence": max(confidence_scores),
            "detection_methods": method_counts,
            "avg_messages_per_interaction": sum(len(i.messages) for i in interactions) / len(interactions)
        }