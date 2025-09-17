"""
Interaction Detection Test Utility

This utility tests the InteractionDetectionService with various scenarios:
1. Real database conversations 
2. Synthetic test cases with known patterns
3. Edge cases and boundary conditions

Author: GitHub Copilot
Date: September 17, 2025
"""

import asyncio
import logging
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Add project root to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from services.interaction_detection_service import InteractionDetectionService, DetectedInteraction
from models import Conversation, Message
from database import SessionLocal
from config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class InteractionDetectionTester:
    """Test suite for interaction detection service."""
    
    def __init__(self):
        self.detection_service = InteractionDetectionService()
        self.test_results = {
            'time_gap_detection': False,
            'keyword_pattern_detection': False,
            'real_conversation_analysis': False,
            'edge_cases_handled': False,
            'errors': [],
            'sample_results': []
        }
    
    async def run_comprehensive_test(self):
        """Run all interaction detection tests."""
        logger.info("=== Starting Interaction Detection Test Suite ===")
        
        # Test 1: Time gap detection
        await self._test_time_gap_detection()
        
        # Test 2: Keyword pattern detection  
        await self._test_keyword_pattern_detection()
        
        # Test 3: Real conversation analysis
        await self._test_real_conversation_analysis()
        
        # Test 4: Edge cases
        await self._test_edge_cases()
        
        # Generate report
        self._generate_test_report()
        
        return self.test_results
    
    async def _test_time_gap_detection(self):
        """Test detection based on time gaps."""
        logger.info("Test 1: Time Gap Detection")
        
        try:
            # Create synthetic conversation with clear time gaps
            conversation = self._create_time_gap_test_conversation()
            
            interactions = await self.detection_service.detect_interactions(conversation)
            
            # Should detect interactions based on time gaps and any keywords
            # Could be 3 (pure time gaps) or more (time gaps + keywords)  
            if len(interactions) >= 3:
                logger.info(f"✅ Time gap detection successful: {len(interactions)} interactions detected")
                self.test_results['time_gap_detection'] = True
                
                # Validate interaction boundaries
                for i, interaction in enumerate(interactions):
                    logger.info(f"   Interaction {i+1}: {len(interaction.messages)} messages, methods: {[m.value for m in interaction.detection_methods]}")
                    
            else:
                logger.warning(f"⚠️  Expected at least 3 interactions, got {len(interactions)}")
            
        except Exception as e:
            error_msg = f"❌ Time gap detection failed: {str(e)}"
            logger.error(error_msg)
            self.test_results['errors'].append(error_msg)
    
    async def _test_keyword_pattern_detection(self):
        """Test detection based on resolution patterns."""
        logger.info("Test 2: Keyword Pattern Detection")
        
        try:
            # Create synthetic conversation with resolution patterns
            conversation = self._create_keyword_pattern_test_conversation()
            
            interactions = await self.detection_service.detect_interactions(conversation)
            
            # Check if keyword patterns were detected
            keyword_detected = any(
                'keyword_pattern' in [method.value for method in interaction.detection_methods]
                for interaction in interactions
            )
            
            if keyword_detected:
                logger.info("✅ Keyword pattern detection successful")
                self.test_results['keyword_pattern_detection'] = True
                
                for interaction in interactions:
                    if 'keyword_pattern' in [method.value for method in interaction.detection_methods]:
                        logger.info(f"   Found keyword-based interaction: {len(interaction.messages)} messages")
            else:
                logger.warning("⚠️  No keyword patterns detected")
                
        except Exception as e:
            error_msg = f"❌ Keyword pattern detection failed: {str(e)}"
            logger.error(error_msg)
            self.test_results['errors'].append(error_msg)
    
    async def _test_real_conversation_analysis(self):
        """Test with real database conversation."""
        logger.info("Test 3: Real Conversation Analysis")
        
        try:
            db = SessionLocal()
            try:
                # Get a conversation with multiple messages
                conversation = (
                    db.query(Conversation)
                    .filter(Conversation.total_messages >= 5)
                    .first()
                )
                
                if not conversation:
                    logger.warning("No suitable conversation found in database")
                    return
                
                logger.info(f"Analyzing conversation ID {conversation.id} with {conversation.total_messages} messages")
                
                interactions = await self.detection_service.detect_interactions(conversation)
                
                if interactions:
                    logger.info(f"✅ Real conversation analysis successful: {len(interactions)} interactions")
                    self.test_results['real_conversation_analysis'] = True
                    
                    # Store sample results
                    self.test_results['sample_results'].append({
                        'conversation_id': conversation.id,
                        'total_messages': conversation.total_messages,
                        'interactions_detected': len(interactions),
                        'detection_stats': self.detection_service.get_detection_stats(interactions)
                    })
                    
                    # Log interaction details
                    for i, interaction in enumerate(interactions):
                        duration = interaction.end_time - interaction.start_time
                        logger.info(f"   Interaction {i+1}: {len(interaction.messages)} msgs, {duration}, conf: {interaction.confidence:.2f}")
                        
                else:
                    logger.warning("No interactions detected in real conversation")
                    
            finally:
                db.close()
                
        except Exception as e:
            error_msg = f"❌ Real conversation analysis failed: {str(e)}"
            logger.error(error_msg)
            self.test_results['errors'].append(error_msg)
    
    async def _test_edge_cases(self):
        """Test edge cases and boundary conditions."""
        logger.info("Test 4: Edge Cases")
        
        try:
            edge_cases_passed = 0
            total_edge_cases = 3
            
            # Edge Case 1: Single message conversation
            single_msg_conv = self._create_single_message_conversation()
            interactions = await self.detection_service.detect_interactions(single_msg_conv)
            if len(interactions) == 1:
                logger.info("✅ Single message conversation handled")
                edge_cases_passed += 1
            
            # Edge Case 2: Empty conversation  
            empty_conv = Conversation(fb_chat_id="empty_test", messages=[])
            interactions = await self.detection_service.detect_interactions(empty_conv)
            if len(interactions) == 0:
                logger.info("✅ Empty conversation handled")
                edge_cases_passed += 1
            
            # Edge Case 3: Very long interaction (no boundaries)
            long_conv = self._create_long_continuous_conversation()
            interactions = await self.detection_service.detect_interactions(long_conv)
            if len(interactions) == 1:  # Should be one long interaction
                logger.info("✅ Long continuous conversation handled")
                edge_cases_passed += 1
            
            if edge_cases_passed == total_edge_cases:
                self.test_results['edge_cases_handled'] = True
                logger.info(f"✅ All {total_edge_cases} edge cases passed")
            else:
                logger.warning(f"⚠️  {edge_cases_passed}/{total_edge_cases} edge cases passed")
                
        except Exception as e:
            error_msg = f"❌ Edge case testing failed: {str(e)}"
            logger.error(error_msg)
            self.test_results['errors'].append(error_msg)
    
    def _create_time_gap_test_conversation(self) -> Conversation:
        """Create test conversation with clear time gaps."""
        base_time = datetime(2025, 9, 17, 9, 0, 0)
        
        messages = [
            # Interaction 1: Initial issue (9:00-9:30)
            Message(
                message_content="Hello, we have a power outage in Kinoo area",
                direction="to_company",
                social_create_time=base_time,
                conversation_id=1
            ),
            Message(
                message_content="We've received your report. Our team is investigating.",
                direction="to_client", 
                social_create_time=base_time + timedelta(minutes=15),
                conversation_id=1
            ),
            Message(
                message_content="Thank you",
                direction="to_company",
                social_create_time=base_time + timedelta(minutes=30),
                conversation_id=1
            ),
            
            # 5 hour gap - should trigger new interaction
            
            # Interaction 2: Follow-up (14:30-15:00)
            Message(
                message_content="Any updates on the power outage?",
                direction="to_company",
                social_create_time=base_time + timedelta(hours=5, minutes=30),
                conversation_id=1
            ),
            Message(
                message_content="Power has been restored in your area",
                direction="to_client",
                social_create_time=base_time + timedelta(hours=5, minutes=45),
                conversation_id=1
            ),
            
            # 6 hour gap - should trigger new interaction
            
            # Interaction 3: New issue (21:00)
            Message(
                message_content="Now my meter is not working properly",
                direction="to_company", 
                social_create_time=base_time + timedelta(hours=12),
                conversation_id=1
            )
        ]
        
        conversation = Conversation(
            fb_chat_id="time_gap_test",
            total_messages=len(messages),
            messages=messages
        )
        
        return conversation
    
    def _create_keyword_pattern_test_conversation(self) -> Conversation:
        """Create test conversation with resolution keywords."""
        base_time = datetime(2025, 9, 17, 10, 0, 0)
        
        messages = [
            Message(
                message_content="My electricity bill seems incorrect",
                direction="to_company",
                social_create_time=base_time,
                conversation_id=1
            ),
            Message(
                message_content="Let me check your account. I can see the issue.",
                direction="to_client",
                social_create_time=base_time + timedelta(minutes=5),
                conversation_id=1
            ),
            Message(
                message_content="Your bill has been corrected and the account updated",  # Resolution pattern
                direction="to_client",
                social_create_time=base_time + timedelta(minutes=10),
                conversation_id=1
            ),
            Message(
                message_content="Thank you so much! That's perfect.",  # Acknowledgment pattern
                direction="to_company",
                social_create_time=base_time + timedelta(minutes=12),
                conversation_id=1
            ),
            # New issue starts - should be detected as boundary
            Message(
                message_content="I also have another question about prepaid tokens",
                direction="to_company",
                social_create_time=base_time + timedelta(minutes=15),
                conversation_id=1
            ),
            Message(
                message_content="Sure, how can I help with your prepaid account?",
                direction="to_client",
                social_create_time=base_time + timedelta(minutes=16),
                conversation_id=1
            )
        ]
        
        conversation = Conversation(
            fb_chat_id="keyword_pattern_test",
            total_messages=len(messages),
            messages=messages
        )
        
        return conversation
    
    def _create_single_message_conversation(self) -> Conversation:
        """Create conversation with single message."""
        messages = [
            Message(
                message_content="Test single message",
                direction="to_company",
                social_create_time=datetime(2025, 9, 17, 10, 0, 0),
                conversation_id=1
            )
        ]
        
        return Conversation(
            fb_chat_id="single_msg_test",
            total_messages=1,
            messages=messages
        )
    
    def _create_long_continuous_conversation(self) -> Conversation:
        """Create long conversation without clear boundaries."""
        base_time = datetime(2025, 9, 17, 10, 0, 0)
        messages = []
        
        for i in range(10):
            messages.extend([
                Message(
                    message_content=f"Customer message {i+1}",
                    direction="to_company",
                    social_create_time=base_time + timedelta(minutes=i*10),
                    conversation_id=1
                ),
                Message(
                    message_content=f"Agent response {i+1}",
                    direction="to_client", 
                    social_create_time=base_time + timedelta(minutes=i*10 + 2),
                    conversation_id=1
                )
            ])
        
        return Conversation(
            fb_chat_id="long_continuous_test",
            total_messages=len(messages),
            messages=messages
        )
    
    def _generate_test_report(self):
        """Generate comprehensive test report."""
        logger.info("\n=== INTERACTION DETECTION TEST REPORT ===")
        
        # Overall Status
        overall_success = all([
            self.test_results['time_gap_detection'],
            self.test_results['keyword_pattern_detection'], 
            self.test_results['real_conversation_analysis'],
            self.test_results['edge_cases_handled']
        ])
        
        status = "✅ PASSED" if overall_success else "❌ FAILED"
        logger.info(f"Overall Status: {status}")
        
        # Detailed Results
        logger.info(f"\nDetailed Results:")
        logger.info(f"  Time Gap Detection: {'✅' if self.test_results['time_gap_detection'] else '❌'}")
        logger.info(f"  Keyword Pattern Detection: {'✅' if self.test_results['keyword_pattern_detection'] else '❌'}")
        logger.info(f"  Real Conversation Analysis: {'✅' if self.test_results['real_conversation_analysis'] else '❌'}")
        logger.info(f"  Edge Cases Handled: {'✅' if self.test_results['edge_cases_handled'] else '❌'}")
        
        # Sample Results
        if self.test_results['sample_results']:
            logger.info(f"\nSample Analysis Results:")
            for result in self.test_results['sample_results']:
                logger.info(f"  Conversation {result['conversation_id']}: {result['total_messages']} msgs → {result['interactions_detected']} interactions")
                stats = result['detection_stats']
                logger.info(f"    Avg confidence: {stats.get('avg_confidence', 0):.2f}")
                logger.info(f"    Methods used: {stats.get('detection_methods', {})}")
        
        # Errors
        if self.test_results['errors']:
            logger.info(f"\nErrors Encountered ({len(self.test_results['errors'])}):")
            for i, error in enumerate(self.test_results['errors'], 1):
                logger.info(f"  {i}. {error}")
        
        # Recommendations
        logger.info(f"\nRecommendations:")
        if overall_success:
            logger.info("  ✅ Interaction detection ready for production use")
            logger.info("  🔄 Next: Implement interaction analytics service")
        else:
            failed_tests = [k for k, v in self.test_results.items() if k not in ['errors', 'sample_results'] and not v]
            logger.info(f"  ⚠️  Fix failed tests: {failed_tests}")
        
        logger.info("=== END REPORT ===")


async def main():
    """Run interaction detection tests."""
    tester = InteractionDetectionTester()
    results = await tester.run_comprehensive_test()
    return results

if __name__ == "__main__":
    asyncio.run(main())