"""
Unit tests for metrics calculation functionality.
"""
import pytest
from datetime import datetime, date
from unittest.mock import Mock, patch
from services.analytics_service import AnalyticsService
from models import Conversation, Message, Metric


class TestMetricsCalculation:
    """Test metrics calculation functionality."""
    
    @pytest.fixture
    def analytics_service(self):
        """Create analytics service instance for testing."""
        return AnalyticsService()
    
    @pytest.fixture
    def sample_conversations(self, test_db_session):
        """Create sample conversations for testing."""
        conversations = []
        
        # Satisfied conversation
        conv1 = Conversation(
            fb_chat_id="CHAT_001",
            is_satisfied=True,
            satisfaction_score=5.0,
            first_contact_resolution=True,
            avg_response_time_minutes=2.5,
            common_topics=["billing"],
            first_message_time=datetime.now(),
            last_message_time=datetime.now()
        )
        
        # Unsatisfied conversation
        conv2 = Conversation(
            fb_chat_id="CHAT_002",
            is_satisfied=False,
            satisfaction_score=2.0,
            first_contact_resolution=False,
            avg_response_time_minutes=15.0,
            common_topics=["technical issue"],
            first_message_time=datetime.now(),
            last_message_time=datetime.now()
        )
        
        # Neutral conversation
        conv3 = Conversation(
            fb_chat_id="CHAT_003",
            is_satisfied=False,
            satisfaction_score=3.0,
            first_contact_resolution=True,
            avg_response_time_minutes=8.0,
            common_topics=["order status"],
            first_message_time=datetime.now(),
            last_message_time=datetime.now()
        )
        
        test_db_session.add_all([conv1, conv2, conv3])
        test_db_session.commit()
        
        return [conv1, conv2, conv3]
    
    def test_csat_percentage_calculation(self, analytics_service, test_db_session, sample_conversations):
        """Test CSAT percentage calculation."""
        metrics = analytics_service.calculate_and_cache_metrics(test_db_session)
        
        # 1 out of 3 conversations satisfied = 33.33%
        assert metrics['csat_percentage'] == pytest.approx(33.33, rel=1e-2)
    
    def test_fcr_percentage_calculation(self, analytics_service, test_db_session, sample_conversations):
        """Test FCR percentage calculation."""
        metrics = analytics_service.calculate_and_cache_metrics(test_db_session)
        
        # 2 out of 3 conversations resolved on first contact = 66.67%
        assert metrics['fcr_percentage'] == pytest.approx(66.67, rel=1e-2)
    
    def test_average_response_time_calculation(self, analytics_service, test_db_session, sample_conversations):
        """Test average response time calculation."""
        metrics = analytics_service.calculate_and_cache_metrics(test_db_session)
        
        # Average of 2.5, 15.0, 8.0 = 8.5 minutes
        assert metrics['avg_response_time_minutes'] == pytest.approx(8.5, rel=1e-2)
    
    def test_topic_extraction_and_counting(self, analytics_service, test_db_session, sample_conversations):
        """Test topic extraction and counting."""
        metrics = analytics_service.calculate_and_cache_metrics(test_db_session)
        
        topics = metrics['most_common_topics']
        
        # Should have 3 topics
        assert len(topics) == 3
        
        # Check topic percentages
        topic_dict = {t['topic']: t['percentage'] for t in topics}
        assert topic_dict['billing'] == pytest.approx(33.3, rel=1e-1)
        assert topic_dict['technical issue'] == pytest.approx(33.3, rel=1e-1)
        assert topic_dict['order status'] == pytest.approx(33.3, rel=1e-1)
    
    def test_empty_database_metrics(self, analytics_service, test_db_session):
        """Test metrics calculation with empty database."""
        metrics = analytics_service.calculate_and_cache_metrics(test_db_session)
        
        assert metrics['csat_percentage'] == 0.0
        assert metrics['fcr_percentage'] == 0.0
        assert metrics['avg_response_time_minutes'] == 0.0
        assert metrics['total_conversations'] == 0
        assert metrics['total_messages'] == 0
        assert metrics['most_common_topics'] == []
    
    def test_date_filtered_metrics(self, analytics_service, test_db_session, sample_conversations):
        """Test metrics calculation with date filtering."""
        # Test with date range
        start_date = date.today()
        end_date = date.today()
        
        metrics = analytics_service.calculate_metrics_with_date_filter(
            test_db_session, start_date, end_date
        )
        
        # Should include conversations from today
        assert metrics['total_conversations'] == 3
    
    def test_metrics_caching(self, analytics_service, test_db_session, sample_conversations):
        """Test metrics caching functionality."""
        # Calculate metrics first time
        metrics1 = analytics_service.calculate_and_cache_metrics(test_db_session)
        
        # Get cached metrics
        metrics2 = analytics_service.get_cached_metrics(test_db_session)
        
        # Should be the same
        assert metrics1['csat_percentage'] == metrics2['csat_percentage']
        assert metrics1['fcr_percentage'] == metrics2['fcr_percentage']
    
    def test_metrics_update_on_new_data(self, analytics_service, test_db_session, sample_conversations):
        """Test metrics update when new data is added."""
        # Get initial metrics
        initial_metrics = analytics_service.calculate_and_cache_metrics(test_db_session)
        
        # Add new satisfied conversation
        new_conv = Conversation(
            fb_chat_id="CHAT_004",
            is_satisfied=True,
            satisfaction_score=5.0,
            first_contact_resolution=True,
            avg_response_time_minutes=1.0,
            common_topics=["excellent service"],
            first_message_time=datetime.now(),
            last_message_time=datetime.now()
        )
        
        test_db_session.add(new_conv)
        test_db_session.commit()
        
        # Recalculate metrics
        updated_metrics = analytics_service.calculate_and_cache_metrics(test_db_session)
        
        # CSAT should increase: 2 out of 4 = 50%
        assert updated_metrics['csat_percentage'] == 50.0
        
        # FCR should increase: 3 out of 4 = 75%
        assert updated_metrics['fcr_percentage'] == 75.0


