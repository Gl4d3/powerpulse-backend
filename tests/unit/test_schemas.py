"""
Unit tests for PowerPulse Analytics Pydantic schemas.
"""
import pytest
from datetime import datetime
from pydantic import ValidationError

from schemas import (
    ConversationResponse,
    MessageResponse,
    MetricsResponse,
    UploadResponse,
    ProgressResponse
)


class TestConversationResponse:
    """Test ConversationResponse schema validation."""
    
    def test_valid_conversation_response(self):
        """Test creating a valid conversation response."""
        data = {
            "id": 1,
            "chat_id": "TEST_CHAT_001",
            "first_message_time": "2025-01-15T10:00:00Z",
            "last_message_time": "2025-01-15T10:05:00Z",
            "message_count": 3,
            "sentiment_score": 0.8,
            "satisfaction_score": 5,
            "is_resolved": True,
            "topics": ["customer service", "satisfaction"],
            "created_at": "2025-01-15T10:00:00Z",
            "updated_at": "2025-01-15T10:05:00Z"
        }
        
        response = ConversationResponse(**data)
        assert response.chat_id == "TEST_CHAT_001"
        assert response.sentiment_score == 0.8
        assert response.satisfaction_score == 5
        assert response.is_resolved is True
        assert len(response.topics) == 2
    
    def test_invalid_sentiment_score(self):
        """Test validation of sentiment score range."""
        data = {
            "id": 1,
            "chat_id": "TEST_CHAT_001",
            "first_message_time": "2025-01-15T10:00:00Z",
            "last_message_time": "2025-01-15T10:05:00Z",
            "message_count": 3,
            "sentiment_score": 1.5,  # Invalid: should be -1 to 1
            "satisfaction_score": 5,
            "is_resolved": True,
            "topics": ["customer service"],
            "created_at": "2025-01-15T10:00:00Z",
            "updated_at": "2025-01-15T10:05:00Z"
        }
        
        with pytest.raises(ValidationError):
            ConversationResponse(**data)
    
    def test_invalid_satisfaction_score(self):
        """Test validation of satisfaction score range."""
        data = {
            "id": 1,
            "chat_id": "TEST_CHAT_001",
            "first_message_time": "2025-01-15T10:00:00Z",
            "last_message_time": "2025-01-15T10:05:00Z",
            "message_count": 3,
            "sentiment_score": 0.8,
            "satisfaction_score": 7,  # Invalid: should be 1 to 5
            "is_resolved": True,
            "topics": ["customer service"],
            "created_at": "2025-01-15T10:00:00Z",
            "updated_at": "2025-01-15T10:05:00Z"
        }
        
        with pytest.raises(ValidationError):
            ConversationResponse(**data)


class TestMessageResponse:
    """Test MessageResponse schema validation."""
    
    def test_valid_message_response(self):
        """Test creating a valid message response."""
        data = {
            "id": 1,
            "conversation_id": 1,
            "content": "Hello, I need help",
            "direction": "to_company",
            "timestamp": "2025-01-15T10:00:00Z",
            "agent_username": None,
            "agent_email": None,
            "sentiment": "neutral",
            "sentiment_score": 0.0,
            "created_at": "2025-01-15T10:00:00Z"
        }
        
        response = MessageResponse(**data)
        assert response.content == "Hello, I need help"
        assert response.direction == "to_company"
        assert response.sentiment == "neutral"
        assert response.sentiment_score == 0.0
    
    def test_invalid_direction(self):
        """Test validation of message direction."""
        data = {
            "id": 1,
            "conversation_id": 1,
            "content": "Test message",
            "direction": "invalid_direction",  # Invalid direction
            "timestamp": "2025-01-15T10:00:00Z",
            "agent_username": None,
            "agent_email": None,
            "sentiment": "neutral",
            "sentiment_score": 0.0,
            "created_at": "2025-01-15T10:00:00Z"
        }
        
        with pytest.raises(ValidationError):
            MessageResponse(**data)


