"""
Performance Validation Tests
Tests ensuring 80% cost reduction, 3-4 interactions/second processing speed, and constitutional compliance.

This test suite validates:
1. Cost reduction targets (80% minimum, 85% target)
2. Processing speed requirements (3-4 interactions/second)
3. Throughput targets (12,000 interactions/hour)
4. Latency requirements (2 second max per interaction)
5. System scalability and performance under load
6. Constitutional performance compliance
"""

import pytest
import asyncio
import json
import time
import statistics
from typing import Dict, Any, List, Tuple
from unittest.mock import AsyncMock, patch
from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from main import app
from database import SessionLocal
from models import UploadSession, BatchContext
from services.upload_session_service import UploadSessionService
from services.batch_processing_service import BatchProcessingService
from services.constitutional_validator import ConstitutionalValidator
from config import settings
from worker import EnhancedWorker


class TestPerformanceValidation:
    """Comprehensive performance validation tests."""
    
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
    def performance_interaction_data(self) -> List[Dict[str, Any]]:
        """Large dataset for performance testing."""
        return [
            {
                "conversation_id": f"perf_conv_{i}",
                "timestamp": f"2024-01-{(i % 30) + 1:02d}T{(i % 24):02d}:00:00Z",
                "messages": [
                    {
                        "role": "user",
                        "content": f"Performance test user message {i} with detailed content to simulate realistic interaction sizes.",
                        "timestamp": f"2024-01-{(i % 30) + 1:02d}T{(i % 24):02d}:00:00Z"
                    },
                    {
                        "role": "assistant",
                        "content": f"Performance test assistant response {i} with comprehensive analysis and detailed explanation to match real-world interaction complexity.",
                        "timestamp": f"2024-01-{(i % 30) + 1:02d}T{(i % 24):02d}:01:00Z"
                    }
                ]
            }
            for i in range(1, 501)  # 500 interactions for load testing
        ]
    
    @pytest.fixture
    def mock_optimized_gemini_service(self):
        """Mock Gemini service optimized for performance testing."""
        with patch('services.batch_processing_service.gemini_service') as mock:
            # Simulate realistic processing times and cost savings
            def create_batch_response(interaction_count: int, batch_size: int) -> Dict[str, Any]:
                # Simulate cost reduction based on batch size
                base_cost_per_interaction = 0.01  # $0.01 per interaction without batching
                individual_cost = base_cost_per_interaction * interaction_count
                
                # Batch processing savings increase with batch size
                batch_efficiency = min(0.9, 0.5 + (batch_size * 0.02))  # Up to 90% efficiency
                batch_cost = individual_cost * (1 - batch_efficiency)
                cost_saved_percentage = ((individual_cost - batch_cost) / individual_cost) * 100
                
                # Simulate processing time based on batch optimization
                base_time_per_interaction = 2.5  # 2.5 seconds per interaction individually
                batch_time_per_interaction = base_time_per_interaction * (1 - (batch_efficiency * 0.8))
                processing_time = interaction_count * batch_time_per_interaction
                
                return {
                    'success': True,
                    'results': [
                        {
                            'conversation_id': f'perf_conv_{i}',
                            'calculated_csi': 0.75 + ((i * 7) % 20) * 0.01,  # 0.75-0.95 range
                            'inferred_csi': 0.77 + ((i * 11) % 18) * 0.01,   # 0.77-0.95 range
                            'ai_insights': f'Performance optimized AI insights for conversation {i}',
                            'processing_metadata': {
                                'tokens_used': 180 + (i % 30) * 5,
                                'cost_usd': batch_cost / interaction_count,
                                'processing_time_ms': (batch_time_per_interaction * 1000) + (i % 100) * 10
                            }
                        }
                        for i in range(1, interaction_count + 1)
                    ],
                    'cost_saved_percentage': cost_saved_percentage,
                    'processing_time_seconds': processing_time,
                    'total_tokens_saved': int(individual_cost * 4000),  # Simulate token savings
                    'batch_optimization_applied': True,
                    'batch_efficiency': batch_efficiency
                }
            
            mock.analyze_interactions_batch = AsyncMock(side_effect=lambda interactions: create_batch_response(len(interactions), len(interactions)))
            
            mock.get_api_cost_estimate = AsyncMock(return_value={
                'estimated_cost_usd': 0.125,
                'estimated_tokens': 5000,
                'cost_reduction_percentage': 82.5
            })
            
            yield mock
    
    @pytest.mark.asyncio
    async def test_cost_reduction_performance(
        self,
        client,
        db_session,
        performance_interaction_data,
        mock_optimized_gemini_service
    ):
        """Test cost reduction performance across different file sizes."""
        
        test_cases = [
            {"name": "Small File", "interactions": 25, "expected_min_savings": 80.0},
            {"name": "Medium File", "interactions": 100, "expected_min_savings": 82.0},
            {"name": "Large File", "interactions": 300, "expected_min_savings": 85.0},
            {"name": "Extra Large File", "interactions": 500, "expected_min_savings": 87.0}
        ]
        
        cost_performance_results = []
        
        for case in test_cases:
            interactions = performance_interaction_data[:case["interactions"]]
            
            # Measure upload time
            start_upload = time.time()
            
            upload_response = client.post(
                "/api/upload-json-enhanced",
                files={"file": ("performance_test.json", json.dumps(interactions), "application/json")},
                data={"batch_strategy": "auto"}
            )
            
            upload_time = time.time() - start_upload
            
            assert upload_response.status_code == 200
            upload_data = upload_response.json()
            
            session_id = upload_data["session_id"]
            session = db_session.get(UploadSession, session_id)
            
            # Measure processing time
            start_processing = time.time()
            
            worker = EnhancedWorker()
            await worker._process_session_batch(session)
            
            processing_time = time.time() - start_processing
            
            db_session.refresh(session)
            
            # Validate cost reduction performance
            assert session.status == "completed"
            assert session.cost_saved_percentage >= case["expected_min_savings"]
            assert session.cost_saved_percentage >= settings.CONSTITUTIONAL_MIN_COST_REDUCTION_PERCENTAGE
            
            # Calculate performance metrics
            interactions_per_second = session.interactions_processed / session.processing_time_seconds
            
            # Validate processing speed constitutional compliance
            assert settings.CONSTITUTIONAL_MIN_INTERACTIONS_PER_SECOND <= interactions_per_second <= settings.CONSTITUTIONAL_MAX_INTERACTIONS_PER_SECOND
            
            cost_performance_results.append({
                "case": case["name"],
                "interactions": case["interactions"],
                "cost_saved_percentage": session.cost_saved_percentage,
                "processing_time": session.processing_time_seconds,
                "interactions_per_second": interactions_per_second,
                "upload_time": upload_time,
                "total_time": upload_time + processing_time
            })
        
        # Log performance results for analysis
        print("\nCost Reduction Performance Results:")
        for result in cost_performance_results:
            print(f"{result['case']}: {result['cost_saved_percentage']:.1f}% savings, "
                  f"{result['interactions_per_second']:.2f} interactions/sec")
        
        # Verify scaling efficiency (larger files should have better cost savings)
        for i in range(1, len(cost_performance_results)):
            current = cost_performance_results[i]
            previous = cost_performance_results[i-1]
            
            # Larger files should achieve better cost savings due to better batching
            assert current["cost_saved_percentage"] >= previous["cost_saved_percentage"] - 2.0  # Allow 2% tolerance
    
    @pytest.mark.asyncio
    async def test_processing_speed_performance(
        self,
        client,
        db_session,
        performance_interaction_data,
        mock_optimized_gemini_service
    ):
        """Test processing speed performance and constitutional compliance."""
        
        # Test multiple batches to get statistical significance
        processing_times = []
        interactions_per_second_measurements = []
        
        for batch_num in range(5):  # 5 batches for statistical analysis
            interactions = performance_interaction_data[batch_num*50:(batch_num+1)*50]  # 50 interactions per batch
            
            upload_response = client.post(
                "/api/upload-json-enhanced",
                files={"file": (f"speed_test_{batch_num}.json", json.dumps(interactions), "application/json")},
                data={"batch_strategy": "medium"}
            )
            
            session_id = upload_response.json()["session_id"]
            session = db_session.get(UploadSession, session_id)
            
            # Measure processing performance
            start_time = time.time()
            
            worker = EnhancedWorker()
            await worker._process_session_batch(session)
            
            end_time = time.time()
            actual_processing_time = end_time - start_time
            
            db_session.refresh(session)
            
            # Collect performance metrics
            processing_times.append(session.processing_time_seconds)
            
            interactions_per_second = session.interactions_processed / session.processing_time_seconds
            interactions_per_second_measurements.append(interactions_per_second)
            
            # Validate individual batch performance
            assert session.status == "completed"
            assert settings.CONSTITUTIONAL_MIN_INTERACTIONS_PER_SECOND <= interactions_per_second <= settings.CONSTITUTIONAL_MAX_INTERACTIONS_PER_SECOND
        
        # Statistical analysis of performance
        avg_processing_time = statistics.mean(processing_times)
        std_processing_time = statistics.stdev(processing_times)
        
        avg_interactions_per_second = statistics.mean(interactions_per_second_measurements)
        std_interactions_per_second = statistics.stdev(interactions_per_second_measurements)
        
        # Performance consistency validation
        assert std_interactions_per_second < 0.5  # Standard deviation should be less than 0.5 interactions/second
        
        # Target performance validation
        assert avg_interactions_per_second >= settings.CONSTITUTIONAL_MIN_INTERACTIONS_PER_SECOND
        assert avg_interactions_per_second <= settings.CONSTITUTIONAL_MAX_INTERACTIONS_PER_SECOND
        
        # Throughput validation (extrapolate to hourly)
        hourly_throughput = avg_interactions_per_second * 3600
        assert hourly_throughput >= settings.THROUGHPUT_TARGET_INTERACTIONS_PER_HOUR * 0.9  # 90% of target
        
        print(f"\nProcessing Speed Performance:")
        print(f"Average: {avg_interactions_per_second:.2f} ± {std_interactions_per_second:.2f} interactions/second")
        print(f"Projected hourly throughput: {hourly_throughput:.0f} interactions/hour")
    
    @pytest.mark.asyncio
    async def test_concurrent_performance(
        self,
        client,
        db_session,
        performance_interaction_data,
        mock_optimized_gemini_service
    ):
        """Test performance under concurrent load."""
        
        concurrent_sessions = min(settings.MAX_CONCURRENT_BATCH_SESSIONS, 3)
        
        # Create concurrent upload sessions
        session_ids = []
        upload_start_time = time.time()
        
        for i in range(concurrent_sessions):
            interactions = performance_interaction_data[i*75:(i+1)*75]  # 75 interactions each
            
            upload_response = client.post(
                "/api/upload-json-enhanced",
                files={"file": (f"concurrent_test_{i}.json", json.dumps(interactions), "application/json")},
                data={"batch_strategy": "medium"}
            )
            
            session_ids.append(upload_response.json()["session_id"])
        
        upload_end_time = time.time()
        
        # Process sessions concurrently
        worker = EnhancedWorker()
        processing_start_time = time.time()
        
        tasks = []
        for session_id in session_ids:
            session = db_session.get(UploadSession, session_id)
            task = asyncio.create_task(worker._process_session_batch(session))
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        
        processing_end_time = time.time()
        
        total_processing_time = processing_end_time - processing_start_time
        
        # Validate concurrent processing results
        total_interactions = 0
        cost_savings = []
        individual_processing_times = []
        
        for session_id in session_ids:
            session = db_session.get(UploadSession, session_id)
            db_session.refresh(session)
            
            assert session.status == "completed"
            assert session.cost_saved_percentage >= settings.CONSTITUTIONAL_MIN_COST_REDUCTION_PERCENTAGE
            
            total_interactions += session.interactions_processed
            cost_savings.append(session.cost_saved_percentage)
            individual_processing_times.append(session.processing_time_seconds)
            
            # Individual session performance validation
            interactions_per_second = session.interactions_processed / session.processing_time_seconds
            assert settings.CONSTITUTIONAL_MIN_INTERACTIONS_PER_SECOND <= interactions_per_second <= settings.CONSTITUTIONAL_MAX_INTERACTIONS_PER_SECOND
        
        # Concurrent processing efficiency
        average_cost_savings = statistics.mean(cost_savings)
        concurrent_throughput = total_interactions / total_processing_time
        
        # Validate concurrent performance
        assert average_cost_savings >= settings.CONSTITUTIONAL_MIN_COST_REDUCTION_PERCENTAGE
        assert concurrent_throughput >= settings.CONSTITUTIONAL_MIN_INTERACTIONS_PER_SECOND * 0.8  # Allow 20% degradation for concurrency
        
        print(f"\nConcurrent Performance Results:")
        print(f"Sessions processed: {concurrent_sessions}")
        print(f"Total interactions: {total_interactions}")
        print(f"Concurrent throughput: {concurrent_throughput:.2f} interactions/second")
        print(f"Average cost savings: {average_cost_savings:.1f}%")
    
    @pytest.mark.asyncio
    async def test_latency_performance(
        self,
        client,
        db_session,
        performance_interaction_data,
        mock_optimized_gemini_service
    ):
        """Test latency performance for individual operations."""
        
        # Test endpoint latency
        latency_measurements = {
            "upload": [],
            "status_check": [],
            "batch_config": [],
            "constitutional_check": []
        }
        
        # Upload latency testing
        for i in range(10):
            interactions = performance_interaction_data[i*10:(i+1)*10]  # 10 interactions each
            
            start_time = time.time()
            
            upload_response = client.post(
                "/api/upload-json-enhanced",
                files={"file": (f"latency_test_{i}.json", json.dumps(interactions), "application/json")},
                data={"batch_strategy": "small"}
            )
            
            upload_latency = (time.time() - start_time) * 1000  # Convert to milliseconds
            latency_measurements["upload"].append(upload_latency)
            
            assert upload_response.status_code == 200
            session_id = upload_response.json()["session_id"]
            
            # Status check latency
            start_time = time.time()
            status_response = client.get(f"/api/upload-status/{session_id}")
            status_latency = (time.time() - start_time) * 1000
            latency_measurements["status_check"].append(status_latency)
            
            assert status_response.status_code == 200
        
        # Batch config endpoint latency
        for i in range(5):
            start_time = time.time()
            batch_config_response = client.get("/api/batch-config")
            batch_config_latency = (time.time() - start_time) * 1000
            latency_measurements["batch_config"].append(batch_config_latency)
            
            assert batch_config_response.status_code == 200
        
        # Constitutional compliance endpoint latency
        for i in range(5):
            start_time = time.time()
            constitutional_response = client.get("/api/constitutional/compliance")
            constitutional_latency = (time.time() - start_time) * 1000
            latency_measurements["constitutional_check"].append(constitutional_latency)
            
            assert constitutional_response.status_code == 200
        
        # Validate latency requirements
        for endpoint, measurements in latency_measurements.items():
            avg_latency = statistics.mean(measurements)
            max_latency = max(measurements)
            
            # Latency should be well below 2 second target
            assert avg_latency < settings.LATENCY_TARGET_MILLISECONDS
            assert max_latency < settings.LATENCY_TARGET_MILLISECONDS * 1.5  # Allow 50% buffer for max
            
            print(f"{endpoint} latency - Average: {avg_latency:.1f}ms, Max: {max_latency:.1f}ms")
    
    @pytest.mark.asyncio
    async def test_scalability_performance(
        self,
        client,
        db_session,
        performance_interaction_data,
        mock_optimized_gemini_service
    ):
        """Test system scalability and performance degradation under increasing load."""
        
        load_test_cases = [
            {"load_level": "Light", "sessions": 2, "interactions_per_session": 50},
            {"load_level": "Medium", "sessions": 3, "interactions_per_session": 100},
            {"load_level": "Heavy", "sessions": 4, "interactions_per_session": 150}
        ]
        
        performance_results = []
        
        for case in load_test_cases:
            print(f"\nTesting {case['load_level']} load scenario...")
            
            # Create sessions for load test
            session_ids = []
            upload_times = []
            
            for i in range(case["sessions"]):
                start_idx = i * case["interactions_per_session"]
                end_idx = start_idx + case["interactions_per_session"]
                interactions = performance_interaction_data[start_idx:end_idx]
                
                start_time = time.time()
                
                upload_response = client.post(
                    "/api/upload-json-enhanced",
                    files={"file": (f"scale_test_{case['load_level']}_{i}.json", json.dumps(interactions), "application/json")},
                    data={"batch_strategy": "auto"}
                )
                
                upload_time = time.time() - start_time
                upload_times.append(upload_time)
                
                assert upload_response.status_code == 200
                session_ids.append(upload_response.json()["session_id"])
            
            # Process all sessions
            worker = EnhancedWorker()
            
            start_processing = time.time()
            
            processing_tasks = []
            for session_id in session_ids:
                session = db_session.get(UploadSession, session_id)
                task = asyncio.create_task(worker._process_session_batch(session))
                processing_tasks.append(task)
            
            await asyncio.gather(*processing_tasks)
            
            total_processing_time = time.time() - start_processing
            
            # Calculate performance metrics
            total_interactions = 0
            cost_savings = []
            processing_speeds = []
            
            for session_id in session_ids:
                session = db_session.get(UploadSession, session_id)
                db_session.refresh(session)
                
                assert session.status == "completed"
                
                total_interactions += session.interactions_processed
                cost_savings.append(session.cost_saved_percentage)
                
                interactions_per_second = session.interactions_processed / session.processing_time_seconds
                processing_speeds.append(interactions_per_second)
                
                # Validate constitutional compliance under load
                assert session.cost_saved_percentage >= settings.CONSTITUTIONAL_MIN_COST_REDUCTION_PERCENTAGE
                assert settings.CONSTITUTIONAL_MIN_INTERACTIONS_PER_SECOND <= interactions_per_second <= settings.CONSTITUTIONAL_MAX_INTERACTIONS_PER_SECOND
            
            # Calculate aggregate metrics
            avg_cost_savings = statistics.mean(cost_savings)
            avg_processing_speed = statistics.mean(processing_speeds)
            system_throughput = total_interactions / total_processing_time
            
            performance_results.append({
                "load_level": case["load_level"],
                "sessions": case["sessions"],
                "total_interactions": total_interactions,
                "avg_cost_savings": avg_cost_savings,
                "avg_processing_speed": avg_processing_speed,
                "system_throughput": system_throughput,
                "processing_time": total_processing_time
            })
            
            # Validate scalability requirements
            assert avg_cost_savings >= settings.CONSTITUTIONAL_MIN_COST_REDUCTION_PERCENTAGE
            assert avg_processing_speed >= settings.CONSTITUTIONAL_MIN_INTERACTIONS_PER_SECOND * 0.9  # Allow 10% degradation under load
            
            print(f"{case['load_level']} load results - Throughput: {system_throughput:.2f} interactions/sec, "
                  f"Cost savings: {avg_cost_savings:.1f}%")
        
        # Validate that performance doesn't degrade significantly with increased load
        for i in range(1, len(performance_results)):
            current = performance_results[i]
            previous = performance_results[i-1]
            
            # Throughput shouldn't decrease by more than 20% with increased load
            throughput_ratio = current["system_throughput"] / previous["system_throughput"]
            assert throughput_ratio > 0.8, f"Significant throughput degradation detected: {throughput_ratio:.2f}"
            
            # Cost savings should remain consistent
            cost_savings_diff = abs(current["avg_cost_savings"] - previous["avg_cost_savings"])
            assert cost_savings_diff < 5.0, f"Cost savings inconsistency detected: {cost_savings_diff:.1f}%"
    
    @pytest.mark.asyncio
    async def test_constitutional_performance_compliance(
        self,
        client,
        db_session,
        performance_interaction_data,
        mock_optimized_gemini_service
    ):
        """Test constitutional compliance under performance stress."""
        
        # Create a high-load scenario to stress test constitutional compliance
        stress_test_sessions = []
        
        for i in range(5):
            interactions = performance_interaction_data[i*100:(i+1)*100]  # 100 interactions each
            
            upload_response = client.post(
                "/api/upload-json-enhanced",
                files={"file": (f"constitutional_stress_{i}.json", json.dumps(interactions), "application/json")},
                data={"batch_strategy": "large"}
            )
            
            stress_test_sessions.append(upload_response.json()["session_id"])
        
        # Process all sessions
        worker = EnhancedWorker()
        
        for session_id in stress_test_sessions:
            session = db_session.get(UploadSession, session_id)
            await worker._process_session_batch(session)
        
        # Validate constitutional compliance for each session
        constitutional_validator = ConstitutionalValidator()
        
        compliance_results = []
        
        for session_id in stress_test_sessions:
            compliance_result = await constitutional_validator.validate_session_compliance(
                session_id, db_session
            )
            
            compliance_results.append(compliance_result)
            
            # Each session must be constitutionally compliant
            assert compliance_result.is_compliant == True
            assert len(compliance_result.violations) == 0
            
            # Verify specific constitutional metrics
            metrics = compliance_result.metrics
            
            assert metrics["cost_saved_percentage"] >= settings.CONSTITUTIONAL_MIN_COST_REDUCTION_PERCENTAGE
            
            if "interactions_per_second" in metrics:
                assert settings.CONSTITUTIONAL_MIN_INTERACTIONS_PER_SECOND <= metrics["interactions_per_second"] <= settings.CONSTITUTIONAL_MAX_INTERACTIONS_PER_SECOND
        
        # System-wide constitutional compliance validation
        system_compliance = await constitutional_validator.validate_system_compliance(db_session)
        
        assert system_compliance.is_compliant == True
        assert system_compliance.metrics["success_rate_percentage"] >= settings.CONSTITUTIONAL_MIN_SUCCESS_RATE_PERCENTAGE
        assert system_compliance.metrics["average_cost_savings"] >= settings.CONSTITUTIONAL_MIN_COST_REDUCTION_PERCENTAGE
        
        print(f"\nConstitutional Performance Compliance:")
        print(f"All sessions compliant: {all(r.is_compliant for r in compliance_results)}")
        print(f"System compliance: {system_compliance.is_compliant}")
        print(f"System success rate: {system_compliance.metrics.get('success_rate_percentage', 0):.1f}%")