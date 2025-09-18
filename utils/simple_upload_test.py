"""
Simple upload test to debug the 500 error
"""
import requests
import json

def test_simple_upload():
    # Create minimal test data
    test_data = [
        {
            "conversation_id": "test_001",
            "messages": [
                {
                    "role": "user",
                    "content": "Hello, I need help",
                    "timestamp": "2025-09-17T10:00:00Z"
                },
                {
                    "role": "assistant", 
                    "content": "How can I assist you?",
                    "timestamp": "2025-09-17T10:01:00Z"
                }
            ]
        }
    ]
    
    # Save to temp file
    with open('test_upload.json', 'w') as f:
        json.dump(test_data, f)
    
    # Try upload
    try:
        with open('test_upload.json', 'rb') as f:
            files = {'file': ('test.json', f, 'application/json')}
            data = {'batch_strategy': 'auto', 'priority': 'normal'}
            
            response = requests.post(
                "http://localhost:8000/api/interaction/upload-json-enhanced",
                files=files,
                data=data,
                timeout=30
            )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_simple_upload()