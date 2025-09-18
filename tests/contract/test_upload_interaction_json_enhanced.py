"""
Contract tests for enhanced upload-interaction-json endpoint with async processing and progress tracking.
These tests MUST FAIL before implementation to follow TDD principles.
"""
import pytest
from fastapi.testclient import TestClient
import json
import io
from unittest.mock import patch, MagicMock
from datetime import datetime

from main import app
from schemas import EnhancedUploadResponse, BatchProcessingStatus

client = TestClient(app)

class TestEnhancedUploadContract:
    """Contract tests for POST /api/upload-interaction-json with enhanced features."""
    
    def test_upload_with_progress_tracking_response_structure(self):
        """Test that upload response includes progress tracking fields."""
        # Create a minimal test JSON file
        test_conversations = {
            "conversations": [
                {
                    "fb_chat_id": "test_chat_1",
                    "customer_name": "Test Customer",
                    "messages": [
                        {
                            "message_content": "Hello, I need help",
                            "direction": "to_company", 
                            "social_create_time": "2025-09-17T10:00:00Z",
                            "agent_info": {"agent_name": "Test Agent"}
                        },
                        {
                            "message_content": "How can I help you?",
                            "direction": "to_client",
                            "social_create_time": "2025-09-17T10:01:00Z", 
                            "agent_info": {"agent_name": "Test Agent"}
                        }
                    ]
                }
            ]
        }
        
        # Create file-like object
        json_content = json.dumps(test_conversations)
        json_file = io.BytesIO(json_content.encode())
        json_file.name = "test_conversations.json"
        
        # Make request
        response = client.post(
            "/api/upload-interaction-json",
            files={"file": ("test.json", json_file, "application/json")},
            data={"mode": "interaction"}
        )
        
        # Should return 202 Accepted for async processing
        assert response.status_code == 202
        
        data = response.json()
        
        # Validate enhanced response structure
        assert "upload_id" in data
        assert "progress_url" in data
        assert "status" in data
        
        # Validate progress tracking fields
        assert "interactions_detected" in data
        assert "interactions_analyzed" in data
        assert "processing_time_seconds" in data
        
        # Validate constitutional dual CSI architecture
        assert "avg_csi_score" in data
        assert "avg_inferred_csi" in data  # Secondary CSI
        assert "avg_effectiveness" in data
        assert "avg_efficiency" in data
        assert "avg_effort" in data
        assert "avg_empathy" in data
        
        # Validate performance metrics
        assert "total_tokens_used" in data
        assert "api_calls_made" in data
        assert "success_rate" in data
        assert "error_count" in data
        
        # Validate timestamps
        assert "started_at" in data
        assert "completed_at" in data  # May be null for async
        
        # Progress URL should follow expected pattern
        expected_progress_url = f"/api/upload-interaction-json/{data['upload_id']}/status"
        assert data["progress_url"] == expected_progress_url

    def test_upload_async_processing_mode(self):
        """Test that large files trigger async processing."""
        # Create a larger test dataset that should trigger async processing
        large_conversations = {
            "conversations": []
        }
        
        # Generate 100 test conversations to simulate large file
        for i in range(100):
            conversation = {
                "fb_chat_id": f"test_chat_{i}",
                "customer_name": f"Test Customer {i}",
                "messages": [
                    {
                        "message_content": f"Hello, I need help with issue {i}",
                        "direction": "to_company",
                        "social_create_time": f"2025-09-17T10:{i:02d}:00Z",
                        "agent_info": {"agent_name": "Test Agent"}
                    },
                    {
                        "message_content": f"I can help you with that issue {i}",
                        "direction": "to_client",
                        "social_create_time": f"2025-09-17T10:{i:02d}:30Z",
                        "agent_info": {"agent_name": "Test Agent"}
                    }
                ]
            }
            large_conversations["conversations"].append(conversation)
        
        json_content = json.dumps(large_conversations)
        json_file = io.BytesIO(json_content.encode())
        json_file.name = "large_conversations.json"
        
        response = client.post(
            "/api/upload-interaction-json",
            files={"file": ("large_test.json", json_file, "application/json")},
            data={"mode": "interaction", "force_reprocess": "true"}
        )
        
        # Should accept and return processing status
        assert response.status_code == 202
        
        data = response.json()
        
        # For large files, status should indicate async processing
        assert data["status"] in ["processing", "completed"]
        assert isinstance(data["conversations_processed"], int)
        assert data["conversations_processed"] <= 100  # May be partial if async

    def test_upload_error_handling_contract(self):
        """Test error response structure for invalid uploads."""
        # Test invalid JSON file
        invalid_content = "not valid json"
        invalid_file = io.BytesIO(invalid_content.encode())
        invalid_file.name = "invalid.json"
        
        response = client.post(
            "/api/upload-interaction-json",
            files={"file": ("invalid.json", invalid_file, "application/json")}
        )
        
        # Should return 400 Bad Request for invalid JSON
        assert response.status_code == 400
        
        error_data = response.json()
        assert "detail" in error_data
        assert "error_code" in error_data
        assert error_data["error_code"] == "INVALID_FILE_FORMAT"

    def test_upload_constitutional_compliance_fields(self):
        """Test that response maintains constitutional dual CSI architecture."""
        test_conversations = {
            "conversations": [
                {
                    "fb_chat_id": "compliance_test",
                    "customer_name": "Constitutional Test",
                    "messages": [
                        {
                            "message_content": "Testing constitutional compliance",
                            "direction": "to_company",
                            "social_create_time": "2025-09-17T10:00:00Z",
                            "agent_info": {"agent_name": "Agent"}
                        }
                    ]
                }
            ]
        }
        
        json_content = json.dumps(test_conversations)
        json_file = io.BytesIO(json_content.encode())
        json_file.name = "constitutional_test.json"
        
        response = client.post(
            "/api/upload-interaction-json",
            files={"file": ("constitutional.json", json_file, "application/json")}
        )
        
        assert response.status_code == 202
        data = response.json()
        
        # CONSTITUTIONAL REQUIREMENT: Dual CSI Architecture
        # Primary CSI from AI micro-metrics
        assert "avg_csi_score" in data
        assert isinstance(data["avg_csi_score"], (int, float))
        
        # Secondary CSI for comparison
        assert "avg_inferred_csi" in data
        # Note: May be None if not calculated yet for async processing
        
        # Four Pillars from AI micro-metrics
        assert "avg_effectiveness" in data
        assert "avg_efficiency" in data  
        assert "avg_effort" in data
        assert "avg_empathy" in data
        
        # All scores should be in valid range (1-10) if present
        for field in ["avg_csi_score", "avg_effectiveness", "avg_efficiency", "avg_effort", "avg_empathy"]:
            if data[field] is not None:
                assert 1.0 <= data[field] <= 10.0, f"{field} should be in range 1-10"

    def test_upload_batch_optimization_metrics(self):
        """Test that response includes batch optimization performance metrics."""
        test_conversations = {
            "conversations": [
                {
                    "fb_chat_id": "batch_test",
                    "customer_name": "Batch Test",
                    "messages": [
                        {
                            "message_content": "Testing batch optimization",
                            "direction": "to_company",
                            "social_create_time": "2025-09-17T10:00:00Z"
                        }
                    ]
                }
            ]
        }
        
        json_content = json.dumps(test_conversations)
        json_file = io.BytesIO(json_content.encode())
        
        response = client.post(
            "/api/upload-interaction-json",
            files={"file": ("batch.json", json_file, "application/json")}
        )
        
        assert response.status_code == 202
        data = response.json()
        
        # Batch optimization metrics
        assert "total_tokens_used" in data
        assert "api_calls_made" in data
        assert isinstance(data["total_tokens_used"], int)
        assert isinstance(data["api_calls_made"], int)
        
        # Success rate and error tracking
        assert "success_rate" in data
        assert "error_count" in data
        assert 0.0 <= data["success_rate"] <= 1.0
        assert isinstance(data["error_count"], int)
        assert data["error_count"] >= 0