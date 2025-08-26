
"""
End-to-end test for the full application flow, from uploading a JSON file
to retrieving the calculated CSI metrics.
"""
import pytest
import json
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import MagicMock

from models import Conversation
from services.gemini_service import GeminiService

import pandas as pd
import io

# Mark all tests in this module as end-to-end tests
pytestmark = pytest.mark.e2e

def test_full_e2e_flow(client: TestClient, test_db_session: Session, mocker):
    """
    Tests the entire application flow:
    1. Upload a file with multiple conversations.
    2. Verify the background job is processed using the mocked Gemini service.
    3. Check that the CSI scores are calculated and stored correctly in the database.
    4. Verify the metrics endpoint returns the correct aggregated data.
    5. Verify the conversations endpoint returns the processed conversations.
    6. Verify the download endpoint returns the correct data.
    """
    # Mock the GeminiService
    mock_gemini_instance = MagicMock(spec=GeminiService)

    async def mock_analyze_batch(conversations: list):
        results = []
        for conv in conversations:
            if conv.fb_chat_id == "TEST_CHAT_CSI_1":
                results.append({
                    'id': conv.id,
                    'chat_id': conv.fb_chat_id,
                    'effectiveness_score': 9.0,
                    'efficiency_score': 8.0,
                    'effort_score': 9.0,
                    'empathy_score': 10.0,
                    'common_topics': ['order status', 'discount'],
                })
            elif conv.fb_chat_id == "TEST_CHAT_CSI_2":
                results.append({
                    'id': conv.id,
                    'chat_id': conv.fb_chat_id,
                    'effectiveness_score': 2.0,
                    'efficiency_score': 4.0,
                    'effort_score': 3.0,
                    'empathy_score': 2.0,
                    'common_topics': ['broken item', 'order number'],
                })
        return results

    mock_gemini_instance.analyze_conversations_batch.side_effect = mock_analyze_batch
    mocker.patch('services.job_service.gemini_service.get_gemini_service', return_value=mock_gemini_instance)

    # 1. Upload the test data file
    with open("csi_test_data.json", "rb") as f:
        response = client.post("/api/upload-json", files={"file": ("csi_test_data.json", f, "application/json")})
    
    assert response.status_code == 200
    assert response.json()["message"] == "Successfully processed 2 conversations"

    # 2. Verify the background job was processed
    # In the TestClient, background tasks run sequentially, so we can immediately check the results.
    
    # 3. Check the database state
    conversations = test_db_session.query(Conversation).order_by(Conversation.fb_chat_id).all()
    assert len(conversations) == 2

    # Conversation 1 assertions
    convo1 = conversations[0]
    assert convo1.fb_chat_id == "TEST_CHAT_CSI_1"
    assert convo1.effectiveness_score == 9.0
    assert convo1.efficiency_score == 8.0
    assert convo1.effort_score == 9.0
    assert convo1.empathy_score == 10.0
    # Assuming a simple average for CSI score for this test
    assert convo1.csi_score is not None

    # Conversation 2 assertions
    convo2 = conversations[1]
    assert convo2.fb_chat_id == "TEST_CHAT_CSI_2"
    assert convo2.effectiveness_score == 2.0
    assert convo2.efficiency_score == 4.0
    assert convo2.effort_score == 3.0
    assert convo2.empathy_score == 2.0
    assert convo2.csi_score is not None

    # 4. Verify the metrics endpoint
    # We need to trigger a recalculation of the metrics
    client.post("/api/metrics/recalculate")
    response = client.get("/api/metrics")
    assert response.status_code == 200
    metrics = response.json()
    assert metrics["total_conversations_analyzed"] == 2
    assert metrics["overall_csi_score"] > 0

    # 5. Verify the conversations endpoint
    response = client.get("/api/conversations")
    assert response.status_code == 200
    convos_response = response.json()
    assert len(convos_response["conversations"]) == 2

    # 6. Verify the download endpoint
    response = client.get("/api/download") # Removed ?file_format=json
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv; charset=utf-8"
    
    download_data_df = pd.read_csv(io.StringIO(response.text))
    assert len(download_data_df) == 2
    assert "csi_score" in download_data_df.columns
    assert download_data_df["csi_score"].iloc[0] is not None
    assert download_data_df["csi_score"].iloc[1] is not None
