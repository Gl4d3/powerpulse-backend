"""
Unit tests for Gemini service functionality.
"""
import pytest
import sys
import os
from unittest.mock import Mock, patch, AsyncMock

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from services.gemini_service import GeminiService


class TestGeminiService:
    """Test Gemini service functionality."""
    
    @pytest.fixture
    def gemini_service(self):
        """Create Gemini service instance for testing."""
        return GeminiService("test-api-key")
    
    @pytest.fixture
    def sample_conversation(self):
        """Sample conversation data for testing."""
        return {
            'chat_id': 'test_chat_123',
            'messages': [
                {
                    'message_content': 'Hello, I have a billing issue',
                    'direction': 'to_company',
                    'social_create_time': '2025-08-16T10:00:00Z'
                },
                {
                    'message_content': 'Hi! I can help you with that. What seems to be the problem?',
                    'direction': 'to_client',
                    'social_create_time': '2025-08-16T10:01:00Z'
                }
            ]
        }
    
    def test_gemini_service_initialization(self, gemini_service):
        """Test Gemini service initialization."""
        assert gemini_service.api_key == "test-api-key"
        assert gemini_service.model is not None
    
    @patch('services.gemini_service.genai.configure')
    @patch('services.gemini_service.genai.GenerativeModel')
    def test_gemini_configure_called(self, mock_model_class, mock_configure, gemini_service):
        """Test that genai.configure is called during initialization."""
        # Re-create service to trigger the configure call
        service = GeminiService("test-api-key")
        mock_configure.assert_called_once_with(api_key="test-api-key")
    
    @patch('services.gemini_service.genai.configure')
    @patch('services.gemini_service.genai.GenerativeModel')
    def test_gemini_model_creation(self, mock_model_class, mock_configure, gemini_service):
        """Test that GenerativeModel is created with correct model name."""
        # Re-create service to trigger the model creation
        service = GeminiService("test-api-key")
        mock_model_class.assert_called_once_with('gemini-1.5-flash')
    
    @pytest.mark.asyncio
    async def test_analyze_single_conversation_success(self, gemini_service, sample_conversation):
        """Test successful conversation analysis."""
        with patch.object(gemini_service, '_call_gemini_with_retry') as mock_call:
            mock_call.return_value = '''
            {
                "conversation_analysis": {
                    "satisfaction_score": 4,
                    "satisfaction_confidence": 0.8,
                    "is_satisfied": true,
                    "resolution_achieved": true,
                    "common_topics": ["billing", "customer support"]
                },
                "message_analyses": [
                    {
                        "message_content": "Hello, I have a billing issue",
                        "sentiment_score": -0.2,
                        "sentiment_confidence": 0.7,
                        "topics": ["billing"]
                    }
                ]
            }
            '''
            
            result = await gemini_service._analyze_single_conversation(sample_conversation)
            
            assert result['satisfaction_score'] == 4
            assert result['is_satisfied'] == True
            assert result['resolution_achieved'] == True
            assert "billing" in result['common_topics']
            assert len(result['message_analyses']) == 2
    
    @pytest.mark.asyncio
    async def test_analyze_single_conversation_fallback(self, gemini_service, sample_conversation):
        """Test fallback when analysis fails."""
        with patch.object(gemini_service, '_call_gemini_with_retry') as mock_call:
            mock_call.side_effect = Exception("API Error")
            
            result = await gemini_service._analyze_single_conversation(sample_conversation)
            
            # Should return fallback values
            assert result['satisfaction_score'] == 3
            assert result['is_satisfied'] == False
            assert result['common_topics'] == ['general inquiry']
    
    def test_create_comprehensive_prompt(self, gemini_service, sample_conversation):
        """Test prompt creation for Gemini."""
        prompt = gemini_service._create_comprehensive_prompt(sample_conversation['messages'])
        
        assert "CUSTOMER" in prompt
        assert "AGENT" in prompt
        assert "billing issue" in prompt
        assert "JSON format" in prompt
        assert "satisfaction_score" in prompt
    
    def test_format_messages_for_analysis(self, gemini_service, sample_conversation):
        """Test message formatting for analysis."""
        formatted = gemini_service._format_messages_for_analysis(sample_conversation['messages'])
        
        assert "[CUSTOMER]: Hello, I have a billing issue" in formatted
        assert "[AGENT]: Hi! I can help you with that" in formatted
    
    @pytest.mark.asyncio
    async def test_call_gemini_with_retry_success(self, gemini_service):
        """Test successful Gemini API call."""
        with patch.object(gemini_service.model, 'generate_content') as mock_generate:
            mock_response = Mock()
            mock_response.text = '{"result": "success"}'
            mock_generate.return_value = mock_response
            
            result = await gemini_service._call_gemini_with_retry("test prompt")
            assert result == '{"result": "success"}'
    
    @pytest.mark.asyncio
    async def test_call_gemini_with_retry_failure_then_success(self, gemini_service):
        """Test retry logic on failure."""
        with patch.object(gemini_service.model, 'generate_content') as mock_generate:
            # First call fails, second succeeds
            mock_generate.side_effect = [Exception("API Error"), Mock(text='{"result": "success"}')]
            
            result = await gemini_service._call_gemini_with_retry("test prompt")
            assert result == '{"result": "success"}'
            assert mock_generate.call_count == 2
    
    def test_create_fallback_result(self, gemini_service, sample_conversation):
        """Test fallback result creation."""
        result = gemini_service._create_fallback_result(sample_conversation)
        
        assert result['chat_id'] == 'test_chat_123'
        assert result['satisfaction_score'] == 3
        assert result['is_satisfied'] == False
        assert result['common_topics'] == ['general inquiry']
        assert len(result['message_analyses']) == 2


class TestGeminiServiceIntegration:
    """Integration tests for Gemini service."""
    
    @pytest.fixture
    def gemini_service(self):
        """Create Gemini service instance for testing."""
        return GeminiService("test-api-key")
    
    @pytest.mark.asyncio
    async def test_batch_analysis_empty_list(self, gemini_service):
        """Test batch analysis with empty conversation list."""
        result = await gemini_service.batch_analyze_conversations([])
        assert result == []
    
    @pytest.mark.asyncio
    async def test_batch_analysis_single_conversation(self, gemini_service):
        """Test batch analysis with single conversation."""
        conversation = {
            'chat_id': 'test_123',
            'messages': [
                {'message_content': 'Hello', 'direction': 'to_company', 'social_create_time': '2025-08-16T10:00:00Z'}
            ]
        }
        
        with patch.object(gemini_service, '_analyze_single_conversation') as mock_analyze:
            mock_analyze.return_value = {
                'satisfaction_score': 5,
                'is_satisfied': True,
                'resolution_achieved': True,
                'common_topics': ['greeting'],
                'message_analyses': []
            }
            
            results = await gemini_service.batch_analyze_conversations([conversation])
            
            assert len(results) == 1
            assert results[0]['satisfaction_score'] == 5
            assert results[0]['is_satisfied'] == True


# Test the global function
def test_get_gemini_service():
    """Test the global get_gemini_service function."""
    from services.gemini_service import get_gemini_service
    
    service1 = get_gemini_service("key1")
    service2 = get_gemini_service("key1")
    
    # Should return the same instance (singleton pattern)
    assert service1 is service2
    
    # Different keys should create different instances
    service3 = get_gemini_service("key2")
    assert service1 is not service3
