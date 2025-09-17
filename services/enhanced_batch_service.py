"""
Enhanced Batch Service supporting both DailyAnalysis and InteractionAnalysis batching.
Maintains backward compatibility while optimizing for interaction-based processing.
"""
import logging
from typing import List, Dict, Union
from collections import defaultdict
import json

from models import DailyAnalysis, InteractionAnalysis, Conversation
from config import settings

logger = logging.getLogger(__name__)

class EnhancedBatchService:
    """
    Enhanced batch service supporting both daily and interaction-based analysis batching.
    """
    
    def create_batches(
        self, 
        analyses: List[Union[DailyAnalysis, InteractionAnalysis]], 
        mode: str = 'auto'
    ) -> List[List[Union[DailyAnalysis, InteractionAnalysis]]]:
        """
        Create optimized batches for either daily or interaction analyses.
        
        Args:
            analyses: List of analysis objects to batch
            mode: 'daily', 'interaction', or 'auto' (detect from first item)
            
        Returns:
            List of batches, each containing analysis objects
        """
        if not analyses:
            return []
        
        # Auto-detect mode if not specified
        if mode == 'auto':
            mode = 'interaction' if isinstance(analyses[0], InteractionAnalysis) else 'daily'
        
        if mode == 'interaction':
            return self.create_interaction_batches(analyses)
        else:
            return self.create_daily_analysis_batches(analyses)
    
    def create_interaction_batches(self, interactions: List[InteractionAnalysis]) -> List[List[InteractionAnalysis]]:
        """
        Create optimized batches for InteractionAnalysis objects.
        
        Interaction batching strategy:
        1. Group by conversation to maintain context
        2. Consider interaction complexity (message count, type)
        3. Balance batch sizes for optimal processing
        """
        if not interactions:
            return []
        
        # Group interactions by conversation
        interactions_by_conv = defaultdict(list)
        for interaction in interactions:
            interactions_by_conv[interaction.conversation_id].append(interaction)
        
        # Estimate complexity for each interaction
        interaction_complexities = {}
        for interaction in interactions:
            complexity = self._estimate_interaction_complexity(interaction)
            interaction_complexities[interaction.id] = complexity
        
        # Calculate conversation complexities
        conv_complexities = {}
        for conv_id, conv_interactions in interactions_by_conv.items():
            total_complexity = sum(
                interaction_complexities[ia.id] for ia in conv_interactions
            )
            conv_complexities[conv_id] = total_complexity
        
        # Build batches keeping conversations together
        batches: List[List[InteractionAnalysis]] = []
        current_batch: List[InteractionAnalysis] = []
        current_batch_complexity = 0
        max_batch_complexity = settings.MAX_TOKENS_PER_BATCH  # Reuse existing limit
        
        # Sort conversations by complexity (process simple ones first)
        sorted_conversations = sorted(
            interactions_by_conv.items(),
            key=lambda x: conv_complexities[x[0]]
        )
        
        for conv_id, conv_interactions in sorted_conversations:
            conv_complexity = conv_complexities[conv_id]
            
            # If single conversation exceeds limit, process as oversized batch
            if conv_complexity > max_batch_complexity:
                logger.warning(
                    f"Conversation {conv_id} with complexity {conv_complexity} exceeds "
                    f"max batch complexity {max_batch_complexity}. Processing as oversized batch."
                )
                if current_batch:
                    batches.append(current_batch)
                batches.append(conv_interactions)
                current_batch = []
                current_batch_complexity = 0
                continue
            
            # Check if adding this conversation would exceed the limit
            if current_batch and (current_batch_complexity + conv_complexity > max_batch_complexity):
                # Finalize current batch
                batches.append(current_batch)
                current_batch = conv_interactions
                current_batch_complexity = conv_complexity
            else:
                # Add to current batch
                current_batch.extend(conv_interactions)
                current_batch_complexity += conv_complexity
        
        # Add final batch if exists
        if current_batch:
            batches.append(current_batch)
        
        logger.info(
            f"Created {len(batches)} interaction batches from {len(interactions)} interactions "
            f"across {len(interactions_by_conv)} conversations"
        )
        
        return batches
    
    def create_daily_analysis_batches(self, daily_analyses: List[DailyAnalysis]) -> List[List[DailyAnalysis]]:
        """
        Create batches for DailyAnalysis objects (existing functionality).
        Delegates to the existing batch service logic.
        """
        return self._create_legacy_daily_batches(daily_analyses)
    
    def _estimate_interaction_complexity(self, interaction: InteractionAnalysis) -> int:
        """
        Estimate the processing complexity of an interaction.
        
        Factors considered:
        - Message count (range between start and end message IDs)
        - Interaction type (some types are more complex to analyze)
        - Boundary detection method (AI-detected interactions are more complex)
        """
        base_complexity = 100  # Base complexity per interaction
        
        # Message count factor
        message_count = interaction.end_message_id - interaction.start_message_id + 1
        message_complexity = message_count * 50  # 50 complexity units per message
        
        # Interaction type factor
        type_multipliers = {
            'outage': 1.0,         # Standard complexity
            'billing': 1.2,        # Slightly more complex
            'technical': 1.5,      # More complex technical analysis
            'escalation': 2.0,     # High complexity for escalations
            'unknown': 1.1         # Slightly higher for unknown types
        }
        type_multiplier = type_multipliers.get(interaction.interaction_type or 'unknown', 1.0)
        
        # Detection method factor
        method_multipliers = {
            'conversation_end': 1.0,           # Simple boundary
            'time_gap_after_closure': 1.1,    # Slightly more complex
            'closure_and_new_start': 1.2,     # More complex detection
            'escalation_signal': 1.3,         # Complex escalation detection
            'ai_detected': 2.0                 # Highest complexity for AI detection
        }
        method_multiplier = method_multipliers.get(interaction.boundary_method, 1.0)
        
        # Calculate total complexity
        total_complexity = int(
            (base_complexity + message_complexity) * type_multiplier * method_multiplier
        )
        
        return total_complexity
    
    def _create_legacy_daily_batches(self, daily_analyses: List[DailyAnalysis]) -> List[List[DailyAnalysis]]:
        """
        Create batches using the existing daily analysis logic.
        """
        if not daily_analyses:
            return []

        # Group analyses by conversation (existing logic)
        analyses_by_conv = defaultdict(list)
        for analysis in daily_analyses:
            analyses_by_conv[analysis.conversation_id].append(analysis)

        # Estimate token count for each conversation (existing logic)
        conv_token_estimates = {
            conv_id: sum(self._estimate_daily_token_count(da) for da in das)
            for conv_id, das in analyses_by_conv.items()
        }

        # Build batches keeping conversations together (existing logic)
        batches: List[List[DailyAnalysis]] = []
        current_batch: List[DailyAnalysis] = []
        current_batch_tokens = 0

        for conv_id, conv_analyses in analyses_by_conv.items():
            conv_tokens = conv_token_estimates[conv_id]

            if conv_tokens > settings.MAX_TOKENS_PER_BATCH:
                logger.warning(
                    f"Conversation {conv_id} with {conv_tokens} estimated tokens exceeds "
                    f"max batch size {settings.MAX_TOKENS_PER_BATCH}. Processing as oversized batch."
                )
                if current_batch:
                    batches.append(current_batch)
                batches.append(conv_analyses)
                current_batch = []
                current_batch_tokens = 0
                continue

            if current_batch and (current_batch_tokens + conv_tokens > settings.MAX_TOKENS_PER_BATCH):
                batches.append(current_batch)
                current_batch = conv_analyses
                current_batch_tokens = conv_tokens
            else:
                current_batch.extend(conv_analyses)
                current_batch_tokens += conv_tokens

        if current_batch:
            batches.append(current_batch)

        logger.info(
            f"Created {len(batches)} daily analysis batches from {len(daily_analyses)} analyses "
            f"based on token limit {settings.MAX_TOKENS_PER_BATCH}"
        )
        
        return batches
    
    def _estimate_daily_token_count(self, analysis: DailyAnalysis) -> int:
        """
        Estimate token count for a DailyAnalysis (existing logic).
        """
        # Simplified estimation - in practice, would use the existing logic
        # from batch_service.py
        base_tokens = 200  # Base tokens for analysis structure
        
        if hasattr(analysis, 'conversation') and analysis.conversation:
            # Estimate based on message count for the day
            message_count = getattr(analysis.conversation, 'total_messages', 10)
            message_tokens = message_count * 25  # Rough estimate per message
            return base_tokens + message_tokens
        
        return base_tokens
    
    # === Utility Methods ===
    
    def get_batch_statistics(
        self, 
        batches: List[List[Union[DailyAnalysis, InteractionAnalysis]]]
    ) -> Dict[str, any]:
        """
        Calculate statistics about the created batches.
        """
        if not batches:
            return {'total_batches': 0, 'total_items': 0}
        
        # Determine batch type
        batch_type = 'interaction' if isinstance(batches[0][0], InteractionAnalysis) else 'daily'
        
        total_items = sum(len(batch) for batch in batches)
        batch_sizes = [len(batch) for batch in batches]
        
        # Get conversation distribution
        conversations = set()
        for batch in batches:
            for item in batch:
                conversations.add(item.conversation_id)
        
        stats = {
            'batch_type': batch_type,
            'total_batches': len(batches),
            'total_items': total_items,
            'unique_conversations': len(conversations),
            'avg_batch_size': sum(batch_sizes) / len(batch_sizes),
            'min_batch_size': min(batch_sizes),
            'max_batch_size': max(batch_sizes),
            'items_per_conversation': total_items / len(conversations) if conversations else 0
        }
        
        return stats

# Create service instance
enhanced_batch_service = EnhancedBatchService()

# Backward compatibility functions
def create_daily_analysis_batches(daily_analyses: List[DailyAnalysis]) -> List[List[DailyAnalysis]]:
    """Legacy function for backward compatibility."""
    return enhanced_batch_service.create_daily_analysis_batches(daily_analyses)

def estimate_token_count(analysis: DailyAnalysis) -> int:
    """Legacy function for backward compatibility.""" 
    return enhanced_batch_service._estimate_daily_token_count(analysis)