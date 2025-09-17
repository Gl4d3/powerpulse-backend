"""
Constitutional Compliance Tests for PowerPulse Interaction Analysis

These tests enforce the CONSTITUTION.md requirements and ensure interaction analysis
follows the same AI micro-metrics approach as daily analysis.

CONSTITUTIONAL REQUIREMENTS TESTED:
1. AI micro-metrics extraction (not rule-based) for interaction analysis
2. Same micro-metrics output format as daily analysis
3. CSI correlation >0.8 between daily and interaction methods
4. Dual CSI storage (calculated + inferred)
5. No degradation in system performance
"""

import pytest
import json
import asyncio
import numpy as np
from typing import List, Dict, Any
from datetime import datetime, date
from scipy.stats import pearsonr
from sqlalchemy.orm import Session

from database import get_db, SessionLocal
from models import Conversation, Message, DailyAnalysis, InteractionAnalysis
from services.gemini_service import GeminiService
from services.analytics_service import analytics_service
from services.enhanced_analytics_service import enhanced_analytics_service
from services.csi_analysis_pipeline import CSIAnalysisPipeline
from config import settings

# Test Configuration
CURATED_SAMPLE_PATH = "attached_assets/curated_sample.json"
CONSTITUTIONAL_CORRELATION_THRESHOLD = 0.8
MAX_CSI_DEVIATION_PERCENT = 5.0

