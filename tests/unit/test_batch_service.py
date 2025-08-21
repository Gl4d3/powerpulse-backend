import pytest
from unittest.mock import MagicMock
from models import Conversation, Message
from services.batch_service import create_batches, estimate_token_count
from config import settings

# Mock session for testing
@pytest.fixture
def mock_db_session():
    return MagicMock()

# Mock Conversation and Message objects
def create_mock_conversation(id, messages_content):
    conv = Conversation(id=id, fb_chat_id=f"chat_{id}")
    conv.messages = [Message(message_content=content) for content in messages_content]
    return conv

def test_estimate_token_count(mock_db_session):
    # This test is limited because the function now queries the DB.
    # A better approach would be to mock the DB query.
    conv = create_mock_conversation(1, ["Hello world", "This is a test"])
    
    # Mock the db query
    mock_db_session.query.return_value.filter.return_value.all.return_value = conv.messages
    
    # Total characters: 11 + 14 = 25. Estimated tokens: 25 // 4 = 6
    assert estimate_token_count(conv, mock_db_session) == 6

def test_create_batches_simple(mock_db_session):
    conversations = [
        create_mock_conversation(1, ["short message"]),
        create_mock_conversation(2, ["another short message"])
    ]
    # Mock the db query for both conversations
    mock_db_session.query.return_value.filter.return_value.all.side_effect = [
        conversations[0].messages,
        conversations[1].messages
    ]
    
    batches = create_batches(conversations, mock_db_session)
    assert len(batches) == 1
    assert len(batches[0]) == 2

def test_create_batches_respects_token_limit(mock_db_session):
    # Set a low token limit for testing
    original_token_limit = settings.MAX_TOKENS_PER_JOB
    settings.MAX_TOKENS_PER_JOB = 20  # Approx 80 characters

    # Create conversations that should be split into multiple batches
    conv1_messages = ["a" * 40]  # 10 tokens
    conv2_messages = ["b" * 40]  # 10 tokens
    conv3_messages = ["c" * 40]  # 10 tokens
    
    conversations = [
        create_mock_conversation(1, conv1_messages),
        create_mock_conversation(2, conv2_messages),
        create_mock_conversation(3, conv3_messages)
    ]
    
    # Mock the db query
    mock_db_session.query.return_value.filter.return_value.all.side_effect = [
        [Message(message_content=c) for c in conv1_messages],
        [Message(message_content=c) for c in conv2_messages],
        [Message(message_content=c) for c in conv3_messages]
    ]

    batches = create_batches(conversations, mock_db_session)
    
    # Each conversation is 10 tokens. The limit is 20.
    # So, batch 1 should have conv1 and conv2 (10 + 10 = 20 tokens)
    # Batch 2 should have conv3 (10 tokens)
    assert len(batches) == 2
    assert len(batches[0]) == 2
    assert len(batches[1]) == 1

    # Restore original token limit
    settings.MAX_TOKENS_PER_JOB = original_token_limit

def test_create_batches_with_large_conversation(mock_db_session):
    # A conversation that is larger than the token limit should be skipped
    original_token_limit = settings.MAX_TOKENS_PER_JOB
    settings.MAX_TOKENS_PER_JOB = 10

    conversations = [
        create_mock_conversation(1, ["a" * 80])  # 20 tokens, > 10
    ]
    
    mock_db_session.query.return_value.filter.return_value.all.return_value = conversations[0].messages

    batches = create_batches(conversations, mock_db_session)
    assert len(batches) == 0

    settings.MAX_TOKENS_PER_JOB = original_token_limit
