"""
Constitutional Service Unit Tests
Unit tests for all newly implemented services to ensure constitutional compliance.

CONSTITUTIONAL REQUIREMENT: All service modifications must have unit tests that pass.
"""

import pytest
import tempfile
import json
import os
import sys
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock
from sqlalchemy.orm import Session

# Add the parent directory to the Python path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the services we need to test
from services.upload_session_service import UploadSessionService
from services.batch_processing_service import BatchProcessingService
from services.constitutional_validator import ConstitutionalValidator, ComplianceResult
from models import UploadSession, Job, BatchContext
from database import get_db


class TestUploadSessionService:
    """Constitutional unit tests for UploadSessionService."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock(spec=Session)
    
    @pytest.fixture
    def service(self, mock_db):
        """Create service instance with mocked dependencies."""
        return UploadSessionService(mock_db)
    
    @pytest.fixture
    def sample_interactions(self):
        """Sample interaction data for testing."""
        return [
            {
                "conversation_id": "test_conv_1",
                "timestamp": "2024-09-17T10:00:00Z",
                "messages": [
                    {"role": "user", "content": "Test message 1", "timestamp": "2024-09-17T10:00:00Z"},
                    {"role": "assistant", "content": "Test response 1", "timestamp": "2024-09-17T10:01:00Z"}
                ]
            }
        ]
    
    def test_create_upload_session_success(self, service, mock_db, sample_interactions):
        """Test successful session creation with constitutional compliance."""
        # Arrange
        with patch('services.upload_session_service.uuid4') as mock_uuid:
            mock_uuid.return_value.hex = 'test-session-id'
            
            # Mock database operations
            mock_db.add = Mock()
            mock_db.commit = Mock()
            mock_db.refresh = Mock()
            
            # Act
            result = service.create_upload_session(
                interactions=sample_interactions,
                batch_strategy="auto",
                priority="normal"
            )
            
            # Assert
            assert result["session_id"] == "test-session-id"
            assert result["status"] == "created"
            assert result["batch_strategy"] == "auto"
            assert "estimated_cost_savings" in result
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()
    
    def test_create_upload_session_validation_error(self, service, sample_interactions):
        """Test session creation with invalid data."""
        # Arrange - Invalid interactions (missing required fields)
        invalid_interactions = [{"invalid": "data"}]
        
        # Act & Assert
        with pytest.raises(ValueError, match="Invalid interaction format"):
            service.create_upload_session(
                interactions=invalid_interactions,
                batch_strategy="auto",
                priority="normal"
            )
    
    def test_get_session_status_exists(self, service, mock_db):
        """Test getting status of existing session."""
        # Arrange
        mock_session = Mock()
        mock_session.id = "test-session-id"
        mock_session.status = "processing"
        mock_session.created_at = datetime.now()
        mock_session.interactions_count = 25
        mock_session.batch_strategy = "auto"
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_session
        
        # Act
        result = service.get_session_status("test-session-id")
        
        # Assert
        assert result["session_id"] == "test-session-id"
        assert result["status"] == "processing"
        assert result["interactions_count"] == 25
        assert result["batch_strategy"] == "auto"
    
    def test_get_session_status_not_found(self, service, mock_db):
        """Test getting status of non-existent session."""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Act & Assert
        with pytest.raises(ValueError, match="Session not found"):
            service.get_session_status("non-existent-session")
    
    def test_retry_failed_session_success(self, service, mock_db):
        """Test retrying a failed session."""
        # Arrange
        mock_session = Mock()
        mock_session.id = "test-session-id"
        mock_session.status = "failed"
        mock_session.retry_count = 1
        mock_session.max_retries = 3
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_session
        mock_db.commit = Mock()
        
        # Act
        result = service.retry_failed_session("test-session-id")
        
        # Assert
        assert result["session_id"] == "test-session-id"
        assert result["status"] == "pending_retry"
        assert mock_session.retry_count == 2
        assert mock_session.status == "pending_retry"
        mock_db.commit.assert_called_once()
    
    def test_retry_failed_session_max_retries_exceeded(self, service, mock_db):
        """Test retrying a session that has exceeded max retries."""
        # Arrange
        mock_session = Mock()
        mock_session.id = "test-session-id"
        mock_session.status = "failed"
        mock_session.retry_count = 3
        mock_session.max_retries = 3
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_session
        
        # Act & Assert
        with pytest.raises(ValueError, match="Maximum retries exceeded"):
            service.retry_failed_session("test-session-id")


class TestBatchProcessingService:
    """Constitutional unit tests for BatchProcessingService."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock(spec=Session)
    
    @pytest.fixture
    def service(self, mock_db):
        """Create service instance with mocked dependencies."""
        return BatchProcessingService(mock_db)
    
    @pytest.fixture
    def mock_session(self):
        """Mock upload session."""
        session = Mock()
        session.id = "test-session-id"
        session.status = "processing"
        session.interactions_count = 50
        session.batch_strategy = "aggressive"
        return session
    
    @pytest.mark.asyncio
    async def test_process_session_batches_success(self, service, mock_db, mock_session):
        """Test successful batch processing with constitutional compliance."""
        # Arrange
        mock_jobs = [Mock(id=f"job_{i}", interaction_data={}) for i in range(10)]
        mock_db.query.return_value.filter.return_value.all.return_value = mock_jobs
        
        with patch.object(service, '_create_constitutional_batch_prompt') as mock_prompt:
            mock_prompt.return_value = "Constitutional batch prompt"
            
            with patch.object(service, '_call_gemini_api') as mock_gemini:
                mock_gemini.return_value = {"status": "success", "results": []}
                
                with patch.object(service, '_update_job_results') as mock_update:
                    mock_update.return_value = None
                    
                    # Act
                    result = await service.process_session_batches(mock_session)
                    
                    # Assert
                    assert "batch_results" in result
                    assert "cost_savings" in result
                    mock_prompt.assert_called()
                    mock_gemini.assert_called()
    
    def test_create_constitutional_batch_prompt(self, service):
        """Test constitutional batch prompt creation."""
        # Arrange
        jobs = [
            Mock(interaction_data={"conversation_id": "conv1", "messages": []}),
            Mock(interaction_data={"conversation_id": "conv2", "messages": []})
        ]
        
        # Act
        prompt = service._create_constitutional_batch_prompt(jobs, "aggressive")
        
        # Assert
        assert "CONSTITUTIONAL REQUIREMENTS" in prompt
        assert "AI MICRO-METRICS SUPREMACY" in prompt
        assert "DUAL CSI ARCHITECTURE" in prompt
        assert "80% cost reduction" in prompt
        assert "3-4 interactions per second" in prompt
    
    def test_optimize_batch_for_cost_reduction(self, service):
        """Test batch optimization for cost reduction."""
        # Arrange
        jobs = [Mock() for _ in range(100)]
        
        # Act
        optimized_batches = service._optimize_batch_for_cost_reduction(jobs, "aggressive")
        
        # Assert
        assert len(optimized_batches) > 0
        # Aggressive strategy should create larger batches for cost efficiency
        assert all(len(batch) >= 8 for batch in optimized_batches)
    
    def test_calculate_cost_savings(self, service):
        """Test cost savings calculation."""
        # Arrange
        original_count = 100
        batched_count = 20
        
        # Act
        savings = service._calculate_cost_savings(original_count, batched_count)
        
        # Assert
        assert savings == 80.0  # 80% reduction
    
    def test_get_batch_configuration(self, service):
        """Test batch configuration retrieval."""
        # Act
        config = service.get_batch_configuration()
        
        # Assert
        assert "batch_settings" in config
        assert "performance_metrics" in config
        assert "system_status" in config
        assert config["batch_settings"]["enabled"] is True
        assert config["performance_metrics"]["target_cost_reduction"] == 80


