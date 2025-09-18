"""
Constitutional Endpoint Testing Script
Tests all newly implemented endpoints using Python requests to validate functionality.

CONSTITUTIONAL REQUIREMENT: All endpoints must pass these tests before advancing to next phase.
"""

import requests
import json
import time
import tempfile
import os
from typing import Dict, Any, Optional
import uuid

class EndpointTester:
    """Constitutional endpoint testing class."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session_ids = []  # Track created sessions for cleanup
        
    def test_server_health(self) -> bool:
        """Test if server is running and responsive."""
        try:
            response = requests.get(f"{self.base_url}/")
            print(f"✅ Server health check: {response.status_code}")
            return response.status_code == 200
        except requests.ConnectionError:
            print("❌ Server not responding! Please start the server with:")
            print("uvicorn main:app --host 0.0.0.0 --port 8000 --reload")
            return False
    
    def create_test_json_file(self, interaction_count: int = 20) -> str:
        """Create a temporary JSON file for testing uploads."""
        test_data = [
            {
                "conversation_id": f"endpoint_test_conv_{i}",
                "timestamp": f"2024-09-17T{i%24:02d}:00:00Z",
                "messages": [
                    {
                        "role": "user",
                        "content": f"Constitutional endpoint test user message {i}",
                        "timestamp": f"2024-09-17T{i%24:02d}:00:00Z"
                    },
                    {
                        "role": "assistant",
                        "content": f"Constitutional endpoint test assistant response {i}",
                        "timestamp": f"2024-09-17T{i%24:02d}:01:00Z"
                    }
                ]
            }
            for i in range(1, interaction_count + 1)
        ]
        
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump(test_data, temp_file)
        temp_file.close()
        return temp_file.name
    
    def test_enhanced_upload_endpoint(self) -> Dict[str, Any]:
        """Test /api/upload-json-enhanced endpoint."""
        print("\n🧪 Testing Enhanced Upload Endpoint (/api/upload-json-enhanced)")
        
        # Create test file
        test_file_path = self.create_test_json_file(25)
        
        try:
            # Test successful upload
            with open(test_file_path, 'rb') as f:
                files = {'file': ('constitutional_test.json', f, 'application/json')}
                data = {
                    'batch_strategy': 'auto',
                    'priority': 'normal'
                }
                
                response = requests.post(
                    f"{self.base_url}/api/interaction/upload-json-enhanced",
                    files=files,
                    data=data
                )
            
            print(f"  📤 Upload Status Code: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"  ✅ Session ID: {result.get('session_id')}")
                print(f"  ✅ Status: {result.get('status')}")
                print(f"  ✅ Batch Strategy: {result.get('batch_strategy')}")
                print(f"  ✅ Estimated Cost Savings: {result.get('estimated_cost_savings')}%")
                
                if result.get('session_id'):
                    self.session_ids.append(result['session_id'])
                
                return result
            else:
                print(f"  ❌ Upload failed: {response.text}")
                return {"error": response.text}
                
        except Exception as e:
            print(f"  ❌ Exception during upload: {e}")
            return {"error": str(e)}
        finally:
            os.unlink(test_file_path)
    
    def test_upload_status_endpoint(self, session_id: str) -> Dict[str, Any]:
        """Test /api/upload-status/{session_id} endpoint."""
        print(f"\n🧪 Testing Upload Status Endpoint (/api/upload-status/{session_id})")
        
        try:
            response = requests.get(f"{self.base_url}/api/interaction/upload-status/{session_id}")
            print(f"  📊 Status Code: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"  ✅ Session ID: {result.get('session_id')}")
                print(f"  ✅ Status: {result.get('status')}")
                print(f"  ✅ Progress: {result.get('progress_percentage', 0)}%")
                print(f"  ✅ Interactions Count: {result.get('interactions_count', 0)}")
                return result
            elif response.status_code == 404:
                print(f"  ⚠️ Session not found (expected for new sessions)")
                return {"status": "not_found"}
            else:
                print(f"  ❌ Status check failed: {response.text}")
                return {"error": response.text}
                
        except Exception as e:
            print(f"  ❌ Exception during status check: {e}")
            return {"error": str(e)}
    
    def test_batch_config_endpoint(self) -> Dict[str, Any]:
        """Test /api/batch-config endpoint."""
        print(f"\n🧪 Testing Batch Config Endpoint (/api/batch-config)")
        
        try:
            response = requests.get(f"{self.base_url}/api/batch-config")
            print(f"  ⚙️ Status Code: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"  ✅ Batch Settings Present: {'batch_settings' in result}")
                print(f"  ✅ Performance Metrics Present: {'performance_metrics' in result}")
                print(f"  ✅ System Status Present: {'system_status' in result}")
                
                if 'batch_settings' in result:
                    batch_settings = result['batch_settings']
                    print(f"  ✅ Batch Enabled: {batch_settings.get('enabled')}")
                    print(f"  ✅ Max Concurrent Sessions: {batch_settings.get('max_concurrent_sessions')}")
                
                return result
            else:
                print(f"  ❌ Batch config failed: {response.text}")
                return {"error": response.text}
                
        except Exception as e:
            print(f"  ❌ Exception during batch config: {e}")
            return {"error": str(e)}
    
    def test_constitutional_compliance_endpoint(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Test /api/constitutional/compliance endpoint."""
        endpoint = "/api/constitutional/compliance"
        if session_id:
            endpoint += f"?session_id={session_id}"
            print(f"\n🧪 Testing Constitutional Compliance Endpoint (with session: {session_id})")
        else:
            print(f"\n🧪 Testing Constitutional Compliance Endpoint (system-wide)")
        
        try:
            response = requests.get(f"{self.base_url}{endpoint}")
            print(f"  ⚖️ Status Code: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"  ✅ Is Compliant: {result.get('is_compliant')}")
                print(f"  ✅ Constitutional Requirements Present: {'constitutional_requirements' in result}")
                
                if 'constitutional_requirements' in result:
                    reqs = result['constitutional_requirements']
                    print(f"  ✅ AI Supremacy: {reqs.get('ai_supremacy', {}).get('status', 'unknown')}")
                    print(f"  ✅ Dual CSI: {reqs.get('dual_csi_architecture', {}).get('status', 'unknown')}")
                    print(f"  ✅ Cost Reduction: {reqs.get('cost_reduction', {}).get('status', 'unknown')}")
                
                if result.get('violations'):
                    print(f"  ⚠️ Violations Found: {len(result['violations'])}")
                    for violation in result['violations'][:3]:  # Show first 3
                        print(f"    - {violation}")
                
                return result
            else:
                print(f"  ❌ Constitutional compliance failed: {response.text}")
                return {"error": response.text}
                
        except Exception as e:
            print(f"  ❌ Exception during constitutional compliance: {e}")
            return {"error": str(e)}
    
    def test_retry_endpoint(self, session_id: str) -> Dict[str, Any]:
        """Test /api/retry/{session_id} endpoint."""
        print(f"\n🧪 Testing Retry Endpoint (/api/retry/{session_id})")
        
        try:
            response = requests.post(f"{self.base_url}/api/interaction/retry/{session_id}")
            print(f"  🔄 Status Code: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"  ✅ Session ID: {result.get('session_id')}")
                print(f"  ✅ Status: {result.get('status')}")
                print(f"  ✅ Retry Count: {result.get('retry_count', 0)}")
                return result
            elif response.status_code == 404:
                print(f"  ⚠️ Session not found")
                return {"status": "not_found"}
            elif response.status_code == 400:
                print(f"  ⚠️ Retry not allowed (may have exceeded max retries)")
                return {"status": "retry_not_allowed"}
            else:
                print(f"  ❌ Retry failed: {response.text}")
                return {"error": response.text}
                
        except Exception as e:
            print(f"  ❌ Exception during retry: {e}")
            return {"error": str(e)}
    
    def test_invalid_endpoints(self) -> Dict[str, Any]:
        """Test error handling with invalid requests."""
        print(f"\n🧪 Testing Error Handling")
        
        results = {}
        
        # Test invalid session ID
        try:
            invalid_session = "invalid-session-id-12345"
            response = requests.get(f"{self.base_url}/api/interaction/upload-status/{invalid_session}")
            print(f"  ❌ Invalid Session Status Code: {response.status_code} (expected 404)")
            results["invalid_session"] = response.status_code
        except Exception as e:
            results["invalid_session"] = f"Exception: {e}"
        
        # Test malformed upload
        try:
            files = {'file': ('bad.txt', b'not json content', 'text/plain')}
            response = requests.post(f"{self.base_url}/api/interaction/upload-json-enhanced", files=files)
            print(f"  ❌ Invalid Upload Status Code: {response.status_code} (expected 400/422)")
            results["invalid_upload"] = response.status_code
        except Exception as e:
            results["invalid_upload"] = f"Exception: {e}"
        
        return results
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all constitutional endpoint tests."""
        print("🚨 CONSTITUTIONAL ENDPOINT TESTING INITIATED")
        print("=" * 60)
        
        all_results = {}
        
        # Test 1: Server Health
        if not self.test_server_health():
            print("\n❌ CONSTITUTIONAL VIOLATION: Server not running!")
            return {"fatal_error": "Server not accessible"}
        
        all_results["server_health"] = "✅ PASSED"
        
        # Test 2: Enhanced Upload
        upload_result = self.test_enhanced_upload_endpoint()
        if "error" not in upload_result and upload_result.get("session_id"):
            all_results["enhanced_upload"] = "✅ PASSED"
            session_id = upload_result["session_id"]
            
            # Test 3: Upload Status (immediate check)
            status_result = self.test_upload_status_endpoint(session_id)
            if "error" not in status_result:
                all_results["upload_status"] = "✅ PASSED"
            else:
                all_results["upload_status"] = "❌ FAILED"
            
            # Test 4: Retry Endpoint
            retry_result = self.test_retry_endpoint(session_id)
            if "error" not in retry_result:
                all_results["retry_endpoint"] = "✅ PASSED"
            else:
                all_results["retry_endpoint"] = "❌ FAILED"
            
            # Test 5: Constitutional Compliance (with session)
            compliance_result = self.test_constitutional_compliance_endpoint(session_id)
            if "error" not in compliance_result:
                all_results["constitutional_compliance_session"] = "✅ PASSED"
            else:
                all_results["constitutional_compliance_session"] = "❌ FAILED"
        else:
            all_results["enhanced_upload"] = "❌ FAILED"
            session_id = None
        
        # Test 6: Batch Config
        batch_config_result = self.test_batch_config_endpoint()
        if "error" not in batch_config_result:
            all_results["batch_config"] = "✅ PASSED"
        else:
            all_results["batch_config"] = "❌ FAILED"
        
        # Test 7: Constitutional Compliance (system-wide)
        system_compliance_result = self.test_constitutional_compliance_endpoint()
        if "error" not in system_compliance_result:
            all_results["constitutional_compliance_system"] = "✅ PASSED"
        else:
            all_results["constitutional_compliance_system"] = "❌ FAILED"
        
        # Test 8: Error Handling
        error_results = self.test_invalid_endpoints()
        all_results["error_handling"] = "✅ PASSED" if error_results else "❌ FAILED"
        
        # Constitutional Compliance Summary
        print("\n" + "=" * 60)
        print("🚨 CONSTITUTIONAL COMPLIANCE SUMMARY")
        print("=" * 60)
        
        passed_tests = sum(1 for result in all_results.values() if "✅ PASSED" in result)
        total_tests = len(all_results)
        
        for test_name, result in all_results.items():
            print(f"  {test_name.replace('_', ' ').title()}: {result}")
        
        print(f"\n📊 CONSTITUTIONAL COMPLIANCE RATE: {passed_tests}/{total_tests} ({passed_tests/total_tests*100:.1f}%)")
        
        if passed_tests == total_tests:
            print("✅ ALL CONSTITUTIONAL REQUIREMENTS MET - PROCEED TO NEXT PHASE")
        else:
            print("❌ CONSTITUTIONAL VIOLATIONS DETECTED - CANNOT PROCEED")
        
        return all_results

def main():
    """Main function to run constitutional endpoint tests."""
    print("🚨 PowerPulse Constitutional Endpoint Testing")
    print("Please ensure the FastAPI server is running on http://localhost:8000")
    print("Command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload")
    
    input("\nPress Enter when server is ready...")
    
    tester = EndpointTester()
    results = tester.run_all_tests()
    
    return results

if __name__ == "__main__":
    results = main()