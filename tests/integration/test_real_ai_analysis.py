import pytest
import json
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import patch, AsyncMock

from models import Conversation
from config import settings
from services.gemini_service import GeminiService, get_gemini_service, gemini_service_instance

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration

@pytest.fixture(scope="module")
def real_gemini_api_key():
    # This fixture provides the actual API key for real AI calls
    # Ensure settings.GEMINI_API_KEY is correctly set in your .env or config
    if not settings.GEMINI_API_KEY:
        pytest.skip("GEMINI_API_KEY not set, skipping real AI integration test.")
    return settings.GEMINI_API_KEY

@pytest.fixture(scope="function")
def real_gemini_service_instance(real_gemini_api_key):
    # This fixture provides a real GeminiService instance for the test
    # We need to ensure the global instance is reset for each test function
    # to avoid interference from other tests or previous runs.
    global gemini_service_instance
    original_instance = gemini_service_instance
    gemini_service_instance = None # Reset global instance
    service = get_gemini_service(real_gemini_api_key)
    yield service
    gemini_service_instance = original_instance # Restore original instance

@pytest.mark.asyncio
async def test_real_ai_analysis_of_snippet(client: TestClient, test_db_session: Session, real_gemini_service_instance: GeminiService):
    """
    Tests the full application flow using the real Gemini AI service
    to analyze conversations from a snippet, verifying CSI scores.
    """
    # Ensure the real GeminiService is used by patching get_gemini_service
    # to return our real_gemini_service_instance
    with patch('services.job_service.gemini_service.get_gemini_service', return_value=real_gemini_service_instance):
        # 1. Upload the test data file (snippet_1755240593792.json)
        # Read the snippet file
        with open("attached_assets/snippet_1755240593792.json", "rb") as f:
            response = client.post("/api/upload-json", files={"file": ("snippet_1755240593792.json", f, "application/json")})
        
        assert response.status_code == 200
        assert response.json()["message"] == "Successfully processed 20 conversations" # Assuming 20 conversations in the snippet

        # 2. Verify the background job was processed and CSI scores are in DB
        # In the TestClient, background tasks run sequentially, so we can immediately check the results.
        conversations = test_db_session.query(Conversation).order_by(Conversation.fb_chat_id).all()
        assert len(conversations) == 20 # Assuming 20 conversations in the snippet

        # Assert that CSI scores are populated for all conversations
        for conv in conversations:
            assert conv.effectiveness_score is not None
            assert conv.efficiency_score is not None
            assert conv.effort_score is not None
            assert conv.empathy_score is not None
            assert conv.csi_score is not None
            assert conv.csi_score > 0 # Ensure scores are calculated and not just default 0

        # 3. Verify the metrics endpoint
        client.post("/api/metrics/recalculate")
        response = client.get("/api/metrics")
        assert response.status_code == 200
        metrics = response.json()
        assert metrics["total_conversations_analyzed"] == 20
        assert metrics["overall_csi_score"] > 0

        # 4. Verify the conversations endpoint
        response = client.get("/api/conversations")
        assert response.status_code == 200
        convos_response = response.json()
        assert len(convos_response["conversations"]) == 20

        # 5. Verify the download endpoint
        response = client.get("/api/download")
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        
        import pandas as pd
        import io
        download_data_df = pd.read_csv(io.StringIO(response.text))
        assert len(download_data_df) == 20
        assert "csi_score" in download_data_df.columns
        assert download_data_df["csi_score"].isnull().sum() == 0 # No null CSI scores
