"""
Constitutional Compliance Integration Tests
Tests ensuring AI micro-metrics supremacy and dual CSI architecture throughout the system.

This test suite validates:
1. AI Micro-Metrics Supremacy requirements
2. Dual CSI Architecture (calculated + inferred CSI)
3. Constitutional cost reduction requirements (80% minimum)
4. Processing speed constitutional compliance (3-4 interactions/second)
5. System success rate requirements (95% minimum)
6. Data integrity and constitutional validation
7. Constitutional compliance monitoring and alerting
"""

import pytest
import asyncio
import json
import uuid
from typing import Dict, Any, List
from unittest.mock import AsyncMock, patch, MagicMock

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from main import app
from database import SessionLocal
from models import UploadSession, BatchContext, Job, DailyAnalysis, Interaction
from services.upload_session_service import UploadSessionService
from services.batch_processing_service import BatchProcessingService
from services.constitutional_validator import ConstitutionalValidator, ComplianceResult
from config import settings
from worker import EnhancedWorker


class TestConstitutionalCompliance:
    """Comprehensive constitutional compliance integration tests."""
    
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
    def constitutional_test_data(self) -> List[Dict[str, Any]]:
        """Test data designed for constitutional compliance validation."""
        return [
            {
                "conversation_id": f"constitutional_conv_{i}",
                "timestamp": f"2024-01-{i:02d}T10:00:00Z",
                "messages": [
                    {
                        "role": "user",
                        "content": f"Constitutional compliance test user message {i}",
                        "timestamp": f"2024-01-{i:02d}T10:00:00Z"
                    },
                    {
                        "role": "assistant",
                        "content": f"Constitutional compliance test assistant response {i}",
                        "timestamp": f"2024-01-{i:02d}T10:01:00Z"
                    }
                ]
            }
            for i in range(1, 101)  # 100 interactions for comprehensive testing
        ]
    
    @pytest.fixture
    def mock_constitutional_gemini_service(self):
        """Mock Gemini service that produces constitutionally compliant responses."""
        with patch('services.batch_processing_service.gemini_service') as mock:
            # Simulate constitutional compliance with proper dual CSI
            mock.analyze_interactions_batch = AsyncMock(return_value={
                'success': True,
                'results': [
                    {
                        'conversation_id': f'constitutional_conv_{i}',
                        'calculated_csi': 0.80 + (i % 15) * 0.01,  # 0.80-0.94 range
                        'inferred_csi': 0.82 + (i % 13) * 0.01,    # 0.82-0.94 range  
                        'ai_insights': f'AI micro-metrics supremacy insights for conversation {i}: Advanced pattern analysis indicates optimal interaction quality with constitutional compliance validation.',
                        'constitutional_metrics': {
                            'ai_supremacy_score': 0.95,  # High AI supremacy
                            'dual_csi_compliance': True,
                            'micro_metrics_quality': 'excellent'
                        },
                        'processing_metadata': {
                            'tokens_used': 200 + (i % 50) * 2,
                            'cost_usd': 0.00020 * (200 + (i % 50) * 2) / 1000,
                            'processing_time_ms': 750 + (i % 200) * 5,
                            'ai_enhancement_applied': True
                        }
                    }
                    for i in range(1, 101)
                ],
                'cost_saved_percentage': 83.5,  # Above constitutional minimum
                'processing_time_seconds': 28.5,  # ~3.5 interactions/second (within constitutional range)
                'total_tokens_saved': 18000,
                'batch_optimization_applied': True,
                'constitutional_compliance': {
                    'ai_supremacy_achieved': True,
                    'dual_csi_enforced': True,
                    'cost_reduction_compliant': True,
                    'processing_speed_compliant': True
                }
            })
            
            yield mock
    
    @pytest.fixture
    def mock_non_compliant_gemini_service(self):
        """Mock Gemini service that produces non-compliant responses for testing violation detection."""
        with patch('services.batch_processing_service.gemini_service') as mock:
            # Simulate constitutional violations for testing
            mock.analyze_interactions_batch = AsyncMock(return_value={
                'success': True,
                'results': [
                    {
                        'conversation_id': f'constitutional_conv_{i}',
                        'calculated_csi': 0.70 + (i % 10) * 0.02 if i % 3 != 0 else None,  # Missing calculated_csi for some
                        'inferred_csi': 0.72 + (i % 8) * 0.02 if i % 4 != 0 else None,     # Missing inferred_csi for some
                        'ai_insights': f'Limited insights for conversation {i}' if i % 5 == 0 else None,  # Missing AI insights
                        'processing_metadata': {
                            'tokens_used': 180 + (i % 30) * 3,
                            'cost_usd': 0.00030 * (180 + (i % 30) * 3) / 1000,  # Higher cost
                            'processing_time_ms': 1200 + (i % 300) * 8  # Slower processing
                        }
                    }
                    for i in range(1, 21)
                ],
                'cost_saved_percentage': 65.0,  # Below constitutional minimum (80%)
                'processing_time_seconds': 45.0,  # ~0.47 interactions/second (below constitutional minimum)
                'total_tokens_saved': 8000,
                'batch_optimization_applied': False,
                'constitutional_compliance': {
                    'ai_supremacy_achieved': False,
                    'dual_csi_enforced': False,
                    'cost_reduction_compliant': False,
                    'processing_speed_compliant': False
                }
            })
            
            yield mock
    
    @pytest.mark.asyncio
    async def test_ai_micro_metrics_supremacy_compliance(
        self,
        client,
        db_session,
        constitutional_test_data,
        mock_constitutional_gemini_service
    ):
        """Test AI micro-metrics supremacy constitutional requirement."""
        
        # Upload session for AI supremacy testing
        upload_response = client.post(
            "/api/upload-json-enhanced",
            files={"file": ("ai_supremacy_test.json", json.dumps(constitutional_test_data), "application/json")},
            data={"batch_strategy": "large"}
        )
        
        assert upload_response.status_code == 200
        session_id = upload_response.json()["session_id"]
        
        # Process session
        worker = EnhancedWorker()
        session = db_session.get(UploadSession, session_id)
        await worker._process_session_batch(session)
        
        db_session.refresh(session)
        
        # Validate AI micro-metrics supremacy
        constitutional_validator = ConstitutionalValidator()
        compliance_result = await constitutional_validator.validate_session_compliance(
            session_id, db_session
        )
        
        assert compliance_result.is_compliant == True
        
        # Specific AI supremacy validations
        metrics = compliance_result.metrics
        
        # AI insights coverage must meet constitutional requirement
        ai_insights_coverage = metrics.get("ai_insights_coverage", 0)
        assert ai_insights_coverage >= settings.REQUIRED_AI_INSIGHTS_COVERAGE_PERCENTAGE
        
        # Verify AI-generated insights exist in batch contexts
        batch_contexts = db_session.query(BatchContext).filter(
            BatchContext.session_id == session_id
        ).all()
        
        ai_insights_count = sum(1 for bc in batch_contexts if bc.ai_insights)
        ai_coverage_actual = (ai_insights_count / len(batch_contexts) * 100) if batch_contexts else 0
        
        assert ai_coverage_actual >= settings.REQUIRED_AI_INSIGHTS_COVERAGE_PERCENTAGE
        
        # Validate AI-driven cost optimization
        assert session.cost_saved_percentage >= settings.CONSTITUTIONAL_MIN_COST_REDUCTION_PERCENTAGE
        
        # Test constitutional compliance endpoint for AI supremacy
        compliance_response = client.get(f"/api/constitutional/compliance?session_id={session_id}")
        assert compliance_response.status_code == 200
        
        compliance_data = compliance_response.json()
        assert compliance_data["constitutional_requirements"]["ai_supremacy"]["status"] == "compliant"
        assert compliance_data["constitutional_requirements"]["ai_supremacy"]["coverage_percentage"] >= settings.REQUIRED_AI_INSIGHTS_COVERAGE_PERCENTAGE
    
    @pytest.mark.asyncio
    async def test_dual_csi_architecture_compliance(
        self,
        client,
        db_session,
        constitutional_test_data,
        mock_constitutional_gemini_service
    ):
        """Test dual CSI architecture constitutional requirement."""
        
        # Upload session for dual CSI testing
        upload_response = client.post(
            "/api/upload-json-enhanced",
            files={"file": ("dual_csi_test.json", json.dumps(constitutional_test_data), "application/json")},
            data={"batch_strategy": "medium"}
        )
        
        session_id = upload_response.json()["session_id"]
        
        # Process session
        worker = EnhancedWorker()
        session = db_session.get(UploadSession, session_id)
        await worker._process_session_batch(session)
        
        # Validate dual CSI compliance
        constitutional_validator = ConstitutionalValidator()
        compliance_result = await constitutional_validator.validate_session_compliance(
            session_id, db_session
        )
        
        assert compliance_result.is_compliant == True
        
        # Validate dual CSI architecture metrics
        metrics = compliance_result.metrics
        
        # CSI completeness must meet constitutional threshold
        csi_completeness = metrics.get("csi_completeness_percentage", 0)
        assert csi_completeness >= settings.CSI_COMPLETENESS_THRESHOLD_PERCENTAGE
        
        # Verify both calculated and inferred CSI are present
        assert metrics.get("missing_calculated_csi", 0) == 0
        assert metrics.get("missing_inferred_csi", 0) == 0
        
        # Test direct database validation
        interactions_query = (
            db_session.query(Interaction)
            .join(DailyAnalysis)
            .join(Job)
            .filter(Job.upload_id == session_id)
        )
        
        total_interactions = interactions_query.count()
        if total_interactions > 0:  # Only test if interactions exist
            missing_calculated = interactions_query.filter(Interaction.calculated_csi.is_(None)).count()
            missing_inferred = interactions_query.filter(Interaction.inferred_csi.is_(None)).count()
            
            assert missing_calculated == 0, f"Found {missing_calculated} interactions missing calculated_csi"
            assert missing_inferred == 0, f"Found {missing_inferred} interactions missing inferred_csi"
        
        # Test constitutional compliance endpoint for dual CSI
        compliance_response = client.get(f"/api/constitutional/compliance?session_id={session_id}")
        compliance_data = compliance_response.json()
        
        dual_csi_status = compliance_data["constitutional_requirements"]["dual_csi_architecture"]
        assert dual_csi_status["status"] == "compliant"
        assert dual_csi_status["calculated_csi_completeness"] == 100.0
        assert dual_csi_status["inferred_csi_completeness"] == 100.0
    
    @pytest.mark.asyncio
    async def test_cost_reduction_constitutional_compliance(
        self,
        client,
        db_session,
        constitutional_test_data,
        mock_constitutional_gemini_service
    ):
        """Test 80% cost reduction constitutional requirement."""
        
        # Test multiple file sizes for consistent cost reduction
        test_scenarios = [
            {"name": "small_file", "interactions": 25, "strategy": "small"},
            {"name": "medium_file", "interactions": 75, "strategy": "medium"}, 
            {"name": "large_file", "interactions": 150, "strategy": "large"}
        ]
        
        for scenario in test_scenarios:
            interactions = constitutional_test_data[:scenario["interactions"]]
            
            upload_response = client.post(
                "/api/upload-json-enhanced",
                files={"file": (f"cost_reduction_{scenario['name']}.json", json.dumps(interactions), "application/json")},
                data={"batch_strategy": scenario["strategy"]}
            )
            
            session_id = upload_response.json()["session_id"]
            
            # Process session
            worker = EnhancedWorker()
            session = db_session.get(UploadSession, session_id)
            await worker._process_session_batch(session)
            
            db_session.refresh(session)
            
            # Validate cost reduction compliance
            assert session.cost_saved_percentage >= settings.CONSTITUTIONAL_MIN_COST_REDUCTION_PERCENTAGE
            
            # Validate constitutional compliance
            constitutional_validator = ConstitutionalValidator()
            compliance_result = await constitutional_validator.validate_session_compliance(
                session_id, db_session
            )
            
            assert compliance_result.is_compliant == True
            
            # No cost reduction violations should exist
            cost_violations = [v for v in compliance_result.violations if "cost reduction" in v.lower()]
            assert len(cost_violations) == 0
            
            # Verify cost reduction metrics
            assert compliance_result.metrics["cost_saved_percentage"] >= settings.CONSTITUTIONAL_MIN_COST_REDUCTION_PERCENTAGE
        
        # Test system-wide cost reduction compliance
        constitutional_validator = ConstitutionalValidator()
        system_compliance = await constitutional_validator.validate_system_compliance(db_session)
        
        assert system_compliance.metrics["average_cost_savings"] >= settings.CONSTITUTIONAL_MIN_COST_REDUCTION_PERCENTAGE
    
    @pytest.mark.asyncio
    async def test_processing_speed_constitutional_compliance(
        self,
        client,
        db_session,
        constitutional_test_data,
        mock_constitutional_gemini_service
    ):
        """Test 3-4 interactions/second processing speed constitutional requirement."""
        
        # Upload session for processing speed testing
        upload_response = client.post(
            "/api/upload-json-enhanced",
            files={"file": ("processing_speed_test.json", json.dumps(constitutional_test_data), "application/json")},
            data={"batch_strategy": "large"}
        )
        
        session_id = upload_response.json()["session_id"]
        
        # Process session
        worker = EnhancedWorker()
        session = db_session.get(UploadSession, session_id)
        await worker._process_session_batch(session)
        
        db_session.refresh(session)
        
        # Validate processing speed compliance
        interactions_per_second = session.interactions_processed / session.processing_time_seconds
        
        assert settings.CONSTITUTIONAL_MIN_INTERACTIONS_PER_SECOND <= interactions_per_second <= settings.CONSTITUTIONAL_MAX_INTERACTIONS_PER_SECOND
        
        # Validate constitutional compliance
        constitutional_validator = ConstitutionalValidator()
        compliance_result = await constitutional_validator.validate_session_compliance(
            session_id, db_session
        )
        
        assert compliance_result.is_compliant == True
        
        # No processing speed violations should exist
        speed_violations = [v for v in compliance_result.violations if "processing speed" in v.lower() or "interactions/second" in v.lower()]
        assert len(speed_violations) == 0
        
        # Test constitutional compliance endpoint for processing speed
        compliance_response = client.get(f"/api/constitutional/compliance?session_id={session_id}")
        compliance_data = compliance_response.json()
        
        processing_speed_status = compliance_data["constitutional_requirements"]["processing_speed"]
        assert processing_speed_status["status"] == "compliant"
        assert settings.CONSTITUTIONAL_MIN_INTERACTIONS_PER_SECOND <= processing_speed_status["interactions_per_second"] <= settings.CONSTITUTIONAL_MAX_INTERACTIONS_PER_SECOND
    
    @pytest.mark.asyncio
    async def test_constitutional_violation_detection(
        self,
        client,
        db_session,
        constitutional_test_data,
        mock_non_compliant_gemini_service
    ):
        """Test detection of constitutional violations."""
        
        # Upload session that will produce violations
        upload_response = client.post(
            "/api/upload-json-enhanced",
            files={"file": ("violation_test.json", json.dumps(constitutional_test_data[:20]), "application/json")},
            data={"batch_strategy": "small"}
        )
        
        session_id = upload_response.json()["session_id"]
        
        # Process session (should produce violations)
        worker = EnhancedWorker()
        session = db_session.get(UploadSession, session_id)
        await worker._process_session_batch(session)
        
        db_session.refresh(session)
        
        # Validate that violations are detected
        constitutional_validator = ConstitutionalValidator()
        compliance_result = await constitutional_validator.validate_session_compliance(
            session_id, db_session
        )
        
        # Session should NOT be compliant
        assert compliance_result.is_compliant == False
        assert len(compliance_result.violations) > 0
        
        # Verify specific violation types are detected
        violation_messages = " ".join(compliance_result.violations).lower()
        
        # Cost reduction violation should be detected
        assert "cost reduction" in violation_messages
        
        # Processing speed violation should be detected
        assert "processing speed" in violation_messages or "interactions/second" in violation_messages
        
        # CSI violations should be detected
        assert "csi" in violation_messages
        
        # Verify constitutional violations are stored in session
        assert session.constitutional_violations is not None
        assert len(session.constitutional_violations) > 0
        
        # Test constitutional compliance endpoint reports violations
        compliance_response = client.get(f"/api/constitutional/compliance?session_id={session_id}")
        compliance_data = compliance_response.json()
        
        assert compliance_data["is_compliant"] == False
        assert len(compliance_data["violations"]) > 0
        assert len(compliance_data["recommendations"]) > 0
    
    @pytest.mark.asyncio
    async def test_system_wide_constitutional_compliance(
        self,
        client,
        db_session,
        constitutional_test_data,
        mock_constitutional_gemini_service
    ):
        """Test system-wide constitutional compliance validation."""
        
        # Create multiple sessions for system-wide testing
        session_ids = []
        
        for i in range(5):
            interactions = constitutional_test_data[i*20:(i+1)*20]  # 20 interactions each
            
            upload_response = client.post(
                "/api/upload-json-enhanced",
                files={"file": (f"system_test_{i}.json", json.dumps(interactions), "application/json")},
                data={"batch_strategy": "small"}
            )
            
            session_ids.append(upload_response.json()["session_id"])
        
        # Process all sessions
        worker = EnhancedWorker()
        
        for session_id in session_ids:
            session = db_session.get(UploadSession, session_id)
            await worker._process_session_batch(session)
        
        # Validate system-wide constitutional compliance
        constitutional_validator = ConstitutionalValidator()
        system_compliance = await constitutional_validator.validate_system_compliance(db_session)
        
        assert system_compliance.is_compliant == True
        assert len(system_compliance.violations) == 0
        
        # Verify system metrics meet constitutional requirements
        metrics = system_compliance.metrics
        
        # System success rate must meet constitutional minimum
        assert metrics["success_rate_percentage"] >= settings.CONSTITUTIONAL_MIN_SUCCESS_RATE_PERCENTAGE
        
        # Average cost savings must meet constitutional minimum
        assert metrics["average_cost_savings"] >= settings.CONSTITUTIONAL_MIN_COST_REDUCTION_PERCENTAGE
        
        # Test system-wide constitutional compliance endpoint
        system_compliance_response = client.get("/api/constitutional/compliance")
        assert system_compliance_response.status_code == 200
        
        system_compliance_data = system_compliance_response.json()
        assert system_compliance_data["system_compliance"]["overall_status"] == "compliant"
        assert system_compliance_data["system_compliance"]["success_rate"] >= settings.CONSTITUTIONAL_MIN_SUCCESS_RATE_PERCENTAGE
    
    @pytest.mark.asyncio
    async def test_constitutional_monitoring_and_alerting(
        self,
        client,
        db_session,
        constitutional_test_data,
        mock_constitutional_gemini_service
    ):
        """Test constitutional compliance monitoring and alerting systems."""
        
        # Upload session for monitoring testing
        upload_response = client.post(
            "/api/upload-json-enhanced",
            files={"file": ("monitoring_test.json", json.dumps(constitutional_test_data), "application/json")},
            data={"batch_strategy": "large"}
        )
        
        session_id = upload_response.json()["session_id"]
        
        # Process session with monitoring
        worker = EnhancedWorker()
        session = db_session.get(UploadSession, session_id)
        
        # Simulate worker constitutional compliance validation
        await worker._process_session_batch(session)
        
        # Test periodic constitutional compliance validation
        compliance_check_start = asyncio.get_event_loop().time()
        await worker._validate_constitutional_compliance()
        compliance_check_time = asyncio.get_event_loop().time() - compliance_check_start
        
        # Constitutional validation should be fast (under 5 seconds)
        assert compliance_check_time < 5.0
        
        # Test batch configuration endpoint for monitoring data
        batch_config_response = client.get("/api/batch-config")
        assert batch_config_response.status_code == 200
        
        config_data = batch_config_response.json()
        
        # Verify constitutional compliance monitoring data
        constitutional_status = config_data["constitutional_compliance"]
        assert "overall_compliance" in constitutional_status
        assert "ai_supremacy_status" in constitutional_status
        assert "dual_csi_status" in constitutional_status
        assert "cost_reduction_status" in constitutional_status
        assert "processing_speed_status" in constitutional_status
        
        # All constitutional requirements should be compliant
        assert constitutional_status["overall_compliance"] == True
        assert constitutional_status["ai_supremacy_status"] == "compliant"
        assert constitutional_status["dual_csi_status"] == "compliant"
        assert constitutional_status["cost_reduction_status"] == "compliant"
        assert constitutional_status["processing_speed_status"] == "compliant"
    
    @pytest.mark.asyncio
    async def test_constitutional_data_integrity(
        self,
        client,
        db_session,
        constitutional_test_data,
        mock_constitutional_gemini_service
    ):
        """Test constitutional data integrity requirements."""
        
        # Upload session for data integrity testing
        upload_response = client.post(
            "/api/upload-json-enhanced",
            files={"file": ("data_integrity_test.json", json.dumps(constitutional_test_data), "application/json")},
            data={"batch_strategy": "medium"}
        )
        
        session_id = upload_response.json()["session_id"]
        
        # Process session
        worker = EnhancedWorker()
        session = db_session.get(UploadSession, session_id)
        await worker._process_session_batch(session)
        
        # Validate data integrity
        constitutional_validator = ConstitutionalValidator()
        
        # Test data integrity validation
        integrity_result = await constitutional_validator._validate_data_integrity(db_session)
        
        assert integrity_result["is_compliant"] == True
        assert integrity_result["metrics"]["orphaned_jobs"] == 0
        
        # Verify referential integrity
        session = db_session.get(UploadSession, session_id)
        assert session is not None
        
        # All batch contexts should be linked properly
        batch_contexts = db_session.query(BatchContext).filter(
            BatchContext.session_id == session_id
        ).all()
        
        for batch_context in batch_contexts:
            assert batch_context.session_id == session_id
            assert batch_context.status in ["completed", "processing", "failed"]
        
        # No orphaned batch contexts should exist
        orphaned_batches = db_session.query(BatchContext).filter(
            BatchContext.session_id.notin_(
                db_session.query(UploadSession.session_id)
            )
        ).count()
        
        assert orphaned_batches == 0
        
        # Constitutional compliance should be maintained with data integrity
        compliance_result = await constitutional_validator.validate_session_compliance(
            session_id, db_session
        )
        
        assert compliance_result.is_compliant == True
    
    @pytest.mark.asyncio
    async def test_constitutional_compliance_recovery(
        self,
        client,
        db_session,
        constitutional_test_data,
        mock_non_compliant_gemini_service,
        mock_constitutional_gemini_service
    ):
        """Test constitutional compliance recovery after violations."""
        
        # First attempt with non-compliant service (should fail)
        with patch('services.batch_processing_service.gemini_service', mock_non_compliant_gemini_service):
            upload_response = client.post(
                "/api/upload-json-enhanced",
                files={"file": ("recovery_test.json", json.dumps(constitutional_test_data[:30]), "application/json")},
                data={"batch_strategy": "medium"}
            )
            
            session_id = upload_response.json()["session_id"]
            
            # Process session (should produce violations)
            worker = EnhancedWorker()
            session = db_session.get(UploadSession, session_id)
            await worker._process_session_batch(session)
            
            db_session.refresh(session)
            
            # Should have violations
            constitutional_validator = ConstitutionalValidator()
            compliance_result = await constitutional_validator.validate_session_compliance(
                session_id, db_session
            )
            
            assert compliance_result.is_compliant == False
            assert session.status in ["failed", "retrying"]
        
        # Retry with compliant service (should recover)
        with patch('services.batch_processing_service.gemini_service', mock_constitutional_gemini_service):
            # Test retry endpoint
            retry_response = client.post(f"/api/retry/{session_id}")
            assert retry_response.status_code == 200
            
            # Process retry (should now be compliant)
            session = db_session.get(UploadSession, session_id)
            await worker._process_session_batch(session)
            
            db_session.refresh(session)
            
            # Should now be compliant
            compliance_result = await constitutional_validator.validate_session_compliance(
                session_id, db_session
            )
            
            assert compliance_result.is_compliant == True
            assert session.status == "completed"
            
            # Verify constitutional requirements are now met
            assert session.cost_saved_percentage >= settings.CONSTITUTIONAL_MIN_COST_REDUCTION_PERCENTAGE
            
            if session.processing_time_seconds:
                interactions_per_second = session.interactions_processed / session.processing_time_seconds
                assert settings.CONSTITUTIONAL_MIN_INTERACTIONS_PER_SECOND <= interactions_per_second <= settings.CONSTITUTIONAL_MAX_INTERACTIONS_PER_SECOND
    
    @pytest.mark.asyncio
    async def test_constitutional_compliance_under_load(
        self,
        client,
        db_session,
        constitutional_test_data,
        mock_constitutional_gemini_service
    ):
        """Test constitutional compliance maintained under concurrent load."""
        
        # Create multiple concurrent sessions
        concurrent_sessions = min(settings.MAX_CONCURRENT_BATCH_SESSIONS, 4)
        session_ids = []
        
        for i in range(concurrent_sessions):
            interactions = constitutional_test_data[i*25:(i+1)*25]  # 25 interactions each
            
            upload_response = client.post(
                "/api/upload-json-enhanced",
                files={"file": (f"load_test_{i}.json", json.dumps(interactions), "application/json")},
                data={"batch_strategy": "small"}
            )
            
            session_ids.append(upload_response.json()["session_id"])
        
        # Process all sessions concurrently
        worker = EnhancedWorker()
        
        tasks = []
        for session_id in session_ids:
            session = db_session.get(UploadSession, session_id)
            task = asyncio.create_task(worker._process_session_batch(session))
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        
        # Validate constitutional compliance for all sessions
        constitutional_validator = ConstitutionalValidator()
        
        for session_id in session_ids:
            compliance_result = await constitutional_validator.validate_session_compliance(
                session_id, db_session
            )
            
            # Each session must maintain constitutional compliance under load
            assert compliance_result.is_compliant == True
            assert len(compliance_result.violations) == 0
            
            # Verify key constitutional metrics
            metrics = compliance_result.metrics
            assert metrics["cost_saved_percentage"] >= settings.CONSTITUTIONAL_MIN_COST_REDUCTION_PERCENTAGE
            
            if "interactions_per_second" in metrics:
                assert settings.CONSTITUTIONAL_MIN_INTERACTIONS_PER_SECOND <= metrics["interactions_per_second"] <= settings.CONSTITUTIONAL_MAX_INTERACTIONS_PER_SECOND
        
        # System-wide compliance should also be maintained
        system_compliance = await constitutional_validator.validate_system_compliance(db_session)
        
        assert system_compliance.is_compliant == True
        assert system_compliance.metrics["success_rate_percentage"] >= settings.CONSTITUTIONAL_MIN_SUCCESS_RATE_PERCENTAGE