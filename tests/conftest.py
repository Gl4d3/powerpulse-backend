"""
Pytest configuration and fixtures for PowerPulse Analytics tests.
"""
import pytest
import asyncio
from typing import AsyncGenerator, Generator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from database import get_db, Base
from models import Conversation, Message, ProcessedChat, Metric


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_db_engine():
    """Create a test database engine using in-memory SQLite."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    return engine


@pytest.fixture(scope="function")
def test_db_session(test_db_engine):
    """Create a test database session."""
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=test_db_engine
    )
    
    # Create all tables
    Base.metadata.create_all(bind=test_db_engine)
    
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        # Drop all tables
        Base.metadata.drop_all(bind=test_db_engine)


@pytest.fixture(scope="function")
def client(test_db_session) -> Generator:
    """Create a test client with test database."""
    
    def override_get_db():
        try:
            yield test_db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def sample_conversation_data():
    """Sample conversation data for testing."""
    return {
        "FB_CHAT_ID_1": [
            {
                "FB_CHAT_ID": "FB_CHAT_ID_1",
                "MESSAGE_CONTENT": "Hello, I have a question about your service",
                "DIRECTION": "to_company",
                "SOCIAL_CREATE_TIME": "2025-01-15T10:00:00.000Z",
                "AGENT_USERNAME": None,
                "AGENT_EMAIL": None
            },
            {
                "FB_CHAT_ID": "FB_CHAT_ID_1",
                "MESSAGE_CONTENT": "Hi! I'd be happy to help. What's your question?",
                "DIRECTION": "to_client",
                "SOCIAL_CREATE_TIME": "2025-01-15T10:01:00.000Z",
                "AGENT_USERNAME": "AGENT_001",
                "AGENT_EMAIL": "agent1@company.com"
            },
            {
                "FB_CHAT_ID": "FB_CHAT_ID_1",
                "MESSAGE_CONTENT": "Thank you! I'm very satisfied with the help.",
                "DIRECTION": "to_company",
                "SOCIAL_CREATE_TIME": "2025-01-15T10:05:00.000Z",
                "AGENT_USERNAME": None,
                "AGENT_EMAIL": None
            }
        ]
    }


@pytest.fixture
def mock_gpt_response():
    """Mock GPT API response for testing."""
    return {
        "sentiment": "positive",
        "sentiment_score": 0.8,
        "satisfaction_score": 5,
        "topics": ["customer service", "satisfaction"],
        "is_resolved": True,
        "resolution_quality": "excellent"
    }


@pytest.fixture
def sample_metrics_data():
    """Sample metrics data for testing."""
    return {
        "total_conversations": 100,
        "satisfied_conversations": 85,
        "csat_percentage": 85.0,
        "fcr_rate": 78.0,
        "avg_response_time": 2.5,
        "sentiment_distribution": {
            "positive": 60,
            "neutral": 25,
            "negative": 15
        }
    }
