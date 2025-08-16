"""
Unit tests for PowerPulse Analytics database models.
"""
import pytest
from datetime import datetime
from sqlalchemy.orm import Session

from models import Conversation, Message, ProcessedChat, Metric


class TestConversationModel:
    """Test Conversation model functionality."""
    
    def test_create_conversation(self, test_db_session: Session):
        """Test creating a new conversation."""
        conversation = Conversation(
            chat_id="TEST_CHAT_001",
            first_message_time=datetime.now(),
            last_message_time=datetime.now(),
            message_count=3,
            sentiment_score=0.8,
            satisfaction_score=5,
            is_resolved=True,
            topics=["customer service", "satisfaction"]
        )
        
        test_db_session.add(conversation)
        test_db_session.commit()
        
        assert conversation.id is not None
        assert conversation.chat_id == "TEST_CHAT_001"
        assert conversation.sentiment_score == 0.8
        assert conversation.satisfaction_score == 5
        assert conversation.is_resolved is True
        assert "customer service" in conversation.topics
    
    def test_conversation_relationships(self, test_db_session: Session):
        """Test conversation relationships with messages."""
        # Create conversation
        conversation = Conversation(
            chat_id="TEST_CHAT_002",
            first_message_time=datetime.now(),
            last_message_time=datetime.now(),
            message_count=2,
            sentiment_score=0.5,
            satisfaction_score=3
        )
        test_db_session.add(conversation)
        test_db_session.commit()
        
        # Create messages
        message1 = Message(
            conversation_id=conversation.id,
            content="Hello, I need help",
            direction="to_company",
            timestamp=datetime.now(),
            agent_username=None
        )
        
        message2 = Message(
            conversation_id=conversation.id,
            content="Hi! How can I help you?",
            direction="to_client",
            timestamp=datetime.now(),
            agent_username="AGENT_001"
        )
        
        test_db_session.add_all([message1, message2])
        test_db_session.commit()
        
        # Test relationships
        assert len(conversation.messages) == 2
        assert conversation.messages[0].content == "Hello, I need help"
        assert conversation.messages[1].agent_username == "AGENT_001"


class TestMessageModel:
    """Test Message model functionality."""
    
    def test_create_message(self, test_db_session: Session):
        """Test creating a new message."""
        message = Message(
            conversation_id=1,
            content="Test message content",
            direction="to_company",
            timestamp=datetime.now(),
            agent_username=None,
            sentiment="neutral",
            sentiment_score=0.0
        )
        
        test_db_session.add(message)
        test_db_session.commit()
        
        assert message.id is not None
        assert message.content == "Test message content"
        assert message.direction == "to_company"
        assert message.sentiment == "neutral"
        assert message.sentiment_score == 0.0
    
    def test_message_validation(self, test_db_session: Session):
        """Test message validation rules."""
        # Test required fields
        with pytest.raises(Exception):  # SQLAlchemy will raise for required fields
            message = Message()
            test_db_session.add(message)
            test_db_session.commit()


class TestProcessedChatModel:
    """Test ProcessedChat model functionality."""
    
    def test_create_processed_chat(self, test_db_session: Session):
        """Test creating a processed chat record."""
        processed_chat = ProcessedChat(
            chat_id="PROCESSED_CHAT_001",
            processed_at=datetime.now(),
            status="completed",
            message_count=5
        )
        
        test_db_session.add(processed_chat)
        test_db_session.commit()
        
        assert processed_chat.id is not None
        assert processed_chat.chat_id == "PROCESSED_CHAT_001"
        assert processed_chat.status == "completed"
        assert processed_chat.message_count == 5


class TestMetricModel:
    """Test Metric model functionality."""
    
    def test_create_metric(self, test_db_session: Session):
        """Test creating a metric record."""
        metric = Metric(
            metric_name="csat_percentage",
            metric_value=85.5,
            calculated_at=datetime.now(),
            data_source="conversations"
        )
        
        test_db_session.add(metric)
        test_db_session.commit()
        
        assert metric.id is not None
        assert metric.metric_name == "csat_percentage"
        assert metric.metric_value == 85.5
        assert metric.data_source == "conversations"
    
    def test_metric_caching(self, test_db_session: Session):
        """Test metric caching functionality."""
        # Create multiple metrics with same name but different timestamps
        metric1 = Metric(
            metric_name="fcr_rate",
            metric_value=78.0,
            calculated_at=datetime.now(),
            data_source="conversations"
        )
        
        metric2 = Metric(
            metric_name="fcr_rate",
            metric_value=79.0,
            calculated_at=datetime.now(),
            data_source="conversations"
        )
        
        test_db_session.add_all([metric1, metric2])
        test_db_session.commit()
        
        # Should be able to store multiple values for same metric
        assert metric1.id != metric2.id
        assert metric1.metric_name == metric2.metric_name
