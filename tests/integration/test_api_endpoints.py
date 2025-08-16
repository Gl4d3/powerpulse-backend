"""
Integration tests for PowerPulse Analytics API endpoints.
"""
import pytest
import json
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from models import Conversation, Message, ProcessedChat


class TestUploadEndpoint:
    """Test file upload endpoint functionality."""
    
    def test_upload_valid_json(self, client: TestClient, test_db_session: Session):
        """Test successful JSON file upload."""
        # Create test data
        test_data = {
            "FB_CHAT_ID_1": [
                {
                    "FB_CHAT_ID": "FB_CHAT_ID_1",
                    "MESSAGE_CONTENT": "Hello, I need help",
                    "DIRECTION": "to_company",
                    "SOCIAL_CREATE_TIME": "2025-01-15T10:00:00.000Z",
                    "AGENT_USERNAME": None,
                    "AGENT_EMAIL": None
                },
                {
                    "FB_CHAT_ID": "FB_CHAT_ID_1",
                    "MESSAGE_CONTENT": "Hi! How can I help you?",
                    "DIRECTION": "to_client",
                    "SOCIAL_CREATE_TIME": "2025-01-15T10:01:00.000Z",
                    "AGENT_USERNAME": "AGENT_001",
                    "AGENT_EMAIL": "agent1@company.com"
                }
            ]
        }
        
        # Convert to JSON string and create file-like object
        json_content = json.dumps(test_data)
        
        # Test upload endpoint
        response = client.post(
            "/api/upload-json",
            files={"file": ("test_data.json", json_content, "application/json")},
            data={"force_reprocess": "false"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "upload_id" in data
        assert data["conversations_processed"] == 1
    
    def test_upload_invalid_format(self, client: TestClient):
        """Test error handling for invalid file format."""
        # Test with non-JSON content
        response = client.post(
            "/api/upload-json",
            files={"file": ("test.txt", "This is not JSON", "text/plain")},
            data={"force_reprocess": "false"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "error" in data
    
    def test_upload_empty_file(self, client: TestClient):
        """Test error handling for empty file."""
        response = client.post(
            "/api/upload-json",
            files={"file": ("empty.json", "", "application/json")},
            data={"force_reprocess": "false"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "error" in data


class TestMetricsEndpoint:
    """Test metrics endpoint functionality."""
    
    def test_get_metrics_empty_database(self, client: TestClient):
        """Test metrics endpoint with empty database."""
        response = client.get("/api/metrics")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_conversations"] == 0
        assert data["csat_percentage"] == 0.0
        assert data["fcr_rate"] == 0.0
    
    def test_get_metrics_with_data(self, client: TestClient, test_db_session: Session):
        """Test metrics endpoint with sample data."""
        # Create test conversation
        conversation = Conversation(
            chat_id="TEST_CHAT_001",
            first_message_time="2025-01-15T10:00:00Z",
            last_message_time="2025-01-15T10:05:00Z",
            message_count=2,
            sentiment_score=0.8,
            satisfaction_score=5,
            is_resolved=True,
            topics=["customer service"]
        )
        test_db_session.add(conversation)
        test_db_session.commit()
        
        response = client.get("/api/metrics")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_conversations"] == 1
        assert data["csat_percentage"] == 100.0  # 1/1 satisfied
        assert data["fcr_rate"] == 100.0  # 1/1 resolved
    
    def test_get_metrics_with_date_filter(self, client: TestClient):
        """Test metrics endpoint with date filtering."""
        response = client.get("/api/metrics?start_date=2025-01-01&end_date=2025-01-31")
        
        assert response.status_code == 200
        # Date filtering should work even with empty database


class TestConversationsEndpoint:
    """Test conversations endpoint functionality."""
    
    def test_get_conversations_empty(self, client: TestClient):
        """Test conversations endpoint with empty database."""
        response = client.get("/api/conversations")
        
        assert response.status_code == 200
        data = response.json()
        assert data["conversations"] == []
        assert data["total"] == 0
        assert data["page"] == 1
    
    def test_get_conversations_with_data(self, client: TestClient, test_db_session: Session):
        """Test conversations endpoint with sample data."""
        # Create test conversation
        conversation = Conversation(
            chat_id="TEST_CHAT_002",
            first_message_time="2025-01-15T10:00:00Z",
            last_message_time="2025-01-15T10:05:00Z",
            message_count=2,
            sentiment_score=0.5,
            satisfaction_score=3,
            is_resolved=False,
            topics=["billing"]
        )
        test_db_session.add(conversation)
        test_db_session.commit()
        
        response = client.get("/api/conversations")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["conversations"]) == 1
        assert data["conversations"][0]["chat_id"] == "TEST_CHAT_002"
        assert data["total"] == 1
    
    def test_get_conversations_pagination(self, client: TestClient):
        """Test conversations endpoint pagination."""
        response = client.get("/api/conversations?page=2&page_size=10")
        
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 2
        assert data["page_size"] == 10
    
    def test_get_conversations_filtering(self, client: TestClient):
        """Test conversations endpoint filtering."""
        response = client.get("/api/conversations?satisfied_only=true")
        
        assert response.status_code == 200
        # Filtering should work even with empty database


class TestProgressEndpoint:
    """Test progress tracking endpoint functionality."""
    
    def test_get_progress_empty(self, client: TestClient):
        """Test progress endpoint with no active uploads."""
        response = client.get("/api/progress")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_progress_specific_upload(self, client: TestClient):
        """Test getting progress for specific upload ID."""
        # Test with non-existent upload ID
        response = client.get("/api/progress/non-existent-id")
        
        assert response.status_code == 404
        data = response.json()
        assert "error" in data


class TestHealthEndpoints:
    """Test health and root endpoints."""
    
    def test_root_endpoint(self, client: TestClient):
        """Test root endpoint."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "PowerPulse Analytics API"
        assert data["version"] == "1.0.0"
        assert data["status"] == "running"
    
    def test_health_endpoint(self, client: TestClient):
        """Test health check endpoint."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "PowerPulse Analytics"
