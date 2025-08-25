"""
Unit tests for GPT service functionality.
"""
import pytest
import sys
import os
from unittest.mock import Mock, patch, AsyncMock

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from services.gpt_service import OptimizedGPTService


class TestOptimizedGPTService:
    """Test GPT service functionality."""
    
    @pytest.fixture
    def gpt_service(self):
        """Create GPT service instance for testing."""
        return OptimizedGPTService("test-api-key")
    
    @pytest.fixture
    def sample_conversation(self):
        """Sample conversation data for testing."""
        return {
            "chat_id": "TEST_CHAT_001",
            "messages": [
                {
                    "message_content": "Hello, I have a billing question",
                    "direction": "to_company",
                    "social_create_time": "2025-01-15T10:00:00Z"
                },
                {
                    "message_content": "Hi! I'd be happy to help with your billing question.",
                    "direction": "to_client",
                    "social_create_time": "2025-01-15T10:01:00Z"
                },
                {
                    "message_content": "Thank you, that solves my problem!",
                    "direction": "to_company",
                    "social_create_time": "2025-01-15T10:02:00Z"
                }
            ]
        }
    
    @pytest.mark.asyncio
    async def test_successful_gpt_analysis(self, gpt_service, sample_conversation):
        """Test successful GPT analysis."""
        # Mock successful GPT response - return the string content, not the full response
        mock_response_content = '''{
            "conversation_analysis": {
                "satisfaction_score": 5,
                "satisfaction_confidence": 0.9,
                "is_satisfied": true,
                "resolution_achieved": true,
                "common_topics": ["billing", "customer service"]
            },
            "message_analyses": [
                {
                    "message_content": "Hello, I have a billing question",
                    "sentiment_score": 0.0,
                    "sentiment_confidence": 0.8,
                    "topics": ["billing"]
                }
            ]
        }'''
        
        # Mock the internal method that actually calls GPT
        with patch.object(gpt_service, '_call_gpt_with_retry', return_value=mock_response_content):
            result = await gpt_service._analyze_single_conversation(sample_conversation)
            
            assert result['satisfaction_score'] == 5
            assert result['is_satisfied'] is True
            assert result['resolution_achieved'] is True
            assert "billing" in result['common_topics']
    
    @pytest.mark.asyncio
    async def test_gpt_api_failure_fallback(self, gpt_service, sample_conversation):
        """Test fallback values when GPT API fails."""
        # Mock GPT API failure
        with patch.object(gpt_service, '_call_gpt_with_retry', side_effect=Exception("API Error")):
            result = await gpt_service._analyze_single_conversation(sample_conversation)
            
            # Should return fallback values
            assert result['satisfaction_score'] == 3
            assert result['is_satisfied'] is False
            assert result['resolution_achieved'] is False
            assert result['common_topics'] == ['general inquiry']
    
    @pytest.mark.asyncio
    async def test_invalid_json_response_fallback(self, gpt_service, sample_conversation):
        """Test fallback when GPT returns invalid JSON."""
        # Mock invalid JSON response
        mock_response_content = "This is not valid JSON"
        
        with patch.object(gpt_service, '_call_gpt_with_retry', return_value=mock_response_content):
            result = await gpt_service._analyze_single_conversation(sample_conversation)
            
            # Should return fallback values
            assert result['satisfaction_score'] == 3
            assert result['is_satisfied'] is False
            assert result['resolution_achieved'] is False
            assert result['common_topics'] == ['general inquiry']
    
    @pytest.mark.asyncio
    async def test_retry_logic_on_api_failure(self, gpt_service, sample_conversation):
        """Test retry logic when GPT API fails temporarily."""
        # This test needs to mock at a lower level to test the actual retry logic
        # Mock the OpenAI client to fail first, then succeed
        
        # This is the successful response object we want to get back on the second try
        successful_response = Mock(choices=[Mock(message=Mock(content='''{
                "conversation_analysis": {
                    "satisfaction_score": 4,
                    "is_satisfied": true,
                    "resolution_achieved": true,
                    "common_topics": ["success"]
                },
                "message_analyses": []
            }'''))])

        mock_effects = [
            Exception("API Error"),  # First call will raise this
            successful_response      # Second call will return this
        ]
        
        # Use new_callable=AsyncMock and pass your list to side_effect
        with patch.object(
            gpt_service.client.chat.completions, 
            'create', 
            new_callable=AsyncMock, 
            side_effect=mock_effects
        ):
            result = await gpt_service._analyze_single_conversation(sample_conversation)
            
            # Should succeed on retry
            assert result['satisfaction_score'] == 4
            assert result['is_satisfied'] is True
            assert result['resolution_achieved'] is True


    def test_fallback_result_creation(self, gpt_service, sample_conversation):
        """Test fallback result creation."""
        result = gpt_service._create_fallback_result(sample_conversation)
        
        assert result['satisfaction_score'] == 3
        assert result['is_satisfied'] is False
        assert result['resolution_achieved'] is False
        assert result['common_topics'] == ['general inquiry']
        assert len(result['message_analyses']) == 3
    
    def test_message_formatting_for_analysis(self, gpt_service):
        """Test message formatting for GPT analysis."""
        original_messages = [
            {
                "message_content": "Hello, I need help",
                "direction": "to_company",
                "social_create_time": "2025-01-15T10:00:00Z"
            }
        ]
        
        formatted = gpt_service._format_messages_for_analysis(original_messages)
        
        # Should format messages for GPT analysis
        assert "Hello, I need help" in formatted
        assert "[CUSTOMER]" in formatted
        # Note: Timestamps are not included in the formatted output by design
    
    @pytest.mark.asyncio
    async def test_batch_analysis(self, gpt_service):
        """Test batch analysis functionality."""
        conversations = [
            {"chat_id": "CHAT_001", "messages": [{"message_content": "Hello", "direction": "to_company"}]},
            {"chat_id": "CHAT_002", "messages": [{"message_content": "Hi", "direction": "to_company"}]}
        ]
        
        # Mock successful analysis for both conversations
        with patch.object(gpt_service, '_analyze_single_conversation') as mock_analyze:
            mock_analyze.return_value = {
                'satisfaction_score': 4,
                'is_satisfied': True,
                'resolution_achieved': True,
                'common_topics': ['test']
            }
            
            results = await gpt_service.batch_analyze_conversations(conversations)
            
            assert len(results) == 2
            assert all(result['is_satisfied'] for result in results)
    
    @pytest.mark.asyncio
    async def test_batch_analysis_with_errors(self, gpt_service):
        """Test batch analysis when some conversations fail."""
        conversations = [
            {"chat_id": "CHAT_001", "messages": [{"message_content": "Hello", "direction": "to_company"}]},
            {"chat_id": "CHAT_002", "messages": [{"message_content": "Hi", "direction": "to_company"}]}
        ]
        
        # Mock first conversation succeeds, second fails
        with patch.object(gpt_service, '_analyze_single_conversation') as mock_analyze:
            mock_analyze.side_effect = [
                {
                    'satisfaction_score': 4,
                    'is_satisfied': True,
                    'resolution_achieved': True,
                    'common_topics': ['test']
                },
                Exception("Analysis failed")
            ]
            
            results = await gpt_service.batch_analyze_conversations(conversations)
            
            assert len(results) == 2
            # First should be successful
            assert results[0]['is_satisfied'] is True
            # Second should be fallback
            assert results[1]['is_satisfied'] is False
            assert results[1]['common_topics'] == ['general inquiry']
    
    @pytest.mark.asyncio
    async def test_gpt_client_integration(self, gpt_service):
        """Test actual GPT client integration (with mocking)."""
        # Mock the OpenAI client response properly
        mock_openai_response = Mock()
        mock_openai_response.choices = [Mock()]
        mock_openai_response.choices[0].message.content = '''{
            "conversation_analysis": {
                "satisfaction_score": 4,
                "is_satisfied": true,
                "resolution_achieved": true,
                "common_topics": ["test"]
            },
            "message_analyses": []
        }'''
        
        # Use AsyncMock to properly handle async calls
        with patch.object(gpt_service.client.chat.completions, 'create', new_callable=AsyncMock, return_value=mock_openai_response):
            result = await gpt_service._call_gpt_with_retry("test prompt")
            
            assert "satisfaction_score" in result
            assert "is_satisfied" in result


