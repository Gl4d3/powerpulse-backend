"""
Test helper utilities for PowerPulse Analytics tests.
"""
import json
import tempfile
from pathlib import Path
from typing import Dict, Any
from fastapi.testclient import TestClient


def create_test_file(data: Dict[str, Any], filename: str = "test_data.json") -> Path:
    """Create a temporary test file with the given data."""
    temp_dir = Path(tempfile.mkdtemp())
    file_path = temp_dir / filename
    
    with open(file_path, 'w') as f:
        json.dump(data, f)
    
    return file_path


def create_mock_gpt_response(
    sentiment: str = "positive",
    sentiment_score: float = 0.8,
    satisfaction_score: int = 5,
    topics: list = None,
    is_resolved: bool = True
) -> Dict[str, Any]:
    """Create a mock GPT API response for testing."""
    if topics is None:
        topics = ["customer service", "satisfaction"]
    
    return {
        "sentiment": sentiment,
        "sentiment_score": sentiment_score,
        "satisfaction_score": satisfaction_score,
        "topics": topics,
        "is_resolved": is_resolved,
        "resolution_quality": "excellent" if is_resolved else "poor"
    }


def create_sample_conversation_data(
    chat_id: str = "TEST_CHAT_001",
    message_count: int = 3,
    sentiment: str = "positive"
) -> Dict[str, Any]:
    """Create sample conversation data for testing."""
    messages = []
    
    # Add customer message
    messages.append({
        "FB_CHAT_ID": chat_id,
        "MESSAGE_CONTENT": f"Hello, I have a {sentiment} experience to share",
        "DIRECTION": "to_company",
        "SOCIAL_CREATE_TIME": "2025-01-15T10:00:00.000Z",
        "AGENT_USERNAME": None,
        "AGENT_EMAIL": None
    })
    
    # Add agent response
    messages.append({
        "FB_CHAT_ID": chat_id,
        "MESSAGE_CONTENT": "Hi! I'd be happy to help you.",
        "DIRECTION": "to_client",
        "SOCIAL_CREATE_TIME": "2025-01-15T10:01:00.000Z",
        "AGENT_USERNAME": "AGENT_001",
        "AGENT_EMAIL": "agent1@company.com"
    })
    
    # Add customer follow-up if more messages needed
    if message_count > 2:
        messages.append({
            "FB_CHAT_ID": chat_id,
            "MESSAGE_CONTENT": "Thank you for your help!",
            "DIRECTION": "to_company",
            "SOCIAL_CREATE_TIME": "2025-01-15T10:02:00.000Z",
            "AGENT_USERNAME": None,
            "AGENT_EMAIL": None
        })
    
    return {chat_id: messages}


def assert_conversation_structure(response_data: Dict[str, Any]):
    """Assert that the response has the correct conversation structure."""
    assert "id" in response_data
    assert "chat_id" in response_data
    assert "first_message_time" in response_data
    assert "last_message_time" in response_data
    assert "message_count" in response_data
    assert "sentiment_score" in response_data
    assert "satisfaction_score" in response_data
    assert "is_resolved" in response_data
    assert "topics" in response_data
    assert "created_at" in response_data
    assert "updated_at" in response_data


def assert_message_structure(response_data: Dict[str, Any]):
    """Assert that the response has the correct message structure."""
    assert "id" in response_data
    assert "conversation_id" in response_data
    assert "content" in response_data
    assert "direction" in response_data
    assert "timestamp" in response_data
    assert "agent_username" in response_data
    assert "agent_email" in response_data
    assert "sentiment" in response_data
    assert "sentiment_score" in response_data
    assert "created_at" in response_data


def assert_metrics_structure(response_data: Dict[str, Any]):
    """Assert that the response has the correct metrics structure."""
    assert "total_conversations" in response_data
    assert "satisfied_conversations" in response_data
    assert "csat_percentage" in response_data
    assert "fcr_rate" in response_data
    assert "avg_response_time" in response_data
    assert "sentiment_distribution" in response_data
    assert "top_topics" in response_data
    assert "calculated_at" in response_data


def assert_upload_response_structure(response_data: Dict[str, Any]):
    """Assert that the response has the correct upload response structure."""
    assert "success" in response_data
    assert "message" in response_data
    assert "conversations_processed" in response_data
    assert "messages_processed" in response_data
    assert "processing_time_seconds" in response_data
    assert "upload_id" in response_data


def assert_progress_response_structure(response_data: Dict[str, Any]):
    """Assert that the response has the correct progress response structure."""
    assert "upload_id" in response_data
    assert "status" in response_data
    assert "progress_percentage" in response_data
    assert "conversations_processed" in response_data
    assert "total_conversations" in response_data
    assert "current_stage" in response_data
    assert "started_at" in response_data


def create_large_test_dataset(conversation_count: int = 100) -> Dict[str, Any]:
    """Create a large test dataset for performance testing."""
    dataset = {}
    
    for i in range(conversation_count):
        chat_id = f"PERF_TEST_CHAT_{i:03d}"
        dataset[chat_id] = create_sample_conversation_data(
            chat_id=chat_id,
            message_count=3,
            sentiment="positive" if i % 3 == 0 else "neutral" if i % 3 == 1 else "negative"
        )[chat_id]
    
    return dataset
