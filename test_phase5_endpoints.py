"""
Test Phase 5: New API Endpoints
Tests the interaction-based API endpoints to ensure they're properly implemented
and return the expected response structures.
"""
import requests
import json
from datetime import datetime, date, timedelta
import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_interaction_endpoints():
    """Test the new interaction-based API endpoints"""
    
    base_url = "http://localhost:8080"
    
    print("=== Testing Phase 5: New API Endpoints ===")
    
    # Test date range
    end_date = date.today()
    start_date = end_date - timedelta(days=30)
    
    print(f"Testing with date range: {start_date} to {end_date}")
    
    # Test endpoints
    test_cases = [
        {
            "name": "Interaction Metrics",
            "url": f"{base_url}/api/interactions/metrics/",
            "method": "GET"
        },
        {
            "name": "Interaction Historical Metrics",
            "url": f"{base_url}/api/interactions/metrics/historical?start_date={start_date}&end_date={end_date}",
            "method": "GET"
        },
        {
            "name": "Interaction Conversations List",
            "url": f"{base_url}/api/interactions/conversations?page=1&page_size=5",
            "method": "GET"
        },
        {
            "name": "Interaction Sentiment Trend",
            "url": f"{base_url}/api/interactions/charts/sentiment-trend?start_date={start_date}&end_date={end_date}",
            "method": "GET"
        },
        {
            "name": "Interaction CSI Trend",
            "url": f"{base_url}/api/interactions/charts/csi-trend?start_date={start_date}&end_date={end_date}",
            "method": "GET"
        },
        {
            "name": "Interaction Distribution",
            "url": f"{base_url}/api/interactions/charts/interaction-distribution?start_date={start_date}&end_date={end_date}",
            "method": "GET"
        },
        {
            "name": "Compare Analysis Modes",
            "url": f"{base_url}/api/interactions/metrics/compare?start_date={start_date}&end_date={end_date}",
            "method": "GET"
        }
    ]
    
    results = {}
    
    for test_case in test_cases:
        print(f"\n--- Testing {test_case['name']} ---")
        
        try:
            if test_case['method'] == 'GET':
                response = requests.get(test_case['url'], timeout=30)
            else:
                response = requests.post(test_case['url'], timeout=30)
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"Response Type: {type(data)}")
                    if isinstance(data, dict):
                        print(f"Response Keys: {list(data.keys())}")
                        # Show sample of response structure
                        for key, value in list(data.items())[:3]:  # First 3 items
                            if isinstance(value, (list, dict)):
                                print(f"  {key}: {type(value)} (length: {len(value) if hasattr(value, '__len__') else 'N/A'})")
                            else:
                                print(f"  {key}: {value}")
                    results[test_case['name']] = {
                        'status': 'SUCCESS',
                        'status_code': response.status_code,
                        'data_type': type(data).__name__,
                        'keys': list(data.keys()) if isinstance(data, dict) else None
                    }
                except json.JSONDecodeError:
                    print("Response is not valid JSON")
                    results[test_case['name']] = {
                        'status': 'ERROR',
                        'error': 'Invalid JSON response'
                    }
            else:
                print(f"Error Response: {response.text[:200]}...")
                results[test_case['name']] = {
                    'status': 'ERROR',
                    'status_code': response.status_code,
                    'error': response.text[:200]
                }
                
        except requests.exceptions.ConnectionError:
            print("Connection Error - Server might not be running")
            results[test_case['name']] = {
                'status': 'ERROR', 
                'error': 'Connection refused'
            }
        except Exception as e:
            print(f"Exception: {e}")
            results[test_case['name']] = {
                'status': 'ERROR',
                'error': str(e)
            }
    
    # Summary
    print("\n" + "="*60)
    print("PHASE 5 TEST SUMMARY")
    print("="*60)
    
    success_count = 0
    for test_name, result in results.items():
        status = "✅ PASS" if result['status'] == 'SUCCESS' else "❌ FAIL"
        print(f"{status} {test_name}")
        if result['status'] == 'SUCCESS':
            success_count += 1
        elif 'error' in result:
            print(f"    Error: {result['error']}")
    
    print(f"\nResults: {success_count}/{len(test_cases)} endpoints working")
    
    if success_count == len(test_cases):
        print("\n🎉 Phase 5 COMPLETE: All interaction-based API endpoints are functional!")
        return True
    else:
        print(f"\n⚠️  Phase 5 PARTIAL: {len(test_cases) - success_count} endpoints need attention")
        return False

if __name__ == "__main__":
    test_interaction_endpoints()