class TestGPTServiceErrorHandling:
    """Test GPT service error handling scenarios."""
    
    @pytest.fixture
    def gpt_service(self):
        """Create GPT service instance for testing."""
        return OptimizedGPTService("test-api-key")
    
    @pytest.mark.asyncio
    async def test_rate_limit_handling(self, gpt_service):
        """Test handling of OpenAI rate limits."""
        # Mock rate limit error
        with patch.object(gpt_service, '_call_gpt_with_retry', 
                         side_effect=Exception("Rate limit exceeded")):
            result = await gpt_service._analyze_single_conversation({"chat_id": "test", "messages": []})
            
            # Should return fallback values
            assert result['common_topics'] == ['general inquiry']
    
    @pytest.mark.asyncio
    async def test_network_timeout_handling(self, gpt_service):
        """Test handling of network timeouts."""
        # Mock timeout error
        with patch.object(gpt_service, '_call_gpt_with_retry', 
                         side_effect=Exception("Request timeout")):
            result = await gpt_service._analyze_single_conversation({"chat_id": "test", "messages": []})
            
            # Should return fallback values
            assert result['common_topics'] == ['general inquiry']
    
    @pytest.mark.asyncio
    async def test_empty_messages_handling(self, gpt_service):
        """Test handling of conversations with no messages."""
        conversation = {"chat_id": "EMPTY_CHAT", "messages": []}
        result = await gpt_service._analyze_single_conversation(conversation)
        
        # Should return fallback result
        assert result['common_topics'] == ['general inquiry']
        assert result['satisfaction_score'] == 3


