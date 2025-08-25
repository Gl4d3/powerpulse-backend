import pytest
import json
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base, get_db
from main import app
from models import Job, Conversation

# Setup a test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture(scope="function")
def db_session():
    # Create the tables.
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Drop the tables after the test.
        Base.metadata.drop_all(bind=engine)

@patch('services.gemini_service.analyze_conversations_batch', new_callable=AsyncMock)
@patch('services.gpt_service.batch_analyze_conversations', new_callable=AsyncMock)
def test_upload_and_process_jobs(mock_gpt_service, mock_gemini_service, db_session):
    # Set up mock return values
    mock_gemini_service.return_value = [
        {"id": 1, "satisfaction_score": 4, "sentiment_score": 0.8, "first_contact_resolution": True},
        {"id": 2, "satisfaction_score": 2, "sentiment_score": -0.5, "first_contact_resolution": False}
    ]
    mock_gpt_service.return_value = mock_gemini_service.return_value # for simplicity

    # Sample file content
    sample_file_content = {
        "chat_1": [
            {"MESSAGE_CONTENT": "Hello", "DIRECTION": "to_company", "SOCIAL_CREATE_TIME": "2025-08-21T10:00:00Z"},
            {"MESSAGE_CONTENT": "Hi, how can I help?", "DIRECTION": "to_client", "SOCIAL_CREATE_TIME": "2025-08-21T10:01:00Z"}
        ],
        "chat_2": [
            {"MESSAGE_CONTENT": "I have an issue.", "DIRECTION": "to_company", "SOCIAL_CREATE_TIME": "2025-08-21T11:00:00Z"}
        ]
    }
    
    # Upload the file
    response = client.post(
        "/api/upload-json",
        files={"file": ("test.json", json.dumps(sample_file_content), "application/json")}
    )
    
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["success"] is True
    assert response_data["conversations_processed"] == 2
    
    # Verify that jobs were created and processed
    jobs = db_session.query(Job).all()
    assert len(jobs) > 0
    for job in jobs:
        assert job.status == "completed"
        assert job.result is not None
        
    # Verify that conversations were updated
    conversations = db_session.query(Conversation).all()
    assert len(conversations) == 2
    convo1 = db_session.query(Conversation).filter_by(id=1).first()
    assert convo1.satisfaction_score == 4