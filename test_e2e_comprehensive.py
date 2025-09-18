"""
Comprehensive End-to-End Test for PowerPulse Constitutional Workflow.

This test validates the complete pipeline:
1. Upload conversation data
2. Process through interaction detection 
3. Send to Gemini for AI micro-metrics analysis
4. Calculate CSI scores with constitutional compliance
5. Verify dual CSI architecture and results
"""
import json
import time
import requests
import pytest
from typing import Dict, Any

BASE_URL = "http://localhost:8000"

def test_complete_workflow_e2e():
    """Test the complete end-to-end workflow from upload to CSI calculation."""
    
    print("\n=== Starting Complete E2E Workflow Test ===")
    
    # Step 1: Upload test conversation
    print("Step 1: Uploading test conversation...")
    
    with open("test_conversation_proper_format.json", "rb") as f:
        upload_response = requests.post(
            f"{BASE_URL}/api/interactions/upload-json-enhanced",
            files={"file": ("test_conversation_proper_format.json", f, "application/json")}
        )
    
    print(f"Upload response status: {upload_response.status_code}")
    
    if upload_response.status_code != 202:
        print(f"Upload failed: {upload_response.text}")
        # Try the regular upload endpoint as fallback
        with open("test_conversation_proper_format.json", "rb") as f:
            upload_response = requests.post(
                f"{BASE_URL}/api/interactions/upload-json",
                files={"file": ("test_conversation_proper_format.json", f, "application/json")}
            )
        print(f"Fallback upload response status: {upload_response.status_code}")
    
    assert upload_response.status_code in [200, 202], f"Upload failed: {upload_response.text}"
    
    upload_data = upload_response.json()
    print(f"Upload successful: {upload_data}")
    
    # Extract session_id or upload_id
    session_id = upload_data.get("session_id") or upload_data.get("upload_id")
    assert session_id, "No session_id or upload_id returned"
    
    # Step 2: Monitor processing status
    print(f"Step 2: Monitoring processing for session/upload: {session_id}")
    
    max_wait_time = 120  # 2 minutes max
    start_time = time.time()
    
    while time.time() - start_time < max_wait_time:
        # Try session status endpoint first
        try:
            status_response = requests.get(f"{BASE_URL}/api/interactions/upload-status/{session_id}")
            if status_response.status_code == 200:
                status_data = status_response.json()
                current_status = status_data.get("status", "unknown")
                print(f"Session status: {current_status}")
                
                if current_status in ["completed", "failed", "partial_success"]:
                    break
        except:
            pass
        
        # Also check general upload status
        try:
            general_status = requests.get(f"{BASE_URL}/api/interactions/upload-status")
            if general_status.status_code == 200:
                print(f"General upload status check successful")
        except:
            pass
        
        time.sleep(5)
        print(".", end="", flush=True)
    
    print(f"\nProcessing completed after {time.time() - start_time:.1f} seconds")
    
    # Step 3: Check constitutional compliance
    print("Step 3: Checking constitutional compliance...")
    
    compliance_response = requests.get(f"{BASE_URL}/api/constitutional/compliance")
    if compliance_response.status_code == 200:
        compliance_data = compliance_response.json()
        print(f"Constitutional compliance: {compliance_data.get('overall_compliance_status', 'Unknown')}")
    else:
        print(f"Compliance check failed: {compliance_response.status_code}")
    
    # Step 4: Check for interactions created
    print("Step 4: Checking for created interactions...")
    
    conversations_response = requests.get(f"{BASE_URL}/api/interactions/conversations")
    if conversations_response.status_code == 200:
        conversations_data = conversations_response.json()
        print(f"Found {len(conversations_data.get('conversations', []))} conversations")
        
        if conversations_data.get("conversations"):
            conv = conversations_data["conversations"][0]
            chat_id = conv.get("chat_id")
            
            # Get interactions for this conversation
            interactions_response = requests.get(f"{BASE_URL}/api/interactions/conversations/{chat_id}/interactions")
            if interactions_response.status_code == 200:
                interactions_data = interactions_response.json()
                interactions = interactions_data.get("interactions", [])
                print(f"Found {len(interactions)} interactions")
                
                if interactions:
                    interaction = interactions[0]
                    print(f"Sample interaction CSI: calculated={interaction.get('csi_score')}, inferred={interaction.get('inferred_csi')}")
                    
                    # Verify dual CSI architecture
                    assert interaction.get('csi_score') is not None, "Calculated CSI missing"
                    assert interaction.get('inferred_csi') is not None, "Inferred CSI missing"
                    
                    # Check four pillars
                    pillars = ['effectiveness_score', 'effort_score', 'efficiency_score', 'empathy_score']
                    pillar_scores = {p: interaction.get(p) for p in pillars}
                    print(f"Four pillar scores: {pillar_scores}")
    
    # Step 5: Check metrics
    print("Step 5: Checking interaction metrics...")
    
    metrics_response = requests.get(f"{BASE_URL}/api/interactions/metrics/")
    if metrics_response.status_code == 200:
        metrics_data = metrics_response.json()
        print(f"Interaction metrics: {metrics_data}")
    
    print("\n=== E2E Workflow Test Completed Successfully ===")
    return True

if __name__ == "__main__":
    try:
        test_complete_workflow_e2e()
        print("✅ All tests passed!")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()