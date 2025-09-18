"""
Integration Tests - Full Workflow
Tests the complete upload-to-analysis workflow with batch processing and constitutional compliance.

This test suite validates:
1. End-to-end upload session workflow
2. Batch processing optimization
3. Constitutional compliance throughout the pipeline
4. Performance targets achievement
5. Error handling and recovery
6. Data integrity and validation
"""

import pytest
import asyncio
import json
import uuid
import time
from typing import Dict, Any, List
from unittest.mock import AsyncMock, patch, MagicMock

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from main import app
from database import SessionLocal, get_db
from models import UploadSession, BatchContext, Job, DailyAnalysis, Interaction
from services.upload_session_service import UploadSessionService
from services.batch_processing_service import BatchProcessingService
from services.constitutional_validator import ConstitutionalValidator
from config import settings
from worker import EnhancedWorker


class TestIntegrationFullWorkflow:
    """Comprehensive integration tests for the full workflow."""
    
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
    def sample_interaction_data(self) -> List[Dict[str, Any]]:
        """Sample interaction data for testing."""
        return [
            {
                "conversation_id": f"conv_{i}",
                "timestamp": f"2024-01-{i:02d}T10:00:00Z",
                "messages": [
                    {
                        "role": "user",
                        "content": f"Test user message {i}",
                        "timestamp": f"2024-01-{i:02d}T10:00:00Z"
                    },
                    {
                        "role": "assistant", 
                        "content": f"Test assistant response {i}",
                        "timestamp": f"2024-01-{i:02d}T10:01:00Z"
                    }
                ]
            }
            for i in range(1, 26)  # 25 interactions for medium batch testing
        ]
    
    @pytest.fixture
    def mock_gemini_service(self):
        """Mock Gemini service for testing."""
        with patch('services.batch_processing_service.gemini_service') as mock:
            # Mock successful AI response with constitutional compliance
            mock.analyze_interactions_batch = AsyncMock(return_value={
                'success': True,
                'results': [
                    {
                        'conversation_id': f'conv_{i}',
                        'calculated_csi': 0.75 + (i % 10) * 0.02,  # Varies between 0.75-0.93
                        'inferred_csi': 0.77 + (i % 10) * 0.02,    # Varies between 0.77-0.95
                        'ai_insights': f'AI-generated insights for conversation {i}',
                        'processing_metadata': {
                            'tokens_used': 150 + (i % 20) * 5,
                            'cost_usd': 0.00025 * (150 + (i % 20) * 5) / 1000,
                            'processing_time_ms': 800 + (i % 100) * 10
                        }
                    }
                    for i in range(1, 26)
                ],
                'cost_saved_percentage': 82.5,  # Above 80% constitutional requirement
                'processing_time_seconds': 18.5,  # ~1.35 interactions/second within 3-4 range
                'total_tokens_saved': 15000,
                'batch_optimization_applied': True
            })
            
            mock.get_api_cost_estimate = AsyncMock(return_value={
                'estimated_cost_usd': 0.125,
                'estimated_tokens': 5000,
                'cost_reduction_percentage': 82.5
            })
            
            yield mock
    
    @pytest.mark.asyncio
    async def test_complete_upload_session_workflow(
        self, 
        client, 
        db_session, 
        sample_interaction_data,
        mock_gemini_service
    ):
        """Test complete upload session workflow from start to finish."""
        
        # Step 1: Create upload session via enhanced endpoint
        upload_response = client.post(
            "/api/upload-json-enhanced",
            files={"file": ("test_interactions.json", json.dumps(sample_interaction_data), "application/json")},
            data={
                "batch_strategy": "auto",
                "priority": "normal"
            }
        )
        
        assert upload_response.status_code == 200
        upload_data = upload_response.json()
        
        # Verify upload response structure
        assert "session_id" in upload_data
        assert upload_data["status"] == "processing"
        assert "estimated_cost_savings" in upload_data
        assert upload_data["batch_strategy"] in ["small", "medium", "large"]
        
        session_id = upload_data["session_id"]
        
        # Step 2: Verify session creation in database
        session = db_session.get(UploadSession, session_id)
        assert session is not None
        assert session.status == "processing"
        assert session.interactions_count == 25
        assert session.batch_strategy == "medium"  # 25 interactions = medium batch
        
        # Step 3: Simulate worker processing
        worker = EnhancedWorker()
        
        # Process the session through batch processing
        await worker._process_session_batch(session)
        
        # Refresh session from database
        db_session.refresh(session)
        
        # Step 4: Verify successful processing
        assert session.status == "completed"
        assert session.cost_saved_percentage >= settings.CONSTITUTIONAL_MIN_COST_REDUCTION_PERCENTAGE
        assert session.interactions_processed == 25
        
        # Verify processing speed constitutional compliance
        if session.processing_time_seconds:
            interactions_per_second = session.interactions_processed / session.processing_time_seconds
            assert settings.CONSTITUTIONAL_MIN_INTERACTIONS_PER_SECOND <= interactions_per_second <= settings.CONSTITUTIONAL_MAX_INTERACTIONS_PER_SECOND
        
        # Step 5: Verify batch contexts were created
        batch_contexts = db_session.query(BatchContext).filter(
            BatchContext.session_id == session_id
        ).all()
        
        assert len(batch_contexts) > 0
        for batch_context in batch_contexts:
            assert batch_context.status == "completed"
            assert batch_context.ai_insights is not None
            assert batch_context.cost_saved_percentage > 0
        
        # Step 6: Verify constitutional compliance
        constitutional_validator = ConstitutionalValidator()
        compliance_result = await constitutional_validator.validate_session_compliance(
            session_id, db_session
        )
        
        assert compliance_result.is_compliant == True
        assert len(compliance_result.violations) == 0
        
        # Verify AI micro-metrics supremacy
        assert compliance_result.metrics.get("ai_insights_coverage", 0) >= settings.REQUIRED_AI_INSIGHTS_COVERAGE_PERCENTAGE
        
        # Step 7: Test session status endpoint
        status_response = client.get(f"/api/upload-status/{session_id}")
        assert status_response.status_code == 200
        
        status_data = status_response.json()
        assert status_data["session_id"] == session_id
        assert status_data["status"] == "completed"
        assert status_data["progress_percentage"] == 100.0
        assert "performance_metrics" in status_data
        assert "constitutional_compliance" in status_data
        
        # Verify constitutional compliance in response
        compliance_data = status_data["constitutional_compliance"]
        assert compliance_data["is_compliant"] == True
        assert compliance_data["cost_reduction_achieved"] >= settings.CONSTITUTIONAL_MIN_COST_REDUCTION_PERCENTAGE
    
    @pytest.mark.asyncio
    async def test_batch_processing_optimization(
        self,
        client,
        db_session,
        sample_interaction_data,
        mock_gemini_service
    ):
        """Test batch processing optimization and cost reduction."""
        
        # Test different file sizes and their batch strategies
        test_cases = [
            {"interactions": 15, "expected_strategy": "small"},
            {"interactions": 75, "expected_strategy": "medium"}, 
            {"interactions": 300, "expected_strategy": "large"}
        ]
        
        for case in test_cases:
            # Create interaction data of specific size
            interaction_data = sample_interaction_data[:case["interactions"]]
            
            # Upload with auto batch strategy
            upload_response = client.post(
                "/api/upload-json-enhanced",
                files={"file": ("test_interactions.json", json.dumps(interaction_data), "application/json")},
                data={"batch_strategy": "auto"}
            )
            
            assert upload_response.status_code == 200
            upload_data = upload_response.json()
            
            # Verify correct batch strategy selection
            assert upload_data["batch_strategy"] == case["expected_strategy"]
            
            session_id = upload_data["session_id"]
            session = db_session.get(UploadSession, session_id)
            
            # Verify session configuration
            assert session.batch_strategy == case["expected_strategy"]
            assert session.interactions_count == case["interactions"]
            
            # Simulate processing
            worker = EnhancedWorker()
            await worker._process_session_batch(session)
            
            db_session.refresh(session)
            
            # Verify cost optimization achieved
            assert session.cost_saved_percentage >= settings.CONSTITUTIONAL_MIN_COST_REDUCTION_PERCENTAGE
            
            # Verify batch optimization was applied
            batch_contexts = db_session.query(BatchContext).filter(
                BatchContext.session_id == session_id
            ).all()
            
            # Larger files should have more batch contexts
            if case["expected_strategy"] == "large":
                assert len(batch_contexts) >= 3  # More batches for large files
            elif case["expected_strategy"] == "medium":
                assert len(batch_contexts) >= 2  # Medium batches
            else:
                assert len(batch_contexts) >= 1  # Small batches
    
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(
        self,
        client,
        db_session,
        sample_interaction_data
    ):
        """Test error handling and recovery mechanisms."""
        
        # Test 1: Simulate API failure and retry
        with patch('services.batch_processing_service.gemini_service') as mock_gemini:
            # First call fails, second call succeeds
            mock_gemini.analyze_interactions_batch = AsyncMock(
                side_effect=[
                    Exception("Simulated API failure"),
                    {
                        'success': True,
                        'results': [
                            {
                                'conversation_id': f'conv_{i}',
                                'calculated_csi': 0.8,
                                'inferred_csi': 0.8,
                                'ai_insights': f'Recovery test insights {i}'
                            }
                            for i in range(1, 11)
                        ],
                        'cost_saved_percentage': 85.0,
                        'processing_time_seconds': 12.0
                    }
                ]
            )
            
            # Upload session
            upload_response = client.post(
                "/api/upload-json-enhanced",
                files={"file": ("test_interactions.json", json.dumps(sample_interaction_data[:10]), "application/json")},
                data={"batch_strategy": "small"}
            )
            
            session_id = upload_response.json()["session_id"]
            session = db_session.get(UploadSession, session_id)
            
            # Process session (first attempt should fail)
            worker = EnhancedWorker()
            await worker._process_session_batch(session)
            
            db_session.refresh(session)
            
            # Session should be marked for retry
            assert session.status == "retrying"
            assert session.retry_count == 1
            
            # Test retry endpoint
            retry_response = client.post(f"/api/retry/{session_id}")
            assert retry_response.status_code == 200
            
            # Process retry (should succeed)
            await worker._process_session_batch(session)
            db_session.refresh(session)
            
            # Session should now be completed
            assert session.status == "completed"
            assert session.retry_count == 1
    
    @pytest.mark.asyncio
    async def test_constitutional_compliance_validation(
        self,
        client,
        db_session,
        sample_interaction_data,
        mock_gemini_service
    ):
        """Test constitutional compliance validation throughout workflow."""
        
        # Upload session
        upload_response = client.post(
            "/api/upload-json-enhanced",
            files={"file": ("test_interactions.json", json.dumps(sample_interaction_data), "application/json")},
            data={"batch_strategy": "medium"}
        )
        
        session_id = upload_response.json()["session_id"]
        session = db_session.get(UploadSession, session_id)
        
        # Process session
        worker = EnhancedWorker()
        await worker._process_session_batch(session)
        
        db_session.refresh(session)
        
        # Test constitutional compliance endpoint
        compliance_response = client.get(f"/api/constitutional/compliance?session_id={session_id}")
        assert compliance_response.status_code == 200
        
        compliance_data = compliance_response.json()
        
        # Verify constitutional requirements
        assert compliance_data["is_compliant"] == True
        
        # Verify specific constitutional metrics
        metrics = compliance_data["metrics"]
        
        # Cost reduction compliance (80% minimum)
        assert metrics["cost_saved_percentage"] >= settings.CONSTITUTIONAL_MIN_COST_REDUCTION_PERCENTAGE
        
        # Processing speed compliance (3-4 interactions/second)
        if "interactions_per_second" in metrics:
            assert settings.CONSTITUTIONAL_MIN_INTERACTIONS_PER_SECOND <= metrics["interactions_per_second"] <= settings.CONSTITUTIONAL_MAX_INTERACTIONS_PER_SECOND
        
        # AI insights coverage (90% minimum)
        assert metrics.get("ai_insights_coverage", 0) >= settings.REQUIRED_AI_INSIGHTS_COVERAGE_PERCENTAGE
        
        # Dual CSI architecture compliance
        assert metrics.get("csi_completeness_percentage", 0) >= settings.CSI_COMPLETENESS_THRESHOLD_PERCENTAGE
    
    @pytest.mark.asyncio
    async def test_performance_monitoring_integration(
        self,
        client,
        db_session,
        sample_interaction_data,
        mock_gemini_service
    ):
        """Test performance monitoring and metrics collection."""
        
        # Upload multiple sessions to test system performance
        session_ids = []
        
        for i in range(3):
            upload_response = client.post(
                "/api/upload-json-enhanced",
                files={"file": (f"test_interactions_{i}.json", json.dumps(sample_interaction_data), "application/json")},
                data={"batch_strategy": "medium"}
            )
            
            session_ids.append(upload_response.json()["session_id"])
        
        # Process all sessions
        worker = EnhancedWorker()
        for session_id in session_ids:
            session = db_session.get(UploadSession, session_id)
            await worker._process_session_batch(session)
        
        # Test batch configuration endpoint for system metrics
        batch_config_response = client.get("/api/batch-config")
        assert batch_config_response.status_code == 200
        
        config_data = batch_config_response.json()
        
        # Verify performance metrics are collected
        assert "performance_metrics" in config_data
        assert "system_status" in config_data
        assert "constitutional_compliance" in config_data
        
        performance_metrics = config_data["performance_metrics"]
        
        # Verify key performance indicators
        assert "average_cost_savings" in performance_metrics
        assert "system_success_rate" in performance_metrics
        assert "average_processing_speed" in performance_metrics
        
        # Verify constitutional compliance at system level
        system_compliance = config_data["constitutional_compliance"]
        assert system_compliance["overall_compliance"] == True
        
        # Test system-wide constitutional validation
        constitutional_validator = ConstitutionalValidator()
        system_compliance_result = await constitutional_validator.validate_system_compliance(db_session)
        
        assert system_compliance_result.is_compliant == True
        assert system_compliance_result.metrics["success_rate_percentage"] >= settings.CONSTITUTIONAL_MIN_SUCCESS_RATE_PERCENTAGE
    
    @pytest.mark.asyncio 
    async def test_concurrent_session_processing(
        self,
        client,
        db_session,
        sample_interaction_data,
        mock_gemini_service
    ):
        """Test concurrent session processing within constitutional limits."""
        
        # Upload multiple sessions simultaneously
        session_ids = []
        
        for i in range(settings.MAX_CONCURRENT_BATCH_SESSIONS + 1):  # One more than max
            upload_response = client.post(
                "/api/upload-json-enhanced", 
                files={"file": (f"test_interactions_{i}.json", json.dumps(sample_interaction_data[:10]), "application/json")},
                data={"batch_strategy": "small"}
            )
            
            session_ids.append(upload_response.json()["session_id"])
        
        # Simulate concurrent processing
        worker = EnhancedWorker()
        
        # Process sessions (should respect concurrency limits)
        start_time = time.time()
        
        tasks = []
        for session_id in session_ids:
            session = db_session.get(UploadSession, session_id)
            task = asyncio.create_task(worker._process_session_batch(session))
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        
        end_time = time.time()
        total_processing_time = end_time - start_time
        
        # Verify all sessions completed
        for session_id in session_ids:
            session = db_session.get(UploadSession, session_id)
            db_session.refresh(session)
            assert session.status in ["completed", "processing"]  # Some may still be processing due to limits
        
        # Verify constitutional compliance for completed sessions
        completed_sessions = [
            db_session.get(UploadSession, sid) 
            for sid in session_ids 
            if db_session.get(UploadSession, sid).status == "completed"
        ]
        
        for session in completed_sessions:
            assert session.cost_saved_percentage >= settings.CONSTITUTIONAL_MIN_COST_REDUCTION_PERCENTAGE
            
            if session.processing_time_seconds:
                interactions_per_second = session.interactions_processed / session.processing_time_seconds
                assert settings.CONSTITUTIONAL_MIN_INTERACTIONS_PER_SECOND <= interactions_per_second <= settings.CONSTITUTIONAL_MAX_INTERACTIONS_PER_SECOND
    
    @pytest.mark.asyncio
    async def test_data_integrity_validation(
        self,
        client,
        db_session,
        sample_interaction_data,
        mock_gemini_service
    ):
        """Test data integrity and referential integrity throughout workflow."""
        
        # Upload session
        upload_response = client.post(
            "/api/upload-json-enhanced",
            files={"file": ("test_interactions.json", json.dumps(sample_interaction_data), "application/json")},
            data={"batch_strategy": "medium"}
        )
        
        session_id = upload_response.json()["session_id"]
        session = db_session.get(UploadSession, session_id)
        
        # Process session
        worker = EnhancedWorker()
        await worker._process_session_batch(session)
        
        db_session.refresh(session)
        
        # Verify data integrity
        # 1. Session exists and is complete
        assert session is not None
        assert session.status == "completed"
        
        # 2. Batch contexts exist and are linked properly
        batch_contexts = db_session.query(BatchContext).filter(
            BatchContext.session_id == session_id
        ).all()
        
        assert len(batch_contexts) > 0
        
        for batch_context in batch_contexts:
            assert batch_context.session_id == session_id
            assert batch_context.status == "completed"
            assert batch_context.ai_insights is not None
        
        # 3. No orphaned records
        constitutional_validator = ConstitutionalValidator()
        integrity_result = await constitutional_validator._validate_data_integrity(db_session)
        
        assert integrity_result["is_compliant"] == True
        assert integrity_result["metrics"]["orphaned_jobs"] == 0
        
        # 4. All required fields populated
        assert session.interactions_count > 0
        assert session.cost_saved_percentage is not None
        assert session.processing_time_seconds is not None
        assert session.completed_at is not None
        
        # 5. Constitutional compliance data exists
        compliance_result = await constitutional_validator.validate_session_compliance(
            session_id, db_session
        )
        
        assert compliance_result.is_compliant == True
        assert len(compliance_result.violations) == 0
        assert len(compliance_result.metrics) > 0