class TestConstitutionalValidator:
    """Constitutional unit tests for ConstitutionalValidator."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock(spec=Session)
    
    @pytest.fixture
    def validator(self, mock_db):
        """Create validator instance with mocked dependencies."""
        return ConstitutionalValidator(mock_db)
    
    @pytest.fixture
    def mock_session(self):
        """Mock upload session for validation."""
        session = Mock()
        session.id = "test-session-id"
        session.status = "completed"
        session.interactions_count = 100
        session.batch_strategy = "aggressive"
        session.created_at = datetime.now()
        return session
    
    def test_validate_session_compliance_success(self, validator, mock_db, mock_session):
        """Test successful session compliance validation."""
        # Arrange
        mock_jobs = []
        for i in range(100):
            job = Mock()
            job.csi_score = 0.85  # Above threshold
            job.processing_time = 0.25  # 4 per second
            job.cost_per_interaction = 0.002  # Reduced cost
            mock_jobs.append(job)
        
        mock_db.query.return_value.filter.return_value.all.return_value = mock_jobs
        
        # Act
        result = validator.validate_session_compliance("test-session-id")
        
        # Assert
        assert isinstance(result, ComplianceResult)
        assert result.is_compliant is True
        assert len(result.violations) == 0
        assert result.constitutional_requirements["ai_supremacy"]["status"] == "compliant"
        assert result.constitutional_requirements["dual_csi_architecture"]["status"] == "compliant"
        assert result.constitutional_requirements["cost_reduction"]["status"] == "compliant"
    
    def test_validate_session_compliance_violations(self, validator, mock_db, mock_session):
        """Test session compliance validation with violations."""
        # Arrange
        mock_jobs = []
        for i in range(50):
            job = Mock()
            job.csi_score = 0.70  # Below threshold (0.75)
            job.processing_time = 0.5   # 2 per second (below 3-4 target)
            job.cost_per_interaction = 0.01  # Higher cost (not reduced)
            mock_jobs.append(job)
        
        mock_db.query.return_value.filter.return_value.all.return_value = mock_jobs
        
        # Act
        result = validator.validate_session_compliance("test-session-id")
        
        # Assert
        assert isinstance(result, ComplianceResult)
        assert result.is_compliant is False
        assert len(result.violations) > 0
        assert any("CSI score" in violation for violation in result.violations)
        assert any("processing speed" in violation for violation in result.violations)
    
    def test_validate_system_compliance(self, validator, mock_db):
        """Test system-wide compliance validation."""
        # Arrange
        mock_sessions = []
        for i in range(10):
            session = Mock()
            session.status = "completed"
            session.interactions_count = 50
            mock_sessions.append(session)
        
        mock_db.query.return_value.filter.return_value.all.return_value = mock_sessions
        
        mock_jobs = []
        for i in range(500):
            job = Mock()
            job.csi_score = 0.80
            job.processing_time = 0.30
            job.cost_per_interaction = 0.002
            mock_jobs.append(job)
        
        # Mock the jobs query to return our mock jobs
        def mock_query_side_effect(*args):
            mock_query = Mock()
            if args[0] == Job:
                mock_query.all.return_value = mock_jobs
            else:
                mock_query.filter.return_value.all.return_value = mock_sessions
            return mock_query
        
        mock_db.query.side_effect = mock_query_side_effect
        
        # Act
        result = validator.validate_system_compliance()
        
        # Assert
        assert isinstance(result, ComplianceResult)
        assert "system_metrics" in result.constitutional_requirements
    
    def test_compliance_result_creation(self, validator):
        """Test ComplianceResult dataclass creation."""
        # Arrange
        violations = ["Test violation 1", "Test violation 2"]
        requirements = {
            "ai_supremacy": {"status": "compliant", "details": "All metrics above threshold"},
            "dual_csi_architecture": {"status": "non_compliant", "details": "Some scores below 0.75"}
        }
        
        # Act
        result = ComplianceResult(
            is_compliant=False,
            violations=violations,
            constitutional_requirements=requirements,
            session_id="test-session"
        )
        
        # Assert
        assert result.is_compliant is False
        assert len(result.violations) == 2
        assert result.session_id == "test-session"
        assert result.constitutional_requirements["ai_supremacy"]["status"] == "compliant"
        assert result.constitutional_requirements["dual_csi_architecture"]["status"] == "non_compliant"


def run_constitutional_tests():
    """Run all constitutional service unit tests."""
    print("🚨 CONSTITUTIONAL SERVICE UNIT TESTS")
    print("=" * 60)
    
    # Run pytest with specific test file
    import subprocess
    import sys
    
    try:
        # Run the tests
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            __file__, 
            "-v", 
            "--tb=short",
            "--color=yes"
        ], capture_output=True, text=True)
        
        print("STDOUT:")
        print(result.stdout)
        
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        
        print(f"\n📊 TEST EXIT CODE: {result.returncode}")
        
        if result.returncode == 0:
            print("✅ ALL CONSTITUTIONAL SERVICE TESTS PASSED")
            return True
        else:
            print("❌ CONSTITUTIONAL SERVICE TEST FAILURES DETECTED")
            return False
            
    except Exception as e:
        print(f"❌ ERROR RUNNING CONSTITUTIONAL TESTS: {e}")
        return False


if __name__ == "__main__":
    success = run_constitutional_tests()
    exit(0 if success else 1)