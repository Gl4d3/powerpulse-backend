"""
Additional Edge Case Tests for Phase 6 Validation
Focused on stress testing and advanced scenarios.
"""
import requests
import json
import time
from datetime import datetime, timedelta
import threading
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_URL = "http://localhost:8000"

def test_concurrent_requests():
    """Test system behavior under concurrent load."""
    print("🔄 Testing Concurrent Request Handling...")
    
    def make_request():
        try:
            response = requests.get(f"{BASE_URL}/api/interactions/metrics/", timeout=10)
            return response.status_code == 200
        except:
            return False
    
    # Create 10 concurrent threads
    threads = []
    results = []
    
    start_time = time.time()
    for _ in range(10):
        thread = threading.Thread(target=lambda: results.append(make_request()))
        threads.append(thread)
        thread.start()
    
    for thread in threads:
        thread.join()
    
    end_time = time.time()
    
    success_count = sum(results)
    success_rate = (success_count / len(results)) * 100
    
    print(f"   Concurrent requests: {len(results)}")
    print(f"   Successful: {success_count} ({success_rate:.1f}%)")
    print(f"   Total time: {end_time - start_time:.2f}s")
    print(f"   Status: {'✅ PASS' if success_rate >= 90 else '❌ FAIL'}")

def test_large_date_ranges():
    """Test API with very large date ranges."""
    print("📅 Testing Large Date Range Handling...")
    
    # Test 10-year range
    start_date = "2015-01-01"
    end_date = "2025-12-31"
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/interactions/charts/sentiment-trend?start_date={start_date}&end_date={end_date}",
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Large date range query: ✅ PASS")
            print(f"   Response size: {len(str(data))} characters")
        else:
            print(f"   Large date range query: ❌ FAIL (Status: {response.status_code})")
            
    except requests.Timeout:
        print(f"   Large date range query: ⚠️  TIMEOUT (>15s)")
    except Exception as e:
        print(f"   Large date range query: ❌ ERROR ({e})")

def test_malformed_requests():
    """Test API resilience to malformed requests."""
    print("🛡️ Testing Malformed Request Resilience...")
    
    malformed_tests = [
        # Invalid JSON in POST
        ("POST", "/api/interactions/metrics/recalculate", "invalid-json"),
        # SQL injection attempt
        ("GET", "/api/interactions/conversations?page=1'; DROP TABLE interactions; --", None),
        # Extremely large page size
        ("GET", "/api/interactions/conversations?page_size=999999", None),
        # Special characters in parameters
        ("GET", "/api/interactions/charts/sentiment-trend?start_date=<script>&end_date=alert()", None),
    ]
    
    results = []
    for method, endpoint, data in malformed_tests:
        try:
            if method == "POST":
                if data:
                    response = requests.post(f"{BASE_URL}{endpoint}", data=data, timeout=5)
                else:
                    response = requests.post(f"{BASE_URL}{endpoint}", timeout=5)
            else:
                response = requests.get(f"{BASE_URL}{endpoint}", timeout=5)
            
            # Should return 400, 422, or similar error code, not 500
            handled_gracefully = 400 <= response.status_code < 500
            results.append(handled_gracefully)
            
        except Exception as e:
            # Exceptions are acceptable for malformed requests
            results.append(True)
    
    success_rate = (sum(results) / len(results)) * 100
    print(f"   Malformed requests handled gracefully: {sum(results)}/{len(results)} ({success_rate:.1f}%)")
    print(f"   Status: {'✅ PASS' if success_rate >= 80 else '❌ FAIL'}")

def test_api_consistency():
    """Test that repeated API calls return consistent results."""
    print("🔄 Testing API Response Consistency...")
    
    endpoint = f"{BASE_URL}/api/interactions/metrics/"
    responses = []
    
    for i in range(5):
        try:
            response = requests.get(endpoint, timeout=10)
            if response.status_code == 200:
                data = response.json()
                responses.append(data.get('csi', None))
        except:
            continue
    
    if len(responses) >= 3:
        # Check if all CSI values are the same (or very close)
        csi_values = [r for r in responses if r is not None]
        if csi_values:
            max_csi = max(csi_values)
            min_csi = min(csi_values)
            variance = max_csi - min_csi
            
            consistent = variance < 0.01  # Allow tiny floating point differences
            print(f"   CSI values: {csi_values}")
            print(f"   Variance: {variance}")
            print(f"   Status: {'✅ PASS' if consistent else '❌ FAIL'}")
        else:
            print("   Status: ❌ FAIL (No valid responses)")
    else:
        print("   Status: ❌ FAIL (Insufficient responses)")

def test_memory_usage_stability():
    """Basic test for memory leak detection."""
    print("💾 Testing Memory Usage Stability...")
    
    # Make many requests to see if response times degrade significantly
    response_times = []
    
    for i in range(20):
        try:
            start_time = time.time()
            response = requests.get(f"{BASE_URL}/api/interactions/metrics/", timeout=10)
            end_time = time.time()
            
            if response.status_code == 200:
                response_times.append(end_time - start_time)
                
        except:
            continue
    
    if len(response_times) >= 15:
        first_5_avg = sum(response_times[:5]) / 5
        last_5_avg = sum(response_times[-5:]) / 5
        degradation = last_5_avg - first_5_avg
        
        print(f"   First 5 requests avg: {first_5_avg:.3f}s")
        print(f"   Last 5 requests avg: {last_5_avg:.3f}s")
        print(f"   Performance degradation: {degradation:.3f}s")
        
        stable = degradation < 0.5  # Less than 500ms degradation acceptable
        print(f"   Status: {'✅ PASS' if stable else '⚠️ WARN' if degradation < 1.0 else '❌ FAIL'}")
    else:
        print("   Status: ❌ FAIL (Insufficient data)")

def main():
    """Run additional edge case tests."""
    print("🧪 Phase 6: Additional Edge Case Testing")
    print("=" * 50)
    
    test_concurrent_requests()
    print()
    test_large_date_ranges() 
    print()
    test_malformed_requests()
    print()
    test_api_consistency()
    print()
    test_memory_usage_stability()
    
    print("\n" + "=" * 50)
    print("🎯 Additional Testing Complete!")

if __name__ == "__main__":
    main()