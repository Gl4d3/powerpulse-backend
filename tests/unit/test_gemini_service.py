"""
Unit tests for the refactored GeminiService, focusing on CSI score generation.
"""
import pytest
import json
from unittest.mock import Mock, patch, AsyncMock

from services.gemini_service import GeminiService
from models import Conversation, Message

@pytest.fixture
def gemini_service():
    """Create a GeminiService instance for testing."""
    return GeminiService(api_key="test-api-key")

@pytest.fixture
def sample_conversations():
    """Create sample Conversation objects for testing."""
    conv1 = Conversation(id=1, fb_chat_id="chat1")
    conv1.messages = [
        Message(direction="to_company", message_content="Hello, I have an issue."),
        Message(direction="to_client", message_content="Hi, how can I help?")
    ]

    conv2 = Conversation(id=2, fb_chat_id="chat2")
    conv2.messages = [
        Message(direction="to_company", message_content="My order is late."),
        Message(direction="to_client", message_content="I can check on that for you.")
    ]
    return [conv1, conv2]

def test_create_batch_prompt(gemini_service, sample_conversations):
    """Test that the batch prompt is created with the correct structure and content."""
    prompt = gemini_service._create_batch_prompt(sample_conversations)

    assert "Analyze the following batch" in prompt
    assert "CONVERSATIONS_BATCH:" in prompt
    assert "chat1" in prompt
    assert "My order is late" in prompt
    assert "effectiveness_score" in prompt
    assert "empathy_score" in prompt

def test_parse_batch_response_success(gemini_service, sample_conversations):
    """Test successful parsing of a valid JSON response from the AI."""
    mock_response = json.dumps([
        {
            "chat_id": "chat1",
            "conversation_analysis": {
                "effectiveness_score": 8.5,
                "efficiency_score": 9.0,
                "effort_score": 7.5,
                "empathy_score": 9.5,
                "common_topics": ["issue resolution"]
            }
        },
        {
            "chat_id": "chat2",
            "conversation_analysis": {
                "effectiveness_score": 5.0,
                "efficiency_score": 6.0,
                "effort_score": 7.0,
                "empathy_score": 8.0,
                "common_topics": ["order status"]
            }
        }
    ])

    results = gemini_service._parse_batch_response(mock_response, sample_conversations)

    assert len(results) == 2
    assert results[0]['id'] == 1
    assert results[0]['effectiveness_score'] == 8.5
    assert results[1]['chat_id'] == "chat2"
    assert results[1]['empathy_score'] == 8.0

def test_parse_batch_response_with_missing_conversation(gemini_service, sample_conversations):
    """Test that a fallback is created if a conversation from the original batch is missing in the response."""
    mock_response = json.dumps([
        {
            "chat_id": "chat1", # Only chat1 is in the response
            "conversation_analysis": {
                "effectiveness_score": 8.5,
                "efficiency_score": 9.0,
                "effort_score": 7.5,
                "empathy_score": 9.5,
                "common_topics": ["issue resolution"]
            }
        }
    ])

    results = gemini_service._parse_batch_response(mock_response, sample_conversations)

    assert len(results) == 2
    assert results[0]['effectiveness_score'] == 8.5
    # Check that the second result is a fallback
    assert results[1]['chat_id'] == "chat2"
    assert results[1]['effectiveness_score'] == 5.0 # Fallback value

def test_parse_batch_response_invalid_json(gemini_service, sample_conversations):
    """Test that fallbacks are returned for all conversations if the JSON is invalid."""
    invalid_response = "This is not valid JSON."

    results = gemini_service._parse_batch_response(invalid_response, sample_conversations)

    assert len(results) == 2
    assert results[0]['chat_id'] == "chat1"
    assert results[0]['empathy_score'] == 5.0 # Fallback value
    assert results[1]['chat_id'] == "chat2"
    assert results[1]['empathy_score'] == 5.0 # Fallback value

def test_create_fallback_result(gemini_service):
    """Test the creation of a fallback result for a single conversation."""
    conv = Conversation(id=10, fb_chat_id="fallback_chat")
    fallback = gemini_service._create_fallback_result(conv)

    assert fallback['id'] == 10
    assert fallback['chat_id'] == "fallback_chat"
    assert fallback['effectiveness_score'] == 5.0
    assert fallback['efficiency_score'] == 5.0
    assert fallback['effort_score'] == 5.0
    assert fallback['empathy_score'] == 5.0
    assert fallback['common_topics'] == ['analysis_failed']

@pytest.mark.asyncio
async def test_analyze_conversations_batch_e2e_success(gemini_service, sample_conversations):
    """E2E test for the main batch analysis function, mocking the AI call."""
    mock_response_text = json.dumps([
        {
            "chat_id": "chat1",
            "conversation_analysis": {"effectiveness_score": 8, "efficiency_score": 9, "effort_score": 7, "empathy_score": 9, "common_topics": []}
        },
        {
            "chat_id": "chat2",
            "conversation_analysis": {"effectiveness_score": 5, "efficiency_score": 6, "effort_score": 7, "empathy_score": 8, "common_topics": []}
        }
    ])

    with patch.object(gemini_service, '_call_gemini_with_retry', new_callable=AsyncMock) as mock_ai_call:
        mock_ai_call.return_value = mock_response_text

        results = await gemini_service.analyze_conversations_batch(sample_conversations)

        mock_ai_call.assert_called_once()
        assert len(results) == 2
        assert results[0]['effectiveness_score'] == 8
        assert results[1]['chat_id'] == "chat2"

@pytest.mark.asyncio
async def test_analyze_conversations_batch_e2e_failure(gemini_service, sample_conversations):
    """Test that the main batch analysis function returns fallbacks if the AI call fails."""
    with patch.object(gemini_service, '_call_gemini_with_retry', new_callable=AsyncMock) as mock_ai_call:
        mock_ai_call.side_effect = Exception("Fatal AI Error")

        results = await gemini_service.analyze_conversations_batch(sample_conversations)

        mock_ai_call.assert_called_once()
        assert len(results) == 2
        assert results[0]['chat_id'] == "chat1"
        assert results[0]['effectiveness_score'] == 5.0 # Fallback value
        assert results[1]['chat_id'] == "chat2"
        assert results[1]['empathy_score'] == 5.0 # Fallback value