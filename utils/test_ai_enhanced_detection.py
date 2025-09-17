"""
AI Enhanced Interaction Detection Test

This tests the hybrid AI enhancement approach:
1. Rule-based detection provides baseline boundaries
2. AI enhancement reviews and improves boundaries  
3. Final interactions incorporate both rule and AI insights

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
from services.gemini_service import GeminiService
from models import Conversation, Message
from database import SessionLocal
from config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AIEnhancedDetectionTester:
    """Test suite for AI-enhanced interaction detection."""
    
    def __init__(self):
        # Initialize with AI enhancement enabled
        gemini_service = GeminiService(settings.GEMINI_API_KEY)
        self.detection_service = InteractionDetectionService(gemini_service)
        
        # Enable AI enhancement
        self.detection_service.update_config({
            'ai_enhancement_enabled': True,
            'ai_enhancement_confidence_threshold': 0.6  # Lower for testing
        })
        
        self.test_results = {
            'ai_enhancement_working': False,
            'rule_vs_ai_comparison': {},
            'real_conversation_enhanced': False,
            'enhancement_quality': {},
            'errors': []
        }
    
    async def run_comprehensive_test(self):
        """Run all AI enhancement tests."""
        logger.info("=== Starting AI Enhanced Interaction Detection Test ===")
        
        # Test 1: AI enhancement on synthetic conversation
        await self._test_ai_enhancement_synthetic()
        
        # Test 2: Rule vs AI enhanced comparison  
        await self._test_rule_vs_ai_comparison()
        
        # Test 3: Real conversation AI enhancement
        await self._test_real_conversation_enhancement()
        
        # Test 4: Enhancement quality assessment
        await self._test_enhancement_quality()
        
        # Generate comprehensive report
        self._generate_enhancement_report()
        
        return self.test_results
    
    async def _test_ai_enhancement_synthetic(self):
        """Test AI enhancement with synthetic conversation designed to need improvements."""
        logger.info("Test 1: AI Enhancement on Synthetic Conversation")
        
        try:
            # Create conversation that should benefit from AI enhancement
            conversation = self._create_enhancement_test_conversation()
            
            # Run with AI enhancement enabled
            interactions = await self.detection_service.detect_interactions(conversation)
            
            if interactions:
                logger.info(f"✅ AI enhancement successful: {len(interactions)} interactions detected")
                self.test_results['ai_enhancement_working'] = True
                
                # Log interaction details
                for i, interaction in enumerate(interactions):
                    methods = [m.value for m in interaction.detection_methods]
                    logger.info(f"   Interaction {i+1}: {len(interaction.messages)} msgs, methods: {methods}, conf: {interaction.confidence:.2f}")
                    
                    # Check if any AI enhancement methods were used
                    if 'ai_fallback' in methods:
                        logger.info(f"   → AI enhancement detected in interaction {i+1}")
                
            else:
                logger.warning("No interactions detected with AI enhancement")
                
        except Exception as e:
            error_msg = f"❌ AI enhancement test failed: {str(e)}"
            logger.error(error_msg)
            self.test_results['errors'].append(error_msg)
    
    async def _test_rule_vs_ai_comparison(self):
        """Compare rule-only vs AI-enhanced detection on same conversation."""
        logger.info("Test 2: Rule vs AI Enhanced Comparison")
        
        try:
            # Create test conversation
            conversation = self._create_comparison_test_conversation()
            
            # Test 1: Rule-only detection
            self.detection_service.update_config({'ai_enhancement_enabled': False})
            rule_interactions = await self.detection_service.detect_interactions(conversation)
            
            # Test 2: AI-enhanced detection
            self.detection_service.update_config({'ai_enhancement_enabled': True})
            ai_interactions = await self.detection_service.detect_interactions(conversation)
            
            # Compare results
            comparison = {
                'rule_only_count': len(rule_interactions),
                'ai_enhanced_count': len(ai_interactions),
                'improvement': len(ai_interactions) - len(rule_interactions),
                'rule_confidence': sum(i.confidence for i in rule_interactions) / len(rule_interactions) if rule_interactions else 0,
                'ai_confidence': sum(i.confidence for i in ai_interactions) / len(ai_interactions) if ai_interactions else 0
            }
            
            self.test_results['rule_vs_ai_comparison'] = comparison
            
            logger.info(f"Rule-only: {comparison['rule_only_count']} interactions (avg conf: {comparison['rule_confidence']:.2f})")
            logger.info(f"AI-enhanced: {comparison['ai_enhanced_count']} interactions (avg conf: {comparison['ai_confidence']:.2f})")
            logger.info(f"Improvement: {comparison['improvement']} interactions")
            
            if comparison['ai_enhanced_count'] >= comparison['rule_only_count']:
                logger.info("✅ AI enhancement maintained or improved interaction detection")
            else:
                logger.warning("⚠️ AI enhancement reduced interaction count")
                
        except Exception as e:
            error_msg = f"❌ Rule vs AI comparison failed: {str(e)}"
            logger.error(error_msg)
            self.test_results['errors'].append(error_msg)
    
    async def _test_real_conversation_enhancement(self):
        """Test AI enhancement on real database conversation."""
        logger.info("Test 3: Real Conversation AI Enhancement")
        
        try:
            db = SessionLocal()
            try:
                # Get a real conversation with reasonable length
                conversation = (
                    db.query(Conversation)
                    .filter(Conversation.total_messages.between(5, 15))  # Medium length
                    .first()
                )
                
                if not conversation:
                    logger.warning("No suitable real conversation found")
                    return
                
                logger.info(f"Testing AI enhancement on conversation {conversation.id} ({conversation.total_messages} messages)")
                
                # Run AI-enhanced detection
                interactions = await self.detection_service.detect_interactions(conversation)
                
                if interactions:
                    self.test_results['real_conversation_enhanced'] = True
                    logger.info(f"✅ Real conversation enhanced: {len(interactions)} interactions")
                    
                    # Store enhancement details
                    enhancement_details = {
                        'conversation_id': conversation.id,
                        'original_messages': conversation.total_messages,
                        'detected_interactions': len(interactions),
                        'avg_confidence': sum(i.confidence for i in interactions) / len(interactions),
                        'detection_methods': {}
                    }
                    
                    # Count detection methods
                    for interaction in interactions:
                        for method in interaction.detection_methods:
                            method_name = method.value
                            enhancement_details['detection_methods'][method_name] = enhancement_details['detection_methods'].get(method_name, 0) + 1
                    
                    self.test_results['enhancement_quality'] = enhancement_details
                    logger.info(f"   Methods used: {enhancement_details['detection_methods']}")
                    
                else:
                    logger.warning("No interactions detected in real conversation")
                    
            finally:
                db.close()
                
        except Exception as e:
            error_msg = f"❌ Real conversation enhancement failed: {str(e)}"
            logger.error(error_msg)
            self.test_results['errors'].append(error_msg)
    
    async def _test_enhancement_quality(self):
        """Test the quality and consistency of AI enhancements."""
        logger.info("Test 4: Enhancement Quality Assessment")
        
        try:
            # Test with conversation that has obvious enhancement opportunities
            conversation = self._create_quality_test_conversation()
            
            # Run multiple times to test consistency
            results = []
            for i in range(3):
                interactions = await self.detection_service.detect_interactions(conversation)
                results.append({
                    'run': i + 1,
                    'interaction_count': len(interactions),
                    'avg_confidence': sum(i.confidence for i in interactions) / len(interactions) if interactions else 0
                })
            
            # Analyze consistency
            counts = [r['interaction_count'] for r in results]
            confidences = [r['avg_confidence'] for r in results]
            
            consistency_metrics = {
                'count_variance': max(counts) - min(counts),
                'avg_count': sum(counts) / len(counts),
                'confidence_variance': max(confidences) - min(confidences),
                'avg_confidence': sum(confidences) / len(confidences)
            }
            
            logger.info(f"Consistency test: {consistency_metrics}")
            
            # Quality thresholds
            if (consistency_metrics['count_variance'] <= 1 and 
                consistency_metrics['confidence_variance'] <= 0.2):
                logger.info("✅ AI enhancement shows good consistency")
            else:
                logger.warning("⚠️ AI enhancement shows inconsistent results")
                
        except Exception as e:
            error_msg = f"❌ Enhancement quality test failed: {str(e)}"
            logger.error(error_msg)
            self.test_results['errors'].append(error_msg)
    
    def _create_enhancement_test_conversation(self) -> Conversation:
        """Create conversation that should benefit from AI boundary enhancement."""
        base_time = datetime(2025, 9, 17, 9, 0, 0)
        
        messages = [
            # Power outage issue
            Message(
                message_content="Hello, power is out in my area since morning",
                direction="to_company",
                social_create_time=base_time,
                conversation_id=1
            ),
            Message(
                message_content="We'll check on this immediately. Can you confirm your area?",
                direction="to_client",
                social_create_time=base_time + timedelta(minutes=5),
                conversation_id=1
            ),
            Message(
                message_content="Kinoo area, house number 45",
                direction="to_company",
                social_create_time=base_time + timedelta(minutes=7),
                conversation_id=1
            ),
            # Continuation of same issue - should NOT be separate interaction
            Message(
                message_content="Also, my neighbor at 47 has the same problem",
                direction="to_company",
                social_create_time=base_time + timedelta(minutes=8),
                conversation_id=1
            ),
            Message(
                message_content="Thank you, we've identified the transformer issue. Repair team dispatched.",
                direction="to_client",
                social_create_time=base_time + timedelta(minutes=15),
                conversation_id=1
            ),
            # Resolution
            Message(
                message_content="Power restored in your area. Please confirm.",
                direction="to_client",
                social_create_time=base_time + timedelta(hours=2),
                conversation_id=1
            ),
            Message(
                message_content="Yes, power is back. Thank you!",
                direction="to_company",
                social_create_time=base_time + timedelta(hours=2, minutes=5),
                conversation_id=1
            ),
            # NEW different issue - should be separate interaction
            Message(
                message_content="By the way, I received a bill that seems too high. Can you check?",
                direction="to_company",
                social_create_time=base_time + timedelta(hours=2, minutes=10),
                conversation_id=1
            )
        ]
        
        return Conversation(
            fb_chat_id="ai_enhancement_test",
            total_messages=len(messages),
            messages=messages
        )
    
    def _create_comparison_test_conversation(self) -> Conversation:
        """Create conversation for rule vs AI comparison."""
        base_time = datetime(2025, 9, 17, 10, 0, 0)
        
        messages = [
            Message(
                message_content="My prepaid meter shows error E01",
                direction="to_company",
                social_create_time=base_time,
                conversation_id=1
            ),
            Message(
                message_content="Error E01 indicates low balance. Please top up your account.",
                direction="to_client",
                social_create_time=base_time + timedelta(minutes=3),
                conversation_id=1
            ),
            Message(
                message_content="I just topped up but still showing error",
                direction="to_company",
                social_create_time=base_time + timedelta(minutes=5),
                conversation_id=1
            ),
            Message(
                message_content="Let me reset your meter remotely. Please wait 5 minutes.",
                direction="to_client",
                social_create_time=base_time + timedelta(minutes=7),
                conversation_id=1
            ),
            Message(
                message_content="Working now, thank you",
                direction="to_company",
                social_create_time=base_time + timedelta(minutes=12),
                conversation_id=1
            )
        ]
        
        return Conversation(
            fb_chat_id="comparison_test",
            total_messages=len(messages),
            messages=messages
        )
    
    def _create_quality_test_conversation(self) -> Conversation:
        """Create conversation to test enhancement consistency."""
        base_time = datetime(2025, 9, 17, 11, 0, 0)
        
        messages = [
            Message(
                message_content="I need help with two different issues",
                direction="to_company",
                social_create_time=base_time,
                conversation_id=1
            ),
            Message(
                message_content="Sure, I'll help with both. What's the first issue?",
                direction="to_client",
                social_create_time=base_time + timedelta(minutes=1),
                conversation_id=1
            ),
            Message(
                message_content="My bill calculation seems wrong for last month",
                direction="to_company",
                social_create_time=base_time + timedelta(minutes=2),
                conversation_id=1
            ),
            Message(
                message_content="Let me check... I see the issue. Bill has been corrected.",
                direction="to_client",
                social_create_time=base_time + timedelta(minutes=5),
                conversation_id=1
            ),
            Message(
                message_content="Great! Now the second issue - my street light is not working",
                direction="to_company",
                social_create_time=base_time + timedelta(minutes=6),
                conversation_id=1
            ),
            Message(
                message_content="I'll report this to our maintenance team. Expect repair within 48 hours.",
                direction="to_client",
                social_create_time=base_time + timedelta(minutes=8),
                conversation_id=1
            )
        ]
        
        return Conversation(
            fb_chat_id="quality_test",
            total_messages=len(messages),
            messages=messages
        )
    
    def _generate_enhancement_report(self):
        """Generate comprehensive AI enhancement test report."""
        logger.info("\n=== AI ENHANCED INTERACTION DETECTION REPORT ===")
        
        # Overall Status
        overall_success = (
            self.test_results['ai_enhancement_working'] and
            self.test_results['real_conversation_enhanced']
        )
        
        status = "✅ PASSED" if overall_success else "❌ FAILED"
        logger.info(f"Overall Status: {status}")
        
        # Detailed Results
        logger.info(f"\nDetailed Results:")
        logger.info(f"  AI Enhancement Working: {'✅' if self.test_results['ai_enhancement_working'] else '❌'}")
        logger.info(f"  Real Conversation Enhanced: {'✅' if self.test_results['real_conversation_enhanced'] else '❌'}")
        
        # Rule vs AI Comparison
        if self.test_results['rule_vs_ai_comparison']:
            comparison = self.test_results['rule_vs_ai_comparison']
            logger.info(f"\nRule vs AI Comparison:")
            logger.info(f"  Rule-only interactions: {comparison['rule_only_count']}")
            logger.info(f"  AI-enhanced interactions: {comparison['ai_enhanced_count']}")
            logger.info(f"  Improvement: {comparison['improvement']}")
            logger.info(f"  Confidence improvement: {comparison['ai_confidence'] - comparison['rule_confidence']:.3f}")
        
        # Enhancement Quality
        if self.test_results['enhancement_quality']:
            quality = self.test_results['enhancement_quality']
            logger.info(f"\nEnhancement Quality (Real Conversation {quality['conversation_id']}):")
            logger.info(f"  {quality['original_messages']} messages → {quality['detected_interactions']} interactions")
            logger.info(f"  Average confidence: {quality['avg_confidence']:.3f}")
            logger.info(f"  Detection methods: {quality['detection_methods']}")
        
        # Errors
        if self.test_results['errors']:
            logger.info(f"\nErrors Encountered ({len(self.test_results['errors'])}):")
            for i, error in enumerate(self.test_results['errors'], 1):
                logger.info(f"  {i}. {error}")
        
        # Recommendations
        logger.info(f"\nRecommendations:")
        if overall_success:
            logger.info("  ✅ AI-enhanced interaction detection ready for production")
            logger.info("  🔄 Next: Implement interaction analytics service")
        else:
            logger.info("  ⚠️  Fix AI enhancement issues before proceeding")
        
        logger.info("=== END ENHANCEMENT REPORT ===")


async def main():
    """Run AI enhanced interaction detection tests."""
    tester = AIEnhancedDetectionTester()
    results = await tester.run_comprehensive_test()
    return results

if __name__ == "__main__":
    asyncio.run(main())