class TestMetricsEdgeCases:
    """Test edge cases in metrics calculation."""
    
    def test_null_values_handling(self, analytics_service, test_db_session):
        """Test handling of null values in metrics calculation."""
        # Create conversation with null values
        conv = Conversation(
            fb_chat_id="CHAT_NULL",
            is_satisfied=None,
            satisfaction_score=None,
            first_contact_resolution=None,
            avg_response_time_minutes=None,
            common_topics=None,
            first_message_time=datetime.now(),
            last_message_time=datetime.now()
        )
        
        test_db_session.add(conv)
        test_db_session.commit()
        
        metrics = analytics_service.calculate_and_cache_metrics(test_db_session)
        
        # Should handle nulls gracefully
        assert metrics['total_conversations'] == 1
        assert metrics['csat_percentage'] == 0.0  # null is_satisfied counts as False
    
    def test_extreme_values_handling(self, analytics_service, test_db_session):
        """Test handling of extreme values."""
        # Create conversation with extreme response time
        conv = Conversation(
            fb_chat_id="CHAT_EXTREME",
            is_satisfied=False,
            satisfaction_score=1.0,
            first_contact_resolution=False,
            avg_response_time_minutes=999.0,  # Very high response time
            common_topics=["urgent issue"],
            first_message_time=datetime.now(),
            last_message_time=datetime.now()
        )
        
        test_db_session.add(conv)
        test_db_session.commit()
        
        metrics = analytics_service.calculate_and_cache_metrics(test_db_session)
        
        # Should handle extreme values
        assert metrics['avg_response_time_minutes'] == 999.0
        assert metrics['csat_percentage'] == 0.0
        assert metrics['fcr_percentage'] == 0.0


class TestTopicAnalysis:
    """Test topic analysis functionality."""
    
    def test_topic_extraction_from_conversations(self, analytics_service):
        """Test topic extraction from conversation objects."""
        conversations = [
            Mock(common_topics=["billing", "payment"]),
            Mock(common_topics=["technical support", "billing"]),
            Mock(common_topics=["order status"]),
            Mock(common_topics=None),  # Test null handling
            Mock(common_topics=[]),    # Test empty list
        ]
        
        topics = analytics_service._extract_topics_from_conversations(conversations)
        
        # billing appears 2 times, others 1 time each
        assert len(topics) == 3
        
        billing_topic = next(t for t in topics if t['topic'] == 'billing')
        assert billing_topic['count'] == 2
        assert billing_topic['percentage'] == pytest.approx(40.0, rel=1e-1)
    
    def test_topic_cleaning_and_normalization(self, analytics_service):
        """Test topic cleaning and normalization."""
        conversations = [
            Mock(common_topics=["  BILLING  ", "Technical Support", "billing", "BILLING"]),
        ]
        
        topics = analytics_service._extract_topics_from_conversations(conversations)
        
        # Should normalize and deduplicate
        assert len(topics) == 2  # billing and technical support
        
        billing_topic = next(t for t in topics if t['topic'] == 'billing')
        assert billing_topic['count'] == 3  # 3 instances of billing
        assert billing_topic['percentage'] == 100.0