class TestGPTServicePromptGeneration:
    """Test GPT prompt generation functionality."""
    
    @pytest.fixture
    def gpt_service(self):
        """Create GPT service instance for testing."""
        return OptimizedGPTService("test-api-key")
    
    def test_comprehensive_prompt_creation(self, gpt_service):
        """Test comprehensive prompt creation."""
        messages = [
            {"message_content": "Hello", "direction": "to_company"},
            {"message_content": "Hi there", "direction": "to_client"}
        ]
        
        prompt = gpt_service._create_comprehensive_prompt(messages)
        
        # Should contain key analysis instructions
        assert "customer service conversation" in prompt.lower()
        assert "json format" in prompt.lower()
        assert "satisfaction_score" in prompt
        assert "resolution_achieved" in prompt
    
    def test_message_formatting(self, gpt_service):
        """Test message formatting for analysis."""
        messages = [
            {
                "message_content": "Hello, I have a problem",
                "direction": "to_company",
                "social_create_time": "2025-01-15T10:00:00Z"
            }
        ]
        
        formatted = gpt_service._format_messages_for_analysis(messages)
        
        # Should format messages properly
        assert "Hello, I have a problem" in formatted
        assert "[CUSTOMER]" in formatted
        # Note: Timestamps are not included in formatted output by design


class TestGPTServiceIntegration:
    """Test GPT service integration scenarios."""
    
    @pytest.fixture
    def gpt_service(self):
        """Create GPT service instance for testing."""
        return OptimizedGPTService("test-api-key")
    
    @pytest.mark.asyncio
    async def test_full_conversation_analysis_flow(self, gpt_service):
        """Test the complete conversation analysis flow."""
        conversation = {
            "chat_id": "FLOW_TEST",
            "messages": [
                {
                    "message_content": "I need help with my bill",
                    "direction": "to_company",
                    "social_create_time": "2025-01-15T10:00:00Z"
                },
                {
                    "message_content": "I can help you with that",
                    "direction": "to_client",
                    "social_create_time": "2025-01-15T10:01:00Z"
                }
            ]
        }
        
        # Mock GPT response
        mock_response_content = '''{
            "conversation_analysis": {
                "satisfaction_score": 4,
                "satisfaction_confidence": 0.8,
                "is_satisfied": true,
                "resolution_achieved": true,
                "common_topics": ["billing", "customer service"]
            },
            "message_analyses": [
                {
                    "message_content": "I need help with my bill",
                    "sentiment_score": 0.0,
                    "sentiment_confidence": 0.7,
                    "topics": ["billing"]
                }
            ]
        }'''
        
        with patch.object(gpt_service, '_call_gpt_with_retry', return_value=mock_response_content):
            result = await gpt_service._analyze_single_conversation(conversation)
            
            # Verify complete analysis
            assert result['chat_id'] == "FLOW_TEST"
            assert result['satisfaction_score'] == 4
            assert result['is_satisfied'] is True
            assert result['resolution_achieved'] is True
            assert "billing" in result['common_topics']
            assert len(result['message_analyses']) == 2
