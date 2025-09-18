"""
Final End-to-End Workflow Test for PowerPulse Constitutional Compliance.

This test simulates the entire user journey:
1. Uploads a sample interaction file using the enhanced endpoint.
2. Polls the status endpoint until processing is complete.
3. Verifies that the session was constitutionally compliant.
4. Fetches and validates the final analysis results.
"""
import asyncio
import json
import os
import time
from typing import Dict, Any

import pytest
import requests

# --- Test Configuration ---
BASE_URL = "http://localhost:8000"
SAMPLE_DATA_PATH = "sample_interaction_data.json" 
# Using a smaller, more focused sample for E2E test speed
# For a full regression, 'e2e_test_data.json' could be used.

# --- Helper Functions ---

def get_api_url(path: str) -> str:
    """Constructs the full API URL."""
    return f"{BASE_URL}{path}"

def check_server_status() -> bool:
    """Checks if the FastAPI server is running."""
    try:
        response = requests.get(get_api_url("/health"), timeout=5)
        return response.status_code == 200
    except requests.ConnectionError:
        return False

# --- Pytest Fixtures ---

@pytest.fixture(scope="module")
def test_data():
    """Loads the sample interaction data from file."""
    if not os.path.exists(SAMPLE_DATA_PATH):
        pytest.fail(f"Sample data file not found at: {SAMPLE_DATA_PATH}")
    with open(SAMPLE_DATA_PATH, "r") as f:
        return json.load(f)

@pytest.fixture(scope="module", autouse=True)
def wait_for_server():
    """Waits for the server to be available before running tests."""
    start_time = time.time()
    while not check_server_status():
        time.sleep(1)
        if time.time() - start_time > 30: # 30-second timeout
            pytest.fail("Server did not start within 30 seconds.")
    print("Server is up and running.")

# --- End-to-End Test ---

@pytest.mark.e2e
def test_full_constitutional_workflow(test_data: Dict[str, Any]):
    """
    Tests the complete end-to-end workflow from upload to result validation.
    """
    # --- 1. Upload Data ---
    with open(SAMPLE_DATA_PATH, 'rb') as f:
        upload_response = requests.post(
            get_api_url("/api/interactions/upload-json-enhanced"),
            files={'file': ('sample_interaction_data.json', f, 'application/json')}
        )
    assert upload_response.status_code == 202, "Failed to initiate upload"
    upload_data = upload_response.json()
    session_id = upload_data.get("session_id")
    assert session_id, "Response missing session_id"
    print(f"Upload initiated. Session ID: {session_id}")

    # --- 2. Poll for Status ---
    processing_status = ""
    start_time = time.time()
    timeout = 180  # 3 minutes
    
    while processing_status not in ["completed", "failed", "partial_success"]:
        if time.time() - start_time > timeout:
            pytest.fail(f"Processing timed out after {timeout} seconds.")
        
        time.sleep(5) # Poll every 5 seconds
        status_response = requests.get(get_api_url(f"/api/upload-status/{session_id}"))
        assert status_response.status_code == 200, "Failed to get status"
        status_data = status_response.json()
        processing_status = status_data.get("status")
        print(f"Polling status... Current status: {processing_status}")

    assert processing_status == "completed", f"Processing ended with status: {processing_status}"

    # --- 3. Verify Constitutional Compliance ---
    compliance_response = requests.get(get_api_url(f"/api/constitutional/compliance?session_id={session_id}"))
    assert compliance_response.status_code == 200, "Failed to get compliance data"
    compliance_data = compliance_response.json()
    
    print("Verifying Constitutional Compliance...")
    assert compliance_data.get("overall_compliance_status") is True, "Overall compliance check failed"
    
    # Check key constitutional pillars
    supremacy = compliance_data.get("ai_micro_metrics_supremacy", {})
    dual_csi = compliance_data.get("dual_csi_architecture", {})
    cost_opt = compliance_data.get("cost_optimization", {})

    assert supremacy.get("compliant") is True, "AI Micro-Metrics Supremacy was not met"
    assert dual_csi.get("compliant") is True, "Dual CSI Architecture was not met"
    assert cost_opt.get("compliant") is True, "Cost Optimization target was not met"
    print("Constitutional Compliance: PASSED")

    # --- 4. Fetch and Validate Results ---
    results_response = requests.get(get_api_url(f"/api/results/{session_id}"))
    assert results_response.status_code == 200, "Failed to fetch final results"
    results_data = results_response.json()

    print("Validating final results...")
    assert "analysis_results" in results_data, "Results missing 'analysis_results' key"
    analysis_results = results_data["analysis_results"]
    assert isinstance(analysis_results, list), "'analysis_results' should be a list"
    assert len(analysis_results) > 0, "No analysis results were returned"

    # Validate a sample result
    sample_result = analysis_results[0]
    assert "interaction_id" in sample_result
    assert "calculated_csi" in sample_result
    assert "inferred_csi" in sample_result
    assert "ai_micro_metrics" in sample_result
    assert "constitutional_validation" in sample_result
    
    # Check for valid CSI scores (0-1 range from batch processing)
    assert 0 <= sample_result["calculated_csi"] <= 1
    assert 0 <= sample_result["inferred_csi"] <= 1
    
    print("Final Results Validation: PASSED")
    print("--- E2E Test Completed Successfully ---")

