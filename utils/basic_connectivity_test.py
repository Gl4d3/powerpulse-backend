"""
Simplified upload test to bypass service issues and test basic functionality
"""
import requests
import json
import io

def test_basic_interaction_upload():
    """Test basic interaction upload bypassing enhanced features for now"""
    
    # Use the original upload endpoint that should work
    test_data = [
        {
            "conversation_id": "simple_test_001",
            "timestamp": "2025-09-17T10:00:00Z", 
            "messages": [
                {
                    "role": "user",
                    "content": "Hello, I need help with my power connection",
                    "timestamp": "2025-09-17T10:00:00Z"
                },
                {
                    "role": "assistant",
                    "content": "I can help you with that. What seems to be the issue?",
                    "timestamp": "2025-09-17T10:01:00Z"
                }
            ]
        }
    ]
    
    # Save to temp file
    with open('simple_test.json', 'w') as f:
        json.dump(test_data, f)
    
    # Try the basic upload endpoint first
    print("🧪 Testing basic upload endpoint...")
    try:
        with open('simple_test.json', 'rb') as f:
            files = {'file': ('test.json', f, 'application/json')}
            
            response = requests.post(
                "http://localhost:8000/api/interaction/upload-json",
                files=files,
                timeout=30
            )
        
        print(f"Basic Upload Status: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        
        if response.status_code == 202:
            return True
            
    except Exception as e:
        print(f"Basic upload error: {e}")
    
    return False

def test_available_endpoints():
    """Test what endpoints are actually available"""
    endpoints_to_test = [
        "/",
        "/docs", 
        "/api/interaction/batch-config",
        "/api/interaction/constitutional/compliance"
    ]
    
    print("\n🔍 Testing available endpoints...")
    for endpoint in endpoints_to_test:
        try:
            response = requests.get(f"http://localhost:8000{endpoint}", timeout=10)
            print(f"  {endpoint}: {response.status_code}")
        except Exception as e:
            print(f"  {endpoint}: ERROR - {e}")

if __name__ == "__main__":
    print("🚨 PowerPulse Basic Connectivity Test")
    print("=" * 50)
    
    test_available_endpoints()
    
    success = test_basic_interaction_upload()
    
    if success:
        print("\n✅ Basic upload successful! Server is working.")
    else:
        print("\n❌ Basic upload failed. Need to fix core functionality.")