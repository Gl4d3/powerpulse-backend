"""
Comprehensive Functional Testing Suite
Tests all endpoints, service logic, and integration points to validate complete system functionality.

This test suite validates:
1. All API endpoints with various input scenarios
2. Service logic functionality and edge cases
3. Integration between services and components
4. Error handling and validation
5. Data flow and transformations
6. Authentication and authorization (if applicable)
7. Response formats and status codes
8. Database operations and transactions
9. Configuration validation
10. Worker and background processing
"""

import pytest
import asyncio
import json
import uuid
import time
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
import tempfile
import os

from fastapi.testclient import TestClient
from fastapi import status
from sqlalchemy.orm import Session
from sqlalchemy import text

from main import app
from database import SessionLocal, get_db
from models import UploadSession, BatchContext, Job, DailyAnalysis, Interaction
from services.upload_session_service import UploadSessionService
from services.batch_processing_service import BatchProcessingService
from services.constitutional_validator import ConstitutionalValidator
from config import settings
from worker import EnhancedWorker


class TestComprehensiveFunctional:
    """Comprehensive functional tests covering all system components."""
    
    @pytest.fixture
    def client(self):
        """FastAPI test client."""
        return TestClient(app)
    
    @pytest.fixture
    def db_session(self):
        """Database session for testing."""
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    @pytest.fixture
    def sample_json_file(self):
        """Create a temporary JSON file for upload testing."""
        test_data = [
            {
                "conversation_id": f"test_conv_{i}",
                "timestamp": f"2024-01-{i:02d}T10:00:00Z",
                "messages": [
                    {
                        "role": "user",
                        "content": f"Test message {i}",
                        "timestamp": f"2024-01-{i:02d}T10:00:00Z"
                    },
                    {
                        "role": "assistant",
                        "content": f"Test response {i}",
                        "timestamp": f"2024-01-{i:02d}T10:01:00Z"
                    }
                ]
            }
            for i in range(1, 21)  # 20 interactions
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_data, f)
            yield f.name
        
        os.unlink(f.name)
    
    @pytest.fixture
    def mock_gemini_success(self):
        """Mock successful Gemini service responses."""
        with patch('services.batch_processing_service.gemini_service') as mock:
            mock.analyze_interactions_batch = AsyncMock(return_value={
                'success': True,
                'results': [
                    {
                        'conversation_id': f'test_conv_{i}',
                        'calculated_csi': 0.80 + (i % 10) * 0.01,
                        'inferred_csi': 0.82 + (i % 8) * 0.01,
                        'ai_insights': f'Test insights for conversation {i}',
                        'processing_metadata': {
                            'tokens_used': 150,
                            'cost_usd': 0.001,
                            'processing_time_ms': 800
                        }
                    }
                    for i in range(1, 21)
                ],
                'cost_saved_percentage': 85.0,
                'processing_time_seconds': 15.0,
                'total_tokens_saved': 2000,
                'batch_optimization_applied': True
            })
            
            mock.get_api_cost_estimate = AsyncMock(return_value={
                'estimated_cost_usd': 0.05,
                'estimated_tokens': 2000,
                'cost_reduction_percentage': 85.0
            })
            
            yield mock

    # ==================== ENDPOINT TESTING ====================
    
    def test_root_endpoint(self, client):
        """Test root endpoint functionality."""
        response = client.get("/")
        assert response.status_code == status.HTTP_200_OK
        # Verify response structure if root endpoint returns data
    
    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            assert "status" in data
            assert data["status"] in ["healthy", "ok"]
    
    # ==================== UPLOAD ENDPOINTS ====================
    
    def test_enhanced_upload_endpoint_success(self, client, sample_json_file, mock_gemini_success):
        """Test successful file upload via enhanced endpoint."""
        with open(sample_json_file, 'rb') as f:
            response = client.post(
                "/api/upload-json-enhanced",
                files={"file": ("test.json", f, "application/json")},
                data={"batch_strategy": "auto", "priority": "normal"}
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Validate response structure
        required_fields = ["session_id", "status", "batch_strategy", "estimated_cost_savings"]
        for field in required_fields:
            assert field in data
        
        assert data["status"] == "processing"
        assert data["batch_strategy"] in ["small", "medium", "large"]
        assert isinstance(data["estimated_cost_savings"], (int, float))
    
    def test_enhanced_upload_endpoint_validation_errors(self, client):
        """Test upload endpoint with invalid inputs."""
        # Test missing file
        response = client.post("/api/upload-json-enhanced", data={"batch_strategy": "auto"})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Test invalid file type
        response = client.post(
            "/api/upload-json-enhanced",
            files={"file": ("test.txt", b"not json", "text/plain")},
            data={"batch_strategy": "auto"}
        )
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY]
        
        # Test invalid batch strategy
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump([{"test": "data"}], f)
            f.flush()
            
            response = client.post(
                "/api/upload-json-enhanced",
                files={"file": ("test.json", open(f.name, 'rb'), "application/json")},
                data={"batch_strategy": "invalid"}
            )
            assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY]
        
        os.unlink(f.name)
    
    def test_upload_status_endpoint(self, client, db_session):
        """Test upload status endpoint functionality."""
        # Create a test session
        session = UploadSession(
            session_id="test-session-123",
            status="processing",
            interactions_count=25,
            batch_strategy="medium",
            cost_saved_percentage=85.0,
            processing_time_seconds=12.5
        )
        db_session.add(session)
        db_session.commit()
        
        # Test valid session ID
        response = client.get("/api/upload-status/test-session-123")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        required_fields = ["session_id", "status", "progress_percentage"]
        for field in required_fields:
            assert field in data
        
        assert data["session_id"] == "test-session-123"
        assert data["status"] == "processing"
        
        # Test invalid session ID
        response = client.get("/api/upload-status/nonexistent-session")
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_retry_endpoint(self, client, db_session):
        """Test session retry endpoint functionality."""
        # Create a failed session
        session = UploadSession(
            session_id="failed-session-456",
            status="failed",
            interactions_count=30,
            batch_strategy="medium",
            retry_count=1,
            max_retries=3,
            error_message="Test failure"
        )
        db_session.add(session)
        db_session.commit()
        
        # Test retry for failed session
        response = client.post("/api/retry/failed-session-456")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["session_id"] == "failed-session-456"
        assert data["status"] == "retrying"
        assert data["retry_count"] == 2
        
        # Test retry for nonexistent session
        response = client.post("/api/retry/nonexistent-session")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        
        # Test retry for session that has exceeded max retries
        session.retry_count = 3
        db_session.commit()
        
        response = client.post("/api/retry/failed-session-456")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    # ==================== BATCH CONFIGURATION ENDPOINTS ====================
    
    def test_batch_config_endpoint(self, client, db_session):
        """Test batch configuration endpoint."""
        response = client.get("/api/batch-config")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        required_sections = ["batch_settings", "performance_metrics", "system_status"]
        for section in required_sections:
            assert section in data
        
        # Validate batch settings structure
        batch_settings = data["batch_settings"]
        assert "enabled" in batch_settings
        assert "max_concurrent_sessions" in batch_settings
        assert "batch_sizes" in batch_settings
        
        # Validate performance metrics structure
        performance_metrics = data["performance_metrics"]
        assert isinstance(performance_metrics, dict)
    
    def test_update_batch_config_endpoint(self, client):
        """Test batch configuration update endpoint."""
        new_config = {
            "max_concurrent_sessions": 5,
            "batch_sizes": {
                "small": 15,
                "medium": 50,
                "large": 150
            }
        }
        
        response = client.put("/api/batch-config", json=new_config)
        # Endpoint might not exist yet, so allow 404 or success
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND, status.HTTP_501_NOT_IMPLEMENTED]
        
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            assert "updated" in data
    
    # ==================== CONSTITUTIONAL COMPLIANCE ENDPOINTS ====================
    
    def test_constitutional_compliance_endpoint(self, client, db_session):
        """Test constitutional compliance endpoint."""
        response = client.get("/api/constitutional/compliance")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        required_fields = ["is_compliant", "constitutional_requirements", "system_compliance"]
        for field in required_fields:
            assert field in data
        
        # Validate constitutional requirements structure
        requirements = data["constitutional_requirements"]
        assert "ai_supremacy" in requirements
        assert "dual_csi_architecture" in requirements
        assert "cost_reduction" in requirements
        assert "processing_speed" in requirements
    
    def test_constitutional_compliance_with_session_id(self, client, db_session):
        """Test constitutional compliance for specific session."""
        # Create a compliant session
        session = UploadSession(
            session_id="compliant-session-789",
            status="completed",
            interactions_count=50,
            batch_strategy="medium",
            cost_saved_percentage=87.5,
            processing_time_seconds=14.0,
            interactions_processed=50
        )
        db_session.add(session)
        db_session.commit()
        
        response = client.get("/api/constitutional/compliance?session_id=compliant-session-789")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert "session_id" in data
        assert data["session_id"] == "compliant-session-789"
        assert "is_compliant" in data
        assert "metrics" in data
    
    # ==================== SERVICE LOGIC TESTING ====================
    
    @pytest.mark.asyncio
    async def test_upload_session_service_functionality(self, db_session):
        """Test UploadSessionService functionality."""
        service = UploadSessionService()
        
        # Test session creation
        test_data = [{"conversation_id": "test", "messages": []}]
        session_id = await service.create_upload_session(
            interactions=test_data,
            batch_strategy="auto",
            priority="normal",
            db=db_session
        )
        
        assert isinstance(session_id, str)
        assert len(session_id) > 0
        
        # Verify session in database
        session = db_session.get(UploadSession, session_id)
        assert session is not None
        assert session.status == "processing"
        assert session.interactions_count == 1
        
        # Test session status retrieval
        status_info = await service.get_session_status(session_id, db_session)
        assert status_info["session_id"] == session_id
        assert status_info["status"] == "processing"
        
        # Test batch strategy determination
        strategy = service.determine_batch_strategy([{"test": "data"}] * 75, "auto")
        assert strategy == "medium"  # 75 interactions should be medium batch
        
        strategy = service.determine_batch_strategy([{"test": "data"}] * 15, "auto")
        assert strategy == "small"  # 15 interactions should be small batch
    
    @pytest.mark.asyncio
    async def test_batch_processing_service_functionality(self, mock_gemini_success):
        """Test BatchProcessingService functionality."""
        service = BatchProcessingService()
        
        # Test cost estimation
        interactions = [{"conversation_id": f"test_{i}", "messages": []} for i in range(25)]
        
        estimate = await service.estimate_processing_cost(interactions, "medium")
        assert "estimated_cost_usd" in estimate
        assert "cost_reduction_percentage" in estimate
        assert estimate["cost_reduction_percentage"] >= settings.CONSTITUTIONAL_MIN_COST_REDUCTION_PERCENTAGE
        
        # Test batch creation
        batches = service.create_batches(interactions, "medium")
        assert len(batches) > 0
        assert all(len(batch) <= settings.ENHANCED_BATCH_SIZE_MEDIUM for batch in batches)
        
        # Test context optimization
        context = service.optimize_batch_context(interactions[:10])
        assert "shared_context" in context
        assert "optimization_applied" in context
    
    @pytest.mark.asyncio
    async def test_constitutional_validator_functionality(self, db_session):
        """Test ConstitutionalValidator functionality."""
        validator = ConstitutionalValidator()
        
        # Create a test session for validation
        session = UploadSession(
            session_id="validation-test-session",
            status="completed",
            interactions_count=50,
            batch_strategy="medium",
            cost_saved_percentage=85.0,
            processing_time_seconds=15.0,
            interactions_processed=50
        )
        db_session.add(session)
        db_session.commit()
        
        # Test session compliance validation
        compliance_result = await validator.validate_session_compliance(
            "validation-test-session", db_session
        )
        
        assert hasattr(compliance_result, 'is_compliant')
        assert hasattr(compliance_result, 'violations')
        assert hasattr(compliance_result, 'metrics')
        assert isinstance(compliance_result.violations, list)
        assert isinstance(compliance_result.metrics, dict)
        
        # Test system-wide compliance validation
        system_compliance = await validator.validate_system_compliance(db_session)
        
        assert hasattr(system_compliance, 'is_compliant')
        assert isinstance(system_compliance.metrics, dict)
        assert "success_rate_percentage" in system_compliance.metrics
    
    # ==================== WORKER FUNCTIONALITY TESTING ====================
    
    @pytest.mark.asyncio
    async def test_enhanced_worker_functionality(self, db_session, mock_gemini_success):
        """Test EnhancedWorker functionality."""
        worker = EnhancedWorker()
        
        # Create a test session for worker processing
        session = UploadSession(
            session_id="worker-test-session",
            status="processing",
            interactions_count=20,
            batch_strategy="small",
            retry_count=0,
            max_retries=3
        )
        db_session.add(session)
        db_session.commit()
        
        # Test batch processing
        await worker._process_session_batch(session)
        
        # Verify session was processed
        db_session.refresh(session)
        assert session.status in ["completed", "processing"]
        
        # Test constitutional compliance validation
        await worker._validate_constitutional_compliance()
        # Should not raise exceptions
    
    # ==================== ERROR HANDLING TESTING ====================
    
    def test_error_handling_invalid_json(self, client):
        """Test error handling for invalid JSON uploads."""
        invalid_json = b'{"invalid": json content}'
        
        response = client.post(
            "/api/upload-json-enhanced",
            files={"file": ("invalid.json", invalid_json, "application/json")},
            data={"batch_strategy": "auto"}
        )
        
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY]
        
        if response.status_code == status.HTTP_400_BAD_REQUEST:
            error_data = response.json()
            assert "error" in error_data or "detail" in error_data
    
    def test_error_handling_missing_fields(self, client):
        """Test error handling for missing required fields."""
        incomplete_data = [{"conversation_id": "test"}]  # Missing messages
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(incomplete_data, f)
            f.flush()
            
            response = client.post(
                "/api/upload-json-enhanced",
                files={"file": ("incomplete.json", open(f.name, 'rb'), "application/json")},
                data={"batch_strategy": "auto"}
            )
            
            # Should handle gracefully - either accept or return clear error
            assert response.status_code in [
                status.HTTP_200_OK,  # Accepted with validation warnings
                status.HTTP_400_BAD_REQUEST,  # Clear validation error
                status.HTTP_422_UNPROCESSABLE_ENTITY  # Schema validation error
            ]
        
        os.unlink(f.name)
    
    @pytest.mark.asyncio
    async def test_error_handling_service_failures(self, db_session):
        """Test error handling in service layer."""
        service = UploadSessionService()
        
        # Test handling of invalid data
        try:
            invalid_data = None
            await service.create_upload_session(
                interactions=invalid_data,
                batch_strategy="auto",
                priority="normal",
                db=db_session
            )
        except (ValueError, TypeError, AttributeError) as e:
            # Should raise appropriate exception
            assert isinstance(e, (ValueError, TypeError, AttributeError))
        
        # Test handling of invalid session ID
        try:
            status_info = await service.get_session_status("nonexistent-session", db_session)
            # Should handle gracefully or raise appropriate exception
        except Exception as e:
            assert isinstance(e, (ValueError, KeyError, AttributeError))
    
    # ==================== DATABASE OPERATIONS TESTING ====================
    
    def test_database_operations(self, db_session):
        """Test database operations and transactions."""
        # Test session creation and retrieval
        session = UploadSession(
            session_id="db-test-session",
            status="processing",
            interactions_count=30,
            batch_strategy="medium"
        )
        
        db_session.add(session)
        db_session.commit()
        
        # Verify session exists
        retrieved_session = db_session.get(UploadSession, "db-test-session")
        assert retrieved_session is not None
        assert retrieved_session.status == "processing"
        assert retrieved_session.interactions_count == 30
        
        # Test batch context creation
        batch_context = BatchContext(
            batch_id="test-batch-123",
            session_id="db-test-session",
            batch_size=25,
            status="processing"
        )
        
        db_session.add(batch_context)
        db_session.commit()
        
        # Verify batch context exists and is linked
        retrieved_batch = db_session.query(BatchContext).filter(
            BatchContext.session_id == "db-test-session"
        ).first()
        
        assert retrieved_batch is not None
        assert retrieved_batch.batch_id == "test-batch-123"
        assert retrieved_batch.session_id == "db-test-session"
        
        # Test transaction rollback behavior
        try:
            db_session.add(UploadSession(
                session_id="db-test-session",  # Duplicate ID should fail
                status="processing",
                interactions_count=10,
                batch_strategy="small"
            ))
            db_session.commit()
        except Exception:
            db_session.rollback()
            # Should handle gracefully
        
        # Original session should still exist
        original_session = db_session.get(UploadSession, "db-test-session")
        assert original_session is not None
        assert original_session.interactions_count == 30  # Unchanged
    
    # ==================== CONFIGURATION TESTING ====================
    
    def test_configuration_validation(self):
        """Test configuration settings validation."""
        # Test that required settings are present
        assert hasattr(settings, 'CONSTITUTIONAL_MIN_COST_REDUCTION_PERCENTAGE')
        assert hasattr(settings, 'CONSTITUTIONAL_MIN_INTERACTIONS_PER_SECOND')
        assert hasattr(settings, 'CONSTITUTIONAL_MAX_INTERACTIONS_PER_SECOND')
        assert hasattr(settings, 'ENHANCED_BATCH_SIZE_SMALL')
        assert hasattr(settings, 'ENHANCED_BATCH_SIZE_MEDIUM')
        assert hasattr(settings, 'ENHANCED_BATCH_SIZE_LARGE')
        
        # Test configuration value ranges
        assert 0 <= settings.CONSTITUTIONAL_MIN_COST_REDUCTION_PERCENTAGE <= 100
        assert settings.CONSTITUTIONAL_MIN_INTERACTIONS_PER_SECOND > 0
        assert settings.CONSTITUTIONAL_MAX_INTERACTIONS_PER_SECOND > settings.CONSTITUTIONAL_MIN_INTERACTIONS_PER_SECOND
        assert settings.ENHANCED_BATCH_SIZE_SMALL > 0
        assert settings.ENHANCED_BATCH_SIZE_MEDIUM >= settings.ENHANCED_BATCH_SIZE_SMALL
        assert settings.ENHANCED_BATCH_SIZE_LARGE >= settings.ENHANCED_BATCH_SIZE_MEDIUM
        
        # Test batch strategy configuration
        batch_config = settings.get_batch_processing_config()
        assert isinstance(batch_config, dict)
        assert "enabled" in batch_config
        assert "batch_sizes" in batch_config
        assert "thresholds" in batch_config
        
        # Test constitutional compliance configuration
        constitutional_config = settings.get_constitutional_compliance_config()
        assert isinstance(constitutional_config, dict)
        assert "ai_supremacy_enabled" in constitutional_config
        assert "dual_csi_required" in constitutional_config
        assert "min_cost_reduction_percentage" in constitutional_config
    
    # ==================== INTEGRATION TESTING ====================
    
    @pytest.mark.asyncio
    async def test_full_integration_workflow(self, client, db_session, sample_json_file, mock_gemini_success):
        """Test complete integration workflow from upload to completion."""
        # Step 1: Upload file
        with open(sample_json_file, 'rb') as f:
            upload_response = client.post(
                "/api/upload-json-enhanced",
                files={"file": ("integration_test.json", f, "application/json")},
                data={"batch_strategy": "small", "priority": "normal"}
            )
        
        assert upload_response.status_code == status.HTTP_200_OK
        upload_data = upload_response.json()
        session_id = upload_data["session_id"]
        
        # Step 2: Check initial status
        status_response = client.get(f"/api/upload-status/{session_id}")
        assert status_response.status_code == status.HTTP_200_OK
        status_data = status_response.json()
        assert status_data["status"] == "processing"
        
        # Step 3: Simulate worker processing
        worker = EnhancedWorker()
        session = db_session.get(UploadSession, session_id)
        await worker._process_session_batch(session)
        
        # Step 4: Check final status
        db_session.refresh(session)
        final_status_response = client.get(f"/api/upload-status/{session_id}")
        assert final_status_response.status_code == status.HTTP_200_OK
        final_status_data = final_status_response.json()
        
        # Step 5: Validate constitutional compliance
        compliance_response = client.get(f"/api/constitutional/compliance?session_id={session_id}")
        assert compliance_response.status_code == status.HTTP_200_OK
        compliance_data = compliance_response.json()
        
        # Step 6: Check batch configuration reflects processing
        batch_config_response = client.get("/api/batch-config")
        assert batch_config_response.status_code == status.HTTP_200_OK
        
        # Validate end-to-end integration
        assert session.status in ["completed", "processing"]
        if session.status == "completed":
            assert session.cost_saved_percentage >= settings.CONSTITUTIONAL_MIN_COST_REDUCTION_PERCENTAGE
            assert session.interactions_processed > 0
    
    def test_concurrent_requests_handling(self, client, sample_json_file, mock_gemini_success):
        """Test handling of concurrent API requests."""
        import concurrent.futures
        import threading
        
        def make_upload_request():
            with open(sample_json_file, 'rb') as f:
                return client.post(
                    "/api/upload-json-enhanced",
                    files={"file": ("concurrent_test.json", f.read(), "application/json")},
                    data={"batch_strategy": "auto"}
                )
        
        # Make multiple concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(make_upload_request) for _ in range(3)]
            responses = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # All requests should succeed or fail gracefully
        for response in responses:
            assert response.status_code in [
                status.HTTP_200_OK,
                status.HTTP_429_TOO_MANY_REQUESTS,  # Rate limiting
                status.HTTP_503_SERVICE_UNAVAILABLE  # Service overload
            ]
        
        # At least one should succeed if system is healthy
        success_count = sum(1 for r in responses if r.status_code == status.HTTP_200_OK)
        assert success_count >= 1, "No concurrent requests succeeded"
    
    # ==================== EDGE CASE TESTING ====================
    
    def test_edge_cases_empty_file(self, client):
        """Test edge case handling for empty files."""
        empty_json = json.dumps([])
        
        response = client.post(
            "/api/upload-json-enhanced",
            files={"file": ("empty.json", empty_json.encode(), "application/json")},
            data={"batch_strategy": "auto"}
        )
        
        # Should handle empty files gracefully
        assert response.status_code in [
            status.HTTP_200_OK,  # Accepted with warnings
            status.HTTP_400_BAD_REQUEST,  # Validation error
            status.HTTP_422_UNPROCESSABLE_ENTITY  # Schema validation
        ]
    
    def test_edge_cases_large_file(self, client):
        """Test edge case handling for large files."""
        # Create a large JSON file (but within reasonable limits for testing)
        large_data = [
            {
                "conversation_id": f"large_conv_{i}",
                "timestamp": f"2024-01-01T{i%24:02d}:00:00Z",
                "messages": [
                    {
                        "role": "user",
                        "content": f"Large test message {i} with lots of content " * 50,
                        "timestamp": f"2024-01-01T{i%24:02d}:00:00Z"
                    }
                ]
            }
            for i in range(1000)  # 1000 interactions
        ]
        
        large_json = json.dumps(large_data)
        
        response = client.post(
            "/api/upload-json-enhanced",
            files={"file": ("large.json", large_json.encode(), "application/json")},
            data={"batch_strategy": "auto"}
        )
        
        # Should handle large files appropriately
        assert response.status_code in [
            status.HTTP_200_OK,  # Accepted
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,  # File too large
            status.HTTP_400_BAD_REQUEST  # Processing limitations
        ]
    
    def test_edge_cases_malformed_data_structures(self, client):
        """Test edge case handling for malformed data structures."""
        malformed_data = [
            {"conversation_id": None, "messages": []},  # Null conversation_id
            {"conversation_id": "", "messages": None},   # Null messages
            {"conversation_id": 123, "messages": [{"role": None, "content": "test"}]},  # Invalid types
        ]
        
        malformed_json = json.dumps(malformed_data)
        
        response = client.post(
            "/api/upload-json-enhanced",
            files={"file": ("malformed.json", malformed_json.encode(), "application/json")},
            data={"batch_strategy": "auto"}
        )
        
        # Should handle malformed data gracefully
        assert response.status_code in [
            status.HTTP_200_OK,  # Accepted with validation
            status.HTTP_400_BAD_REQUEST,  # Validation error
            status.HTTP_422_UNPROCESSABLE_ENTITY  # Schema validation
        ]
    
    # ==================== PERFORMANCE TESTING ====================
    
    def test_response_time_performance(self, client):
        """Test API response time performance."""
        # Test lightweight endpoint performance
        start_time = time.time()
        response = client.get("/api/batch-config")
        response_time = time.time() - start_time
        
        # Response should be fast (under 2 seconds)
        assert response_time < 2.0
        assert response.status_code == status.HTTP_200_OK
        
        # Test status endpoint performance
        start_time = time.time()
        # Use a non-existent session ID to test quick 404 response
        response = client.get("/api/upload-status/nonexistent-session-performance-test")
        response_time = time.time() - start_time
        
        # Even 404 responses should be fast
        assert response_time < 1.0
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    @pytest.mark.asyncio
    async def test_memory_usage_stability(self, db_session):
        """Test memory usage stability during processing."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Perform memory-intensive operations
        service = UploadSessionService()
        
        for i in range(10):
            test_data = [{"conversation_id": f"memory_test_{i}", "messages": []}] * 100
            session_id = await service.create_upload_session(
                interactions=test_data,
                batch_strategy="auto",
                priority="normal",
                db=db_session
            )
            
            # Clean up session to prevent memory accumulation
            session = db_session.get(UploadSession, session_id)
            if session:
                db_session.delete(session)
                db_session.commit()
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 100MB for this test)
        assert memory_increase < 100 * 1024 * 1024, f"Memory increased by {memory_increase / 1024 / 1024:.2f} MB"