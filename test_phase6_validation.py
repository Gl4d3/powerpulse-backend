"""
Phase 6: Comprehensive Testing and Validation Suite for Interaction-Based Analysis
Tests edge cases, performance, data integrity, and API reliability.
"""
import pytest
import requests
import json
import time
from datetime import datetime, date, timedelta
from typing import Dict, List, Any
import asyncio
import sys
import os

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal, get_db
from models import Conversation, InteractionAnalysis, DailyAnalysis, Message
from services.enhanced_analytics_service import EnhancedAnalyticsService
from services.enhanced_file_service import EnhancedFileService
from services.interaction_service import InteractionService

# Test Configuration
BASE_URL = "http://localhost:8000"
TEST_DATA_SIZE_SMALL = 10
TEST_DATA_SIZE_LARGE = 100
PERFORMANCE_THRESHOLD_MS = 3000  # Adjusted to reasonable threshold for interaction analysis

class TestPhase6ValidationSuite:
    """Comprehensive validation suite for interaction-based analysis system."""
    
    def __init__(self):
        self.enhanced_analytics = EnhancedAnalyticsService()
        self.enhanced_file_service = EnhancedFileService()
        self.interaction_service = InteractionService()
        self.test_results = []
    
    # =========================================================================
    # 1. DATA INTEGRITY TESTS
    # =========================================================================
    
    def test_csi_score_bounds(self):
        """Test that CSI scores stay within valid bounds (0-10)."""
        print("🔍 Testing CSI Score Bounds...")
        
        with SessionLocal() as db:
            interactions = db.query(InteractionAnalysis).all()
            
            invalid_scores = []
            for interaction in interactions:
                if interaction.csi_score is not None:
                    if interaction.csi_score < 0 or interaction.csi_score > 10:
                        invalid_scores.append({
                            'id': interaction.id,
                            'csi_score': interaction.csi_score,
                            'effectiveness': interaction.effectiveness_score,
                            'efficiency': interaction.efficiency_score,
                            'effort': interaction.effort_score,
                            'empathy': interaction.empathy_score
                        })
            
            result = {
                'test': 'CSI Score Bounds',
                'status': 'PASS' if not invalid_scores else 'FAIL',
                'total_interactions': len(interactions),
                'invalid_scores': len(invalid_scores),
                'details': invalid_scores[:5] if invalid_scores else None
            }
            
        self.test_results.append(result)
        print(f"   {'✅' if result['status'] == 'PASS' else '❌'} {result}")
        return result
    
    def test_pillar_score_bounds(self):
        """Test that all pillar scores stay within valid bounds (0-10)."""
        print("🔍 Testing Pillar Score Bounds...")
        
        with SessionLocal() as db:
            interactions = db.query(InteractionAnalysis).all()
            
            invalid_pillars = []
            for interaction in interactions:
                pillars = {
                    'effectiveness': interaction.effectiveness_score,
                    'efficiency': interaction.efficiency_score,
                    'effort': interaction.effort_score,
                    'empathy': interaction.empathy_score
                }
                
                for pillar, score in pillars.items():
                    if score is not None and (score < 0 or score > 10):
                        invalid_pillars.append({
                            'interaction_id': interaction.id,
                            'pillar': pillar,
                            'score': score
                        })
            
            result = {
                'test': 'Pillar Score Bounds',
                'status': 'PASS' if not invalid_pillars else 'FAIL',
                'total_interactions': len(interactions),
                'invalid_pillars': len(invalid_pillars),
                'details': invalid_pillars[:5] if invalid_pillars else None
            }
            
        self.test_results.append(result)
        print(f"   {'✅' if result['status'] == 'PASS' else '❌'} {result}")
        return result
    
    def test_interaction_boundaries_validity(self):
        """Test that interaction boundaries are logical (start < end)."""
        print("🔍 Testing Interaction Boundary Validity...")
        
        with SessionLocal() as db:
            interactions = db.query(InteractionAnalysis).all()
            
            invalid_boundaries = []
            for interaction in interactions:
                if interaction.interaction_start >= interaction.interaction_end:
                    invalid_boundaries.append({
                        'id': interaction.id,
                        'start': interaction.interaction_start,
                        'end': interaction.interaction_end,
                        'conversation_id': interaction.conversation_id
                    })
            
            result = {
                'test': 'Interaction Boundaries',
                'status': 'PASS' if not invalid_boundaries else 'FAIL',
                'total_interactions': len(interactions),
                'invalid_boundaries': len(invalid_boundaries),
                'details': invalid_boundaries
            }
            
        self.test_results.append(result)
        print(f"   {'✅' if result['status'] == 'PASS' else '❌'} {result}")
        return result
    
    def test_message_range_validity(self):
        """Test that message ranges are valid (start_message_id <= end_message_id)."""
        print("🔍 Testing Message Range Validity...")
        
        with SessionLocal() as db:
            interactions = db.query(InteractionAnalysis).all()
            
            invalid_ranges = []
            for interaction in interactions:
                if interaction.start_message_id > interaction.end_message_id:
                    invalid_ranges.append({
                        'id': interaction.id,
                        'start_message_id': interaction.start_message_id,
                        'end_message_id': interaction.end_message_id,
                        'conversation_id': interaction.conversation_id
                    })
            
            result = {
                'test': 'Message Range Validity',
                'status': 'PASS' if not invalid_ranges else 'FAIL',
                'total_interactions': len(interactions),
                'invalid_ranges': len(invalid_ranges),
                'details': invalid_ranges
            }
            
        self.test_results.append(result)
        print(f"   {'✅' if result['status'] == 'PASS' else '❌'} {result}")
        return result
    
    # =========================================================================
    # 2. API ENDPOINT TESTS
    # =========================================================================
    
    def test_api_endpoints_availability(self):
        """Test that all new interaction endpoints are accessible."""
        print("🔍 Testing API Endpoint Availability...")
        
        endpoints = [
            ('GET', '/api/interactions/metrics/'),
            ('POST', '/api/interactions/metrics/recalculate'),
            ('GET', '/api/interactions/conversations'),
            ('GET', '/api/interactions/charts/sentiment-trend?start_date=2025-08-18&end_date=2025-08-21'),
            ('GET', '/api/interactions/charts/interaction-distribution?start_date=2025-08-18&end_date=2025-08-21'),
            ('GET', '/api/interactions/export/download?export_type=interactions')
        ]
        
        results = []
        for method, endpoint in endpoints:
            try:
                if method == 'GET':
                    response = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
                elif method == 'POST':
                    response = requests.post(f"{BASE_URL}{endpoint}", timeout=10)
                
                results.append({
                    'endpoint': endpoint,
                    'method': method,
                    'status_code': response.status_code,
                    'success': response.status_code < 400,
                    'response_time_ms': response.elapsed.total_seconds() * 1000
                })
            except Exception as e:
                results.append({
                    'endpoint': endpoint,
                    'method': method,
                    'status_code': None,
                    'success': False,
                    'error': str(e)
                })
        
        success_count = sum(1 for r in results if r['success'])
        result = {
            'test': 'API Endpoint Availability',
            'status': 'PASS' if success_count == len(endpoints) else 'FAIL',
            'successful_endpoints': success_count,
            'total_endpoints': len(endpoints),
            'details': [r for r in results if not r['success']]
        }
        
        self.test_results.append(result)
        print(f"   {'✅' if result['status'] == 'PASS' else '❌'} {result}")
        return result
    
    def test_api_response_performance(self):
        """Test API response times under normal load."""
        print("🔍 Testing API Response Performance...")
        
        performance_tests = [
            ('GET', '/api/interactions/metrics/', 'Interaction Metrics'),
            ('GET', '/api/interactions/conversations', 'Conversation List'),
            ('GET', '/api/interactions/charts/interaction-distribution?start_date=2025-08-18&end_date=2025-08-21', 'Chart Data')
        ]
        
        results = []
        for method, endpoint, name in performance_tests:
            response_times = []
            
            # Test 5 times to get average
            for _ in range(5):
                try:
                    start_time = time.time()
                    response = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
                    end_time = time.time()
                    
                    if response.status_code < 400:
                        response_times.append((end_time - start_time) * 1000)
                except Exception as e:
                    print(f"      Error testing {name}: {e}")
            
            if response_times:
                avg_time = sum(response_times) / len(response_times)
                results.append({
                    'endpoint': name,
                    'avg_response_time_ms': avg_time,
                    'max_response_time_ms': max(response_times),
                    'min_response_time_ms': min(response_times),
                    'within_threshold': avg_time < PERFORMANCE_THRESHOLD_MS
                })
        
        all_within_threshold = all(r['within_threshold'] for r in results)
        result = {
            'test': 'API Response Performance',
            'status': 'PASS' if all_within_threshold else 'FAIL',
            'threshold_ms': PERFORMANCE_THRESHOLD_MS,
            'results': results
        }
        
        self.test_results.append(result)
        print(f"   {'✅' if result['status'] == 'PASS' else '❌'} {result}")
        return result
    
    # =========================================================================
    # 3. EDGE CASE TESTS
    # =========================================================================
    
    def test_empty_data_handling(self):
        """Test system behavior with empty datasets."""
        print("🔍 Testing Empty Data Handling...")
        
        tests = []
        
        # Test metrics with no interactions
        try:
            response = requests.get(f"{BASE_URL}/api/interactions/metrics/")
            data = response.json()
            
            tests.append({
                'scenario': 'Metrics with existing data',
                'success': response.status_code == 200,
                'has_data': data.get('interaction_count', 0) > 0
            })
        except Exception as e:
            tests.append({
                'scenario': 'Metrics endpoint error',
                'success': False,
                'error': str(e)
            })
        
        # Test charts with invalid date range
        try:
            response = requests.get(f"{BASE_URL}/api/interactions/charts/sentiment-trend?start_date=2020-01-01&end_date=2020-01-02")
            data = response.json()
            
            tests.append({
                'scenario': 'Charts with no data period',
                'success': response.status_code == 200,
                'empty_response': len(data.get('sentiment_trend', [])) == 0
            })
        except Exception as e:
            tests.append({
                'scenario': 'Charts endpoint error',
                'success': False,
                'error': str(e)
            })
        
        all_successful = all(t['success'] for t in tests)
        result = {
            'test': 'Empty Data Handling',
            'status': 'PASS' if all_successful else 'FAIL',
            'tests': tests
        }
        
        self.test_results.append(result)
        print(f"   {'✅' if result['status'] == 'PASS' else '❌'} {result}")
        return result
    
    def test_invalid_date_ranges(self):
        """Test handling of invalid date parameters."""
        print("🔍 Testing Invalid Date Range Handling...")
        
        invalid_requests = [
            ('start_date=invalid&end_date=2025-08-21', 'Invalid start date format'),
            ('start_date=2025-08-21&end_date=2025-08-18', 'End date before start date'),
            ('start_date=&end_date=', 'Empty date parameters')
        ]
        
        results = []
        for params, scenario in invalid_requests:
            try:
                response = requests.get(f"{BASE_URL}/api/interactions/charts/sentiment-trend?{params}")
                results.append({
                    'scenario': scenario,
                    'status_code': response.status_code,
                    'handled_gracefully': response.status_code in [400, 422]  # 400 for logic errors, 422 for validation errors
                })
            except Exception as e:
                results.append({
                    'scenario': scenario,
                    'error': str(e),
                    'handled_gracefully': False
                })
        
        properly_handled = all(r.get('handled_gracefully', False) for r in results)
        result = {
            'test': 'Invalid Date Range Handling',
            'status': 'PASS' if properly_handled else 'FAIL',
            'results': results
        }
        
        self.test_results.append(result)
        print(f"   {'✅' if result['status'] == 'PASS' else '❌'} {result}")
        return result
    
    # =========================================================================
    # 4. BUSINESS LOGIC TESTS
    # =========================================================================
    
    def test_csi_calculation_consistency(self):
        """Test that CSI calculations are consistent between daily and interaction modes."""
        print("🔍 Testing CSI Calculation Consistency...")
        
        with SessionLocal() as db:
            # Get a sample conversation that has both daily and interaction analyses
            conversation = db.query(Conversation).join(DailyAnalysis).join(InteractionAnalysis).first()
            
            if not conversation:
                result = {
                    'test': 'CSI Calculation Consistency',
                    'status': 'SKIP',
                    'reason': 'No conversations with both daily and interaction analyses found'
                }
                self.test_results.append(result)
                print(f"   ⏭️  {result}")
                return result
            
            # Get CSI scores from both modes
            daily_analyses = db.query(DailyAnalysis).filter(DailyAnalysis.conversation_id == conversation.id).all()
            interaction_analyses = db.query(InteractionAnalysis).filter(InteractionAnalysis.conversation_id == conversation.id).all()
            
            daily_csi_avg = sum(d.csi_score for d in daily_analyses if d.csi_score) / len([d for d in daily_analyses if d.csi_score]) if daily_analyses else 0
            interaction_csi_avg = sum(i.csi_score for i in interaction_analyses if i.csi_score) / len([i for i in interaction_analyses if i.csi_score]) if interaction_analyses else 0
            
            # Allow for reasonable variance (within 2 points)
            csi_difference = abs(daily_csi_avg - interaction_csi_avg)
            
            result = {
                'test': 'CSI Calculation Consistency',
                'status': 'PASS' if csi_difference < 2.0 else 'WARN',
                'daily_csi_avg': daily_csi_avg,
                'interaction_csi_avg': interaction_csi_avg,
                'difference': csi_difference,
                'daily_analyses_count': len(daily_analyses),
                'interaction_analyses_count': len(interaction_analyses)
            }
        
        self.test_results.append(result)
        print(f"   {'✅' if result['status'] == 'PASS' else '⚠️' if result['status'] == 'WARN' else '❌'} {result}")
        return result
    
    def test_interaction_boundary_logic(self):
        """Test interaction boundary detection logic."""
        print("🔍 Testing Interaction Boundary Logic...")
        
        with SessionLocal() as db:
            interactions = db.query(InteractionAnalysis).limit(10).all()
            
            boundary_issues = []
            for interaction in interactions:
                # Check if boundary method is valid
                valid_methods = ['time_gap', 'resolution_keywords', 'ai_detected', 'topic_shift', 'agent_change', 'conversation_end', 'time_gap_after_closure']
                if interaction.boundary_method not in valid_methods:
                    boundary_issues.append({
                        'interaction_id': interaction.id,
                        'issue': 'Invalid boundary method',
                        'method': interaction.boundary_method
                    })
                
                # Check confidence score range
                if interaction.boundary_confidence is not None:
                    if interaction.boundary_confidence < 0 or interaction.boundary_confidence > 1:
                        boundary_issues.append({
                            'interaction_id': interaction.id,
                            'issue': 'Invalid confidence score',
                            'confidence': interaction.boundary_confidence
                        })
            
            result = {
                'test': 'Interaction Boundary Logic',
                'status': 'PASS' if not boundary_issues else 'FAIL',
                'total_interactions_tested': len(interactions),
                'boundary_issues': len(boundary_issues),
                'details': boundary_issues[:3] if boundary_issues else None
            }
        
        self.test_results.append(result)
        print(f"   {'✅' if result['status'] == 'PASS' else '❌'} {result}")
        return result
    
    # =========================================================================
    # 5. BACKWARD COMPATIBILITY TESTS
    # =========================================================================
    
    def test_original_endpoints_still_work(self):
        """Verify that original daily analysis endpoints are unaffected."""
        print("🔍 Testing Backward Compatibility...")
        
        original_endpoints = [
            ('GET', '/api/metrics/'),
            ('GET', '/api/conversations'),
            ('POST', '/api/metrics/recalculate')
        ]
        
        results = []
        for method, endpoint in original_endpoints:
            try:
                if method == 'GET':
                    response = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
                elif method == 'POST':
                    response = requests.post(f"{BASE_URL}{endpoint}", timeout=10)
                
                results.append({
                    'endpoint': endpoint,
                    'method': method,
                    'status_code': response.status_code,
                    'success': response.status_code < 400
                })
            except Exception as e:
                results.append({
                    'endpoint': endpoint,
                    'method': method,
                    'success': False,
                    'error': str(e)
                })
        
        all_working = all(r['success'] for r in results)
        result = {
            'test': 'Backward Compatibility',
            'status': 'PASS' if all_working else 'FAIL',
            'original_endpoints_working': sum(1 for r in results if r['success']),
            'total_endpoints': len(original_endpoints),
            'failed_endpoints': [r for r in results if not r['success']]
        }
        
        self.test_results.append(result)
        print(f"   {'✅' if result['status'] == 'PASS' else '❌'} {result}")
        return result
    
    # =========================================================================
    # 6. MAIN TEST RUNNER
    # =========================================================================
    
    def run_all_tests(self):
        """Run the complete validation suite."""
        print("🚀 Starting Phase 6: Comprehensive Testing and Validation")
        print("=" * 60)
        
        start_time = time.time()
        
        # Data Integrity Tests
        print("\n📊 DATA INTEGRITY TESTS")
        print("-" * 30)
        self.test_csi_score_bounds()
        self.test_pillar_score_bounds()
        self.test_interaction_boundaries_validity()
        self.test_message_range_validity()
        
        # API Endpoint Tests
        print("\n🌐 API ENDPOINT TESTS")
        print("-" * 30)
        self.test_api_endpoints_availability()
        self.test_api_response_performance()
        
        # Edge Case Tests
        print("\n⚠️  EDGE CASE TESTS")
        print("-" * 30)
        self.test_empty_data_handling()
        self.test_invalid_date_ranges()
        
        # Business Logic Tests
        print("\n🧠 BUSINESS LOGIC TESTS")
        print("-" * 30)
        self.test_csi_calculation_consistency()
        self.test_interaction_boundary_logic()
        
        # Backward Compatibility Tests
        print("\n🔄 BACKWARD COMPATIBILITY TESTS")
        print("-" * 30)
        self.test_original_endpoints_still_work()
        
        end_time = time.time()
        
        # Generate Summary
        print("\n" + "=" * 60)
        print("🎯 TEST SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r['status'] == 'PASS'])
        failed_tests = len([r for r in self.test_results if r['status'] == 'FAIL'])
        warning_tests = len([r for r in self.test_results if r['status'] == 'WARN'])
        skipped_tests = len([r for r in self.test_results if r['status'] == 'SKIP'])
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"⚠️  Warnings: {warning_tests}")
        print(f"⏭️  Skipped: {skipped_tests}")
        print(f"⏱️  Total Time: {end_time - start_time:.2f}s")
        print(f"🏆 Success Rate: {(passed_tests / total_tests) * 100:.1f}%")
        
        # Failed Tests Detail
        if failed_tests > 0:
            print(f"\n❌ FAILED TESTS DETAILS:")
            for result in self.test_results:
                if result['status'] == 'FAIL':
                    print(f"   • {result['test']}: {result.get('details', 'See above')}")
        
        return {
            'summary': {
                'total': total_tests,
                'passed': passed_tests,
                'failed': failed_tests,
                'warnings': warning_tests,
                'skipped': skipped_tests,
                'success_rate': (passed_tests / total_tests) * 100,
                'duration_seconds': end_time - start_time
            },
            'detailed_results': self.test_results
        }

def main():
    """Main test runner."""
    print("Phase 6: Testing and Validation Suite")
    print("PowerPulse Interaction-Based Analysis System")
    print()
    
    # Initialize and run tests
    test_suite = TestPhase6ValidationSuite()
    results = test_suite.run_all_tests()
    
    # Save results to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"test_results_phase6_{timestamp}.json"
    
    try:
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\n💾 Detailed results saved to: {results_file}")
    except Exception as e:
        print(f"\n⚠️  Could not save results file: {e}")
    
    return results

if __name__ == "__main__":
    main()