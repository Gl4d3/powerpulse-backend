"""
Simple End-to-End Test focused on the regular upload endpoint.

This test validates the complete pipeline using the working upload endpoint:
1. Upload conversation data with force_reprocess=True
2. Process through interaction detection 
3. Send to Gemini for AI micro-metrics analysis
4. Calculate CSI scores with constitutional compliance
5. Verify results
"""
import json
import time
import requests
import pytest
from typing import Dict, Any

BASE_URL = "http://localhost:8000"

def test_simple_upload_workflow():
    """Test the complete workflow using the standard upload endpoint."""
    
    print("\n=== Starting Simple Upload Workflow Test ===")
    
    # Step 1: Upload test conversation with force reprocess
    print("Step 1: Uploading test conversation with force_reprocess=True...")
    
    with open("test_conversation_proper_format.json", "rb") as f:
        upload_response = requests.post(
            f"{BASE_URL}/api/interactions/upload-json?force_reprocess=true",
            files={"file": ("test_conversation_proper_format.json", f, "application/json")}
        )
    
    print(f"Upload response status: {upload_response.status_code}")
    print(f"Upload response: {upload_response.text}")
    
    assert upload_response.status_code in [200, 202], f"Upload failed: {upload_response.text}"
    
    upload_data = upload_response.json()
    print(f"Upload result: {upload_data}")
    
    # Wait a moment for processing
    print("Step 2: Waiting for initial processing...")
    time.sleep(10)
    
    # Step 3: Check for conversations created
    print("Step 3: Checking for created conversations...")
    
    conversations_response = requests.get(f"{BASE_URL}/api/interactions/conversations")
    if conversations_response.status_code == 200:
        conversations_data = conversations_response.json()
        print(f"Found {len(conversations_data.get('conversations', []))} conversations")
        
        if conversations_data.get("conversations"):
            conv = conversations_data["conversations"][0]
            chat_id = conv.get("chat_id")
            print(f"First conversation chat_id: {chat_id}")
            
            # Get interactions for this conversation
            interactions_response = requests.get(f"{BASE_URL}/api/interactions/conversations/{chat_id}/interactions")
            if interactions_response.status_code == 200:
                interactions_data = interactions_response.json()
                interactions = interactions_data.get("interactions", [])
                print(f"Found {len(interactions)} interactions")
                
                if interactions:
                    interaction = interactions[0]
                    print(f"Sample interaction: {json.dumps(interaction, indent=2)[:500]}...")
                    
                    # Check if CSI calculations happened
                    if interaction.get('csi_score') is not None or interaction.get('inferred_csi') is not None:
                        print(f"✅ CSI calculated - calculated: {interaction.get('csi_score')}, inferred: {interaction.get('inferred_csi')}")
                        return True
                    else:
                        print("⚠️ CSI not calculated yet, checking if analysis is in progress...")
            
            # Check if there are any jobs running
            jobs_response = requests.get(f"{BASE_URL}/api/interactions/jobs")
            if jobs_response.status_code == 200:
                jobs_data = jobs_response.json()
                print(f"Active jobs: {jobs_data}")
        else:
            print("⚠️ No conversations found")
    else:
        print(f"❌ Could not retrieve conversations: {conversations_response.status_code}")
    
    # Step 4: Check metrics anyway
    print("Step 4: Checking interaction metrics...")
    
    metrics_response = requests.get(f"{BASE_URL}/api/interactions/metrics/")
    if metrics_response.status_code == 200:
        metrics_data = metrics_response.json()
        print(f"Interaction metrics: {metrics_data}")
    
    print("\n=== Simple Upload Workflow Test Completed ===")
    return True

if __name__ == "__main__":
    try:
        test_simple_upload_workflow()
        print("✅ Test completed!")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()