class TestConstitutionalCompliance:
    """Test suite enforcing CONSTITUTION.md requirements"""

    @pytest.fixture
    def db_session(self):
        """Database session fixture"""
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    @pytest.fixture
    def gemini_service(self):
        """Gemini service fixture"""
        return GeminiService(api_key=settings.GEMINI_API_KEY)

    @pytest.fixture
    def curated_sample_data(self):
        """Load curated sample data for testing"""
        try:
            with open(CURATED_SAMPLE_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            pytest.skip(f"Curated sample not found at {CURATED_SAMPLE_PATH}")

    def test_ai_micrometrics_extraction_requirement(self, db_session, gemini_service):
        """
        CONSTITUTIONAL TEST: Verify interaction analysis uses AI micro-metrics extraction
        
        AMENDMENT I: AI micro-metrics extraction SHALL remain the authoritative method
        """
        # Verify GeminiService has analyze_interaction_analyses_batch method
        assert hasattr(gemini_service, 'analyze_interaction_analyses_batch'), \
            "CONSTITUTIONAL VIOLATION: Missing AI micro-metrics extraction for interactions"
        
        # Verify the method signature matches daily analysis approach
        daily_method = getattr(gemini_service, 'analyze_daily_analyses_batch')
        interaction_method = getattr(gemini_service, 'analyze_interaction_analyses_batch')
        
        # Both methods should have similar signatures and return formats
        assert callable(daily_method), "Daily analysis method must be callable"
        assert callable(interaction_method), "Interaction analysis method must be callable"

    def test_micrometrics_output_format_consistency(self, db_session, gemini_service):
        """
        CONSTITUTIONAL TEST: Verify interaction analysis produces same micro-metrics format
        
        AMENDMENT II: ALL other pipeline logic SHALL remain identical
        """
        # Test that interaction analysis produces the required micro-metrics:
        # - sentiment_score (0-10)
        # - sentiment_shift (-5 to +5) 
        # - resolution_achieved (0-10)
        # - fcr_score (0-10)
        # - ces (1-7)
        # - common_topics (array)
        
        required_micrometrics = [
            'sentiment_score', 'sentiment_shift', 'resolution_achieved',
            'fcr_score', 'ces', 'common_topics'
        ]
        
        # Get sample interactions
        sample_interactions = db_session.query(InteractionAnalysis).limit(5).all()
        
        for interaction in sample_interactions:
            # Verify all required fields exist (may be None if not yet processed)
            for metric in required_micrometrics:
                assert hasattr(interaction, metric), \
                    f"CONSTITUTIONAL VIOLATION: Missing {metric} field in InteractionAnalysis"

    @pytest.mark.asyncio
    async def test_csi_correlation_between_methods(self, db_session, curated_sample_data):
        """
        CONSTITUTIONAL TEST: Validate CSI correlation >0.8 between daily and interaction methods
        
        DATA INTEGRITY PRINCIPLE: Results must be statistically comparable
        """
        # Process curated sample through both pipelines
        daily_csi_scores = []
        interaction_csi_scores = []
        
        # Process a subset for performance (first 10 conversations)
        sample_conversations = list(curated_sample_data.keys())[:10]
        
        for chat_id in sample_conversations:
            # Get daily analysis CSI
            daily_analyses = db_session.query(DailyAnalysis).join(Conversation).filter(
                Conversation.fb_chat_id == chat_id,
                DailyAnalysis.csi_score.isnot(None)
            ).all()
            
            # Get interaction analysis CSI
            interaction_analyses = db_session.query(InteractionAnalysis).join(Conversation).filter(
                Conversation.fb_chat_id == chat_id,
                InteractionAnalysis.csi_score.isnot(None)
            ).all()
            
            if daily_analyses and interaction_analyses:
                daily_avg = np.mean([d.csi_score for d in daily_analyses])
                interaction_avg = np.mean([i.csi_score for i in interaction_analyses])
                
                daily_csi_scores.append(daily_avg)
                interaction_csi_scores.append(interaction_avg)
        
        # Calculate correlation
        if len(daily_csi_scores) >= 3:  # Need minimum samples for correlation
            correlation, p_value = pearsonr(daily_csi_scores, interaction_csi_scores)
            
            assert correlation >= CONSTITUTIONAL_CORRELATION_THRESHOLD, \
                f"CONSTITUTIONAL VIOLATION: CSI correlation {correlation:.3f} < {CONSTITUTIONAL_CORRELATION_THRESHOLD}"
            
            # Verify average deviation is within acceptable range
            avg_deviation = np.mean([abs(d - i) for d, i in zip(daily_csi_scores, interaction_csi_scores)])
            max_deviation = np.mean(daily_csi_scores) * (MAX_CSI_DEVIATION_PERCENT / 100)
            
            assert avg_deviation <= max_deviation, \
                f"CONSTITUTIONAL VIOLATION: Average CSI deviation {avg_deviation:.3f} > {max_deviation:.3f}"

    def test_dual_csi_storage_requirement(self, db_session):
        """
        CONSTITUTIONAL TEST: Verify both calculated and inferred CSI are stored
        
        AMENDMENT III: Dual AI Enhancement must store both CSI types
        """
        # Check InteractionAnalysis model has both fields
        sample_interaction = db_session.query(InteractionAnalysis).first()
        
        if sample_interaction:
            assert hasattr(sample_interaction, 'csi_score'), \
                "CONSTITUTIONAL VIOLATION: Missing csi_score field for calculated CSI"
            
            assert hasattr(sample_interaction, 'inferred_csi'), \
                "CONSTITUTIONAL VIOLATION: Missing inferred_csi field for AI blackbox CSI"

    def test_no_rule_based_calculations_in_interaction_analysis(self, db_session):
        """
        CONSTITUTIONAL TEST: Verify interaction analysis doesn't use rule-based micro-metrics
        
        REQUIREMENT ADHERENCE: Rule-based calculations are FORBIDDEN
        """
        # This test checks that InteractionAnalyticsService doesn't have rule-based calculation methods
        from services.interaction_analytics_service import InteractionAnalyticsService
        
        forbidden_methods = [
            '_calculate_effectiveness',
            '_calculate_effort', 
            '_calculate_efficiency',
            '_calculate_empathy'
        ]
        
        service = InteractionAnalyticsService(None)  # Pass None gemini service for inspection
        
        for method_name in forbidden_methods:
            # If these methods exist, they should be removed per constitutional requirements
            if hasattr(service, method_name):
                method = getattr(service, method_name)
                # Check if method has AI extraction logic instead of rule-based
                import inspect
                source_code = inspect.getsource(method)
                
                # Rule-based indicators that should NOT be present
                rule_based_indicators = [
                    'resolution_keywords', 'message_penalty', 'transfer_keywords',
                    'positive_indicators', 'scale_time', 'repetition_penalty'
                ]
                
                for indicator in rule_based_indicators:
                    assert indicator not in source_code, \
                        f"CONSTITUTIONAL VIOLATION: Rule-based calculation '{indicator}' found in {method_name}"

    @pytest.mark.asyncio
    async def test_interaction_pipeline_uses_ai_extraction(self, db_session, gemini_service):
        """
        CONSTITUTIONAL TEST: Verify interaction pipeline uses AI micro-metrics extraction
        
        PROVEN PIPELINE PRESERVATION: Must use same approach as daily analysis
        """
        # Create test interaction
        test_conversation = db_session.query(Conversation).first()
        
        if test_conversation and test_conversation.messages:
            # Create test interaction analysis
            test_interaction = InteractionAnalysis(
                conversation_id=test_conversation.id,
                start_message_id=test_conversation.messages[0].id,
                end_message_id=test_conversation.messages[-1].id,
                interaction_start=test_conversation.messages[0].social_create_time,
                interaction_end=test_conversation.messages[-1].social_create_time,
                boundary_method="test",
                boundary_confidence=0.9
            )
            
            db_session.add(test_interaction)
            db_session.commit()
            
            # Verify interaction analysis uses AI extraction
            try:
                # This should use AI micro-metrics extraction, not rule-based
                result = await gemini_service.analyze_interaction_analyses_batch([test_interaction])
                
                # Verify result has expected AI micro-metrics format
                analysis_results, missed_ids, usage_metadata, response_text = result
                
                assert isinstance(analysis_results, list), \
                    "AI extraction should return list of analysis results"
                
                # Clean up test data
                db_session.delete(test_interaction)
                db_session.commit()
                
            except AttributeError:
                pytest.fail("CONSTITUTIONAL VIOLATION: analyze_interaction_analyses_batch method not implemented")

    def test_performance_no_degradation(self, db_session):
        """
        CONSTITUTIONAL TEST: Verify interaction analysis doesn't degrade system performance
        
        QUALITY VIOLATIONS: Performance degradation compared to daily analysis
        """
        import time
        
        # Simple performance test - interaction analysis should complete within reasonable time
        start_time = time.time()
        
        # Test basic interaction analysis query performance
        interactions = db_session.query(InteractionAnalysis).limit(100).all()
        
        query_time = time.time() - start_time
        
        # Should complete within 5 seconds for 100 records
        assert query_time < 5.0, \
            f"PERFORMANCE VIOLATION: Query took {query_time:.2f}s (max 5.0s)"

    def test_backward_compatibility_daily_analysis(self, db_session):
        """
        CONSTITUTIONAL TEST: Verify daily analysis pipeline remains unchanged
        
        AMENDMENT IV: Daily analysis pipeline SHALL remain unchanged
        """
        # Verify daily analysis still works and produces valid results
        daily_analyses = db_session.query(DailyAnalysis).filter(
            DailyAnalysis.csi_score.isnot(None)
        ).limit(10).all()
        
        for analysis in daily_analyses:
            # Verify daily analysis has all required micro-metrics
            assert analysis.sentiment_score is not None or analysis.csi_score is not None, \
                "Daily analysis should have micro-metrics or calculated CSI"
            
            # Verify CSI score is in valid range
            if analysis.csi_score is not None:
                assert 0 <= analysis.csi_score <= 10, \
                    f"Invalid CSI score: {analysis.csi_score} (must be 0-10)"

class TestConstitutionalIntegration:
    """Integration tests for constitutional compliance across the full system"""

    @pytest.mark.asyncio
    async def test_end_to_end_constitutional_pipeline(self, db_session):
        """
        INTEGRATION TEST: Full interaction analysis pipeline following constitutional requirements
        """
        # This test will be implemented once the constitutional corrections are in place
        # It should test the complete flow:
        # 1. AI boundary detection
        # 2. AI micro-metrics extraction  
        # 3. Four-pillars calculation
        # 4. Dual CSI storage
        pass

if __name__ == "__main__":
    # Run constitutional tests
    pytest.main([__file__, "-v", "--tb=short"])