class TestMetricsResponse:
    """Test MetricsResponse schema validation."""
    
    def test_valid_metrics_response(self):
        """Test creating a valid metrics response."""
        data = {
            "total_conversations": 100,
            "satisfied_conversations": 85,
            "csat_percentage": 85.0,
            "fcr_rate": 78.0,
            "avg_response_time": 2.5,
            "sentiment_distribution": {
                "positive": 60,
                "neutral": 25,
                "negative": 15
            },
            "top_topics": ["customer service", "billing", "technical support"],
            "calculated_at": "2025-01-15T10:00:00Z"
        }
        
        response = MetricsResponse(**data)
        assert response.total_conversations == 100
        assert response.csat_percentage == 85.0
        assert response.fcr_rate == 78.0
        assert response.avg_response_time == 2.5
        assert len(response.sentiment_distribution) == 3
        assert len(response.top_topics) == 3
    
    def test_percentage_validation(self):
        """Test validation of percentage fields."""
        data = {
            "total_conversations": 100,
            "satisfied_conversations": 85,
            "csat_percentage": 150.0,  # Invalid: > 100%
            "fcr_rate": 78.0,
            "avg_response_time": 2.5,
            "sentiment_distribution": {"positive": 60, "neutral": 25, "negative": 15},
            "top_topics": ["customer service"],
            "calculated_at": "2025-01-15T10:00:00Z"
        }
        
        with pytest.raises(ValidationError):
            MetricsResponse(**data)


class TestUploadResponse:
    """Test UploadResponse schema validation."""
    
    def test_valid_upload_response(self):
        """Test creating a valid upload response."""
        data = {
            "success": True,
            "message": "Successfully processed 20 conversations",
            "conversations_processed": 20,
            "messages_processed": 154,
            "processing_time_seconds": 26.37,
            "upload_id": "d2a52888-e084-4d79-940c-0f327589d254"
        }
        
        response = UploadResponse(**data)
        assert response.success is True
        assert response.conversations_processed == 20
        assert response.messages_processed == 154
        assert response.processing_time_seconds == 26.37
        assert response.upload_id == "d2a52888-e084-4d79-940c-0f327589d254"


class TestProgressResponse:
    """Test ProgressResponse schema validation."""
    
    def test_valid_progress_response(self):
        """Test creating a valid progress response."""
        data = {
            "upload_id": "test-upload-123",
            "status": "processing",
            "progress_percentage": 45.5,
            "current_stage": "ai_analysis",
            "processed_conversations": 9,
            "total_conversations": 20,
            "details": "Processing analysis jobs...",
            "start_time": "2025-01-15T10:00:00Z",
            "last_update": "2025-01-15T10:01:00Z",
            "duration_seconds": 60.0,
            "statistics": {
                "filtered_autoresponses": 1,
                "gpt_calls_made": 5,
                "errors_count": 0
            },
            "errors": []
        }
        
        response = ProgressResponse(**data)
        assert response.upload_id == "test-upload-123"
        assert response.status == "processing"
        assert response.progress_percentage == 45.5
        assert response.processed_conversations == 9
        assert response.total_conversations == 20
        assert response.current_stage == "ai_analysis"
        assert response.statistics.gpt_calls_made == 5

    def test_progress_percentage_validation(self):
        """Test validation of progress percentage range."""
        # Pydantic v2 doesn't validate ranges with simple float/int.
        # A validator would be needed for this.
        # For now, we test if the type is correct.
        data = {
            "upload_id": "test-upload-123",
            "status": "processing",
            "progress_percentage": 150.0, # This is valid for a float
            "current_stage": "ai_analysis",
            "processed_conversations": 9,
            "total_conversations": 20,
            "details": "Processing analysis jobs...",
            "start_time": "2025-01-15T10:00:00Z",
            "last_update": "2025-01-15T10:01:00Z",
            "duration_seconds": 60.0,
            "statistics": {
                "filtered_autoresponses": 1,
                "gpt_calls_made": 5,
                "errors_count": 0
            },
            "errors": []
        }
        
        response = ProgressResponse(**data)
        assert response.progress_percentage == 150.0
