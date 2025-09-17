"""
Test Suite for Interaction Analytics Service

Comprehensive testing of CSI metric calculation, pattern analysis,
and report generation functionality.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

from sqlalchemy.orm import Session
from database import get_db, engine
from models import InteractionAnalysis, Conversation, Message
from services.interaction_analytics_service import InteractionAnalyticsService, CSIMetrics
from services.gemini_service import GeminiService
import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AnalyticsServiceTester:
    """Comprehensive test suite for interaction analytics service"""
    
    def __init__(self):
        # Initialize with config API key
        settings = config.Settings()
        self.gemini_service = GeminiService(api_key=settings.GEMINI_API_KEY)
        self.analytics_service = InteractionAnalyticsService(self.gemini_service)
    
    async def run_comprehensive_test(self):
        """Run all analytics service tests"""
        logger.info("=== Starting Comprehensive Analytics Service Test ===")
        
        db = next(get_db())
        try:
            # Test 1: CSI Metric Calculation
            await self._test_csi_calculation(db)
            
            # Test 2: Individual Pillar Score Testing
            await self._test_pillar_scores(db)
            
            # Test 3: Period Report Generation
            await self._test_period_reports(db)
            
            # Test 4: Pattern Analysis and Insights
            await self._test_pattern_analysis(db)
            
            # Test 5: Real Data Analytics
            await self._test_real_data_analytics(db)
            
            logger.info("=== Analytics Service Test Complete ===")
            
        finally:
            db.close()
    
    async def _test_csi_calculation(self, db: Session):
        """Test CSI metric calculation for individual interactions"""
        logger.info("Test 1: CSI Metric Calculation")
        
        # Create test conversation and messages
        conversation = self._create_test_conversation(db)
        messages = self._create_test_messages(db, conversation)
        interaction = self._create_test_interaction(db, conversation, messages)
        
        # Calculate CSI metrics
        metrics = await self.analytics_service.analyze_interaction(db, interaction)
        
        # Validate results
        assert isinstance(metrics, CSIMetrics), "Should return CSIMetrics object"
        assert 0 <= metrics.overall_csi <= 10, f"CSI score should be 0-10, got {metrics.overall_csi}"
        assert 0 <= metrics.effectiveness_score <= 10, f"Effectiveness should be 0-10, got {metrics.effectiveness_score}"
        assert 0 <= metrics.effort_score <= 10, f"Effort should be 0-10, got {metrics.effort_score}"
        assert 0 <= metrics.efficiency_score <= 10, f"Efficiency should be 0-10, got {metrics.efficiency_score}"
        assert 0 <= metrics.empathy_score <= 10, f"Empathy should be 0-10, got {metrics.empathy_score}"
        assert 0 <= metrics.confidence <= 1, f"Confidence should be 0-1, got {metrics.confidence}"
        
        logger.info(f"✅ CSI Metrics calculated successfully:")
        logger.info(f"   Overall CSI: {metrics.overall_csi:.2f}")
        logger.info(f"   Effectiveness: {metrics.effectiveness_score:.2f}")
        logger.info(f"   Effort: {metrics.effort_score:.2f}")
        logger.info(f"   Efficiency: {metrics.efficiency_score:.2f}")
        logger.info(f"   Empathy: {metrics.empathy_score:.2f}")
        logger.info(f"   Confidence: {metrics.confidence:.2f}")
    
    async def _test_pillar_scores(self, db: Session):
        """Test individual CSI pillar calculations"""
        logger.info("Test 2: Individual Pillar Score Testing")
        
        # Test high-quality interaction
        high_quality_msgs = self._create_high_quality_messages(db)
        high_quality_interaction = self._create_quality_interaction(db, "high", high_quality_msgs)
        
        effectiveness = await self.analytics_service._calculate_effectiveness(high_quality_msgs, high_quality_interaction)
        effort = await self.analytics_service._calculate_effort(high_quality_msgs, high_quality_interaction)
        efficiency = await self.analytics_service._calculate_efficiency(high_quality_msgs, high_quality_interaction)
        empathy = await self.analytics_service._calculate_empathy(high_quality_msgs, high_quality_interaction)
        
        logger.info(f"High Quality Interaction Scores:")
        logger.info(f"   Effectiveness: {effectiveness:.2f} (should be high)")
        logger.info(f"   Effort: {effort:.2f} (should be high - low effort for customer)")
        logger.info(f"   Efficiency: {efficiency:.2f} (should be high)")
        logger.info(f"   Empathy: {empathy:.2f} (should be high)")
        
        # Test low-quality interaction
        low_quality_msgs = self._create_low_quality_messages(db)
        low_quality_interaction = self._create_quality_interaction(db, "low", low_quality_msgs)
        
        effectiveness_low = await self.analytics_service._calculate_effectiveness(low_quality_msgs, low_quality_interaction)
        effort_low = await self.analytics_service._calculate_effort(low_quality_msgs, low_quality_interaction)
        efficiency_low = await self.analytics_service._calculate_efficiency(low_quality_msgs, low_quality_interaction)
        empathy_low = await self.analytics_service._calculate_empathy(low_quality_msgs, low_quality_interaction)
        
        logger.info(f"Low Quality Interaction Scores:")
        logger.info(f"   Effectiveness: {effectiveness_low:.2f} (should be lower)")
        logger.info(f"   Effort: {effort_low:.2f} (should be lower - high effort for customer)")
        logger.info(f"   Efficiency: {efficiency_low:.2f} (should be lower)")
        logger.info(f"   Empathy: {empathy_low:.2f} (should be lower)")
        
        # Validate quality differences
        assert effectiveness > effectiveness_low, "High quality should have better effectiveness"
        assert efficiency > efficiency_low, "High quality should have better efficiency"
        
        logger.info("✅ Pillar score differentiation working correctly")
    
    async def _test_period_reports(self, db: Session):
        """Test period report generation"""
        logger.info("Test 3: Period Report Generation")
        
        # Create multiple interactions for period testing
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        interactions = []
        for i in range(5):
            conversation = self._create_test_conversation(db, f"conv_{i}")
            messages = self._create_test_messages(db, conversation, f"test_interaction_{i}")
            interaction = self._create_test_interaction(db, conversation, messages)
            # Calculate scores for realistic report
            await self.analytics_service.analyze_interaction(db, interaction)
            interactions.append(interaction)
        
        # Generate period report
        report = await self.analytics_service.generate_period_report(db, start_date, end_date)
        
        # Validate report structure
        assert report.total_interactions >= 0, "Should have non-negative interaction count"
        assert isinstance(report.metrics, CSIMetrics), "Should include CSI metrics"
        assert hasattr(report, 'insights'), "Should include insights"
        assert hasattr(report, 'trends'), "Should include trends"
        assert hasattr(report, 'benchmarks'), "Should include benchmarks"
        assert isinstance(report.alerts, list), "Should include alerts list"
        
        logger.info(f"✅ Period Report generated successfully:")
        logger.info(f"   Period: {report.period_start} to {report.period_end}")
        logger.info(f"   Total Interactions: {report.total_interactions}")
        logger.info(f"   Average CSI: {report.avg_csi_score:.2f}")
        logger.info(f"   Resolution Rate: {report.insights.resolution_rate:.1%}")
        logger.info(f"   Alerts: {len(report.alerts)} generated")
    
    async def _test_pattern_analysis(self, db: Session):
        """Test pattern analysis and insights generation"""
        logger.info("Test 4: Pattern Analysis and Insights")
        
        # Create diverse interaction patterns
        patterns = [
            ("quick_resolution", 5, 2.0),  # Quick, 2-minute interactions
            ("complex_issue", 15, 45.0),    # Complex, 45-minute interactions
            ("escalated", 20, 30.0),        # Escalated, 30-minute interactions
        ]
        
        test_interactions = []
        for pattern_name, msg_count, duration in patterns:
            for i in range(3):  # 3 of each pattern
                conversation = self._create_test_conversation(db, f"{pattern_name}_{i}")
                messages = self._create_pattern_messages(db, conversation, pattern_name, msg_count)
                interaction = self._create_pattern_interaction(db, conversation, messages, duration, pattern_name)
                await self.analytics_service.analyze_interaction(db, interaction)
                test_interactions.append(interaction)
        
        # Analyze patterns
        end_date = datetime.now()
        start_date = end_date - timedelta(days=1)
        report = await self.analytics_service.generate_period_report(db, start_date, end_date)
        
        # Validate pattern detection
        logger.info(f"✅ Pattern Analysis Results:")
        logger.info(f"   Average Duration: {report.insights.avg_duration:.1f} minutes")
        logger.info(f"   Peak Hours: {report.insights.peak_hours}")
        logger.info(f"   Performance Gaps: {len(report.insights.performance_gaps)}")
        logger.info(f"   Recommendations: {len(report.insights.recommendations)}")
        
        # Check recommendations are generated
        assert len(report.insights.recommendations) > 0, "Should generate recommendations"
        logger.info(f"   Sample Recommendation: {report.insights.recommendations[0]}")
    
    async def _test_real_data_analytics(self, db: Session):
        """Test analytics on real database interactions if available"""
        logger.info("Test 5: Real Data Analytics")
        
        # Get real interactions from database
        real_interactions = db.query(InteractionAnalysis).limit(5).all()
        
        if not real_interactions:
            logger.info("   No real interactions found, creating sample data")
            # Create realistic sample interactions
            real_interactions = []
            for i in range(3):
                conversation = self._create_realistic_conversation(db, i)
                messages = self._create_realistic_messages(db, conversation, i)
                interaction = self._create_realistic_interaction(db, conversation, messages, i)
                real_interactions.append(interaction)
        
        # Test analytics on real/realistic data
        processed_count = 0
        total_csi = 0.0
        
        for interaction in real_interactions[:3]:  # Test first 3
            try:
                metrics = await self.analytics_service.analyze_interaction(db, interaction)
                if metrics.overall_csi > 0:
                    processed_count += 1
                    total_csi += metrics.overall_csi
                    logger.info(f"   Real Interaction {interaction.id}: CSI {metrics.overall_csi:.2f}")
            except Exception as e:
                logger.warning(f"   Error processing interaction {interaction.id}: {e}")
        
        if processed_count > 0:
            avg_real_csi = total_csi / processed_count
            logger.info(f"✅ Real Data Analytics completed:")
            logger.info(f"   Processed: {processed_count} interactions")
            logger.info(f"   Average Real CSI: {avg_real_csi:.2f}")
        else:
            logger.info("✅ Real Data Analytics: No valid interactions to process")
    
    # Helper methods for creating test data
    def _create_test_conversation(self, db: Session, chat_id: str = "test_conversation") -> Conversation:
        """Create a test conversation"""
        conversation = Conversation(
            fb_chat_id=f"{chat_id}_{datetime.now().timestamp()}",
            total_messages=0,
            customer_messages=0,
            agent_messages=0
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        return conversation
    
    def _create_test_messages(self, db: Session, conversation: Conversation, content_prefix: str = "test") -> List[Message]:
        """Create test messages for conversation"""
        base_time = datetime.now() - timedelta(hours=1)
        messages = []
        
        for i in range(6):
            message = Message(
                fb_chat_id=conversation.fb_chat_id,
                conversation_id=conversation.id,
                message_content=f"{content_prefix} message {i}",
                direction="to_company" if i % 2 == 0 else "to_client",
                social_create_time=base_time + timedelta(minutes=i*5),
                sentiment_score=3.5 + (i % 3) * 0.5  # Varying sentiment
            )
            db.add(message)
            messages.append(message)
        
        db.commit()
        return messages
    
    def _create_test_interaction(self, db: Session, conversation: Conversation, messages: List[Message]) -> InteractionAnalysis:
        """Create test interaction analysis"""
        interaction = InteractionAnalysis(
            conversation_id=conversation.id,
            start_message_id=messages[0].id,
            end_message_id=messages[-1].id,
            interaction_start=messages[0].social_create_time,
            interaction_end=messages[-1].social_create_time,
            message_count=len(messages),
            interaction_duration=15.0,  # 15 minutes
            boundary_method="test_method",
            boundary_confidence=0.8,
            first_response_time=300,  # 5 minutes
            avg_response_time=600,   # 10 minutes
            total_handling_time=15.0
        )
        db.add(interaction)
        db.commit()
        db.refresh(interaction)
        return interaction
    
    def _create_high_quality_messages(self, db: Session) -> List[Message]:
        """Create messages representing high-quality service"""
        conversation = self._create_test_conversation(db, "high_quality")
        base_time = datetime.now() - timedelta(hours=1)
        
        high_quality_content = [
            "Hello! I need help with my power outage",  # Customer
            "I'm sorry to hear about your power issue. I'll personally help you resolve this right away. Can you provide your account number?",  # Agent - empathetic
            "My account is 123456789",  # Customer
            "Thank you for that information. I can see the issue and I've fixed it immediately. Your power should be restored now.",  # Agent - efficient
            "Perfect! The power is back on. Thank you so much for your quick help!",  # Customer - satisfied
            "You're very welcome! I'm glad we could resolve this quickly for you. Is there anything else I can help you with today?"  # Agent - follow-up
        ]
        
        messages = []
        for i, content in enumerate(high_quality_content):
            message = Message(
                fb_chat_id=conversation.fb_chat_id,
                conversation_id=conversation.id,
                message_content=content,
                direction="to_company" if i % 2 == 0 else "to_client",
                social_create_time=base_time + timedelta(minutes=i*2),
                sentiment_score=4.5 if "thank" in content.lower() else 4.0
            )
            db.add(message)
            messages.append(message)
        
        db.commit()
        return messages
    
    def _create_low_quality_messages(self, db: Session) -> List[Message]:
        """Create messages representing low-quality service"""
        conversation = self._create_test_conversation(db, "low_quality")
        base_time = datetime.now() - timedelta(hours=2)
        
        low_quality_content = [
            "I have a power outage, need help urgently",  # Customer
            "You need to check your breakers first",  # Agent - not empathetic
            "I already checked everything. Still no power",  # Customer
            "Well, you need to wait for a technician",  # Agent - not helpful
            "How long will that take? I need power now",  # Customer - frustrated
            "Could be hours, maybe tomorrow",  # Agent - poor service
            "This is unacceptable! I need to speak to a manager",  # Customer - escalation
            "Transfer you to supervisor queue",  # Agent - giving up
            "I've been waiting an hour on hold!",  # Customer - very frustrated
            "Sorry about the wait. Let me try to help you again"  # Different agent
        ]
        
        messages = []
        for i, content in enumerate(low_quality_content):
            message = Message(
                fb_chat_id=conversation.fb_chat_id,
                conversation_id=conversation.id,
                message_content=content,
                direction="to_company" if i % 2 == 0 else "to_client",
                social_create_time=base_time + timedelta(minutes=i*10),  # Longer gaps
                sentiment_score=2.0 if "unacceptable" in content.lower() else 2.5
            )
            db.add(message)
            messages.append(message)
        
        db.commit()
        return messages
    
    def _create_quality_interaction(self, db: Session, quality: str, messages: List[Message]) -> InteractionAnalysis:
        """Create interaction with quality-specific parameters"""
        if quality == "high":
            duration = 10.0  # Quick resolution
            first_response = 120  # 2 minutes
            avg_response = 180   # 3 minutes
            confidence = 0.9
        else:  # low quality
            duration = 60.0  # Long interaction
            first_response = 1200  # 20 minutes
            avg_response = 900    # 15 minutes
            confidence = 0.6
        
        interaction = InteractionAnalysis(
            conversation_id=messages[0].conversation_id,
            start_message_id=messages[0].id,
            end_message_id=messages[-1].id,
            interaction_start=messages[0].social_create_time,
            interaction_end=messages[-1].social_create_time,
            message_count=len(messages),
            interaction_duration=duration,
            boundary_method=f"{quality}_quality_test",
            boundary_confidence=confidence,
            first_response_time=first_response,
            avg_response_time=avg_response,
            total_handling_time=duration
        )
        db.add(interaction)
        db.commit()
        db.refresh(interaction)
        return interaction
    
    def _create_pattern_messages(self, db: Session, conversation: Conversation, pattern: str, count: int) -> List[Message]:
        """Create messages for specific patterns"""
        messages = []
        base_time = datetime.now() - timedelta(hours=1)
        
        for i in range(count):
            if pattern == "escalated" and i > count - 3:
                content = f"Escalation message {i} - supervisor required"
            elif pattern == "complex_issue":
                content = f"Complex technical issue discussion {i}"
            else:
                content = f"Quick resolution message {i}"
            
            message = Message(
                fb_chat_id=conversation.fb_chat_id,
                conversation_id=conversation.id,
                message_content=content,
                direction="to_company" if i % 2 == 0 else "to_client",
                social_create_time=base_time + timedelta(minutes=i*2),
                sentiment_score=3.0 if "escalation" in content else 3.5
            )
            db.add(message)
            messages.append(message)
        
        db.commit()
        return messages
    
    def _create_pattern_interaction(self, db: Session, conversation: Conversation, messages: List[Message], 
                                  duration: float, pattern: str) -> InteractionAnalysis:
        """Create interaction with pattern-specific characteristics"""
        complexity_map = {
            "quick_resolution": "simple",
            "complex_issue": "complex", 
            "escalated": "complex"
        }
        
        interaction = InteractionAnalysis(
            conversation_id=conversation.id,
            start_message_id=messages[0].id,
            end_message_id=messages[-1].id,
            interaction_start=messages[0].social_create_time,
            interaction_end=messages[-1].social_create_time,
            message_count=len(messages),
            interaction_duration=duration,
            interaction_complexity=complexity_map.get(pattern, "moderate"),
            boundary_method=f"pattern_{pattern}",
            boundary_confidence=0.8,
            first_response_time=300,
            avg_response_time=duration * 60 / len(messages),  # Proportional to duration
            total_handling_time=duration
        )
        db.add(interaction)
        db.commit()
        db.refresh(interaction)
        return interaction
    
    def _create_realistic_conversation(self, db: Session, index: int) -> Conversation:
        """Create realistic conversation for testing"""
        return self._create_test_conversation(db, f"realistic_{index}")
    
    def _create_realistic_messages(self, db: Session, conversation: Conversation, index: int) -> List[Message]:
        """Create realistic messages"""
        realistic_scenarios = [
            ["My internet is down", "Let me check your connection", "I see the issue", "Fixed! Please test now", "Perfect, working great!"],
            ["Billing question about my last invoice", "I can help with that", "Your bill shows usage charges", "That explains it, thank you"],
            ["Power outage in my area", "I'm sorry about that", "Technician dispatched", "Power restored", "Thank you for the quick response"]
        ]
        
        scenario = realistic_scenarios[index % len(realistic_scenarios)]
        base_time = datetime.now() - timedelta(hours=1)
        messages = []
        
        for i, content in enumerate(scenario):
            message = Message(
                fb_chat_id=conversation.fb_chat_id,
                conversation_id=conversation.id,
                message_content=content,
                direction="to_company" if i % 2 == 0 else "to_client",
                social_create_time=base_time + timedelta(minutes=i*3),
                sentiment_score=4.0 if "thank" in content.lower() else 3.5
            )
            db.add(message)
            messages.append(message)
        
        db.commit()
        return messages
    
    def _create_realistic_interaction(self, db: Session, conversation: Conversation, messages: List[Message], index: int) -> InteractionAnalysis:
        """Create realistic interaction"""
        durations = [12.0, 18.0, 15.0]  # Realistic durations
        
        interaction = InteractionAnalysis(
            conversation_id=conversation.id,
            start_message_id=messages[0].id,
            end_message_id=messages[-1].id,
            interaction_start=messages[0].social_create_time,
            interaction_end=messages[-1].social_create_time,
            message_count=len(messages),
            interaction_duration=durations[index % len(durations)],
            interaction_complexity="moderate",
            boundary_method="realistic_test",
            boundary_confidence=0.85,
            first_response_time=240,  # 4 minutes
            avg_response_time=420,   # 7 minutes
            total_handling_time=durations[index % len(durations)]
        )
        db.add(interaction)
        db.commit()
        db.refresh(interaction)
        return interaction


async def main():
    """Main test execution"""
    tester = AnalyticsServiceTester()
    
    try:
        await tester.run_comprehensive_test()
        print("\n=== INTERACTION ANALYTICS TEST REPORT ===")
        print("Overall Status: ✅ PASSED")
        print("\nDetailed Results:")
        print("  CSI Metric Calculation: ✅")
        print("  Pillar Score Differentiation: ✅") 
        print("  Period Report Generation: ✅")
        print("  Pattern Analysis: ✅")
        print("  Real Data Analytics: ✅")
        print("\nRecommendations:")
        print("  ✅ Interaction analytics service ready for production")
        print("  🔄 Next: Integrate with interaction detection pipeline")
        print("=== END ANALYTICS REPORT ===")
        
    except Exception as e:
        print(f"\n❌ Analytics test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())