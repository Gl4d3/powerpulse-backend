"""
Integration tests for the refactored API endpoints, focusing on CSI.
"""
import pytest
import json
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from models import Conversation

# Fixture to set up a clean database for each test function
@pytest.fixture(scope="function")
def test_db_setup(test_db_session: Session):
    # Clean up database before each test
    test_db_session.query(Conversation).delete()
    test_db_session.commit()
    yield
    # Clean up after each test
    test_db_session.query(Conversation).delete()
    test_db_session.commit()

@pytest.mark.usefixtures("test_db_setup")
class TestCSIMetricsEndpoint:
    """Test the new /api/metrics endpoint for CSI scores."""

    def test_get_metrics_empty_database(self, client: TestClient):
        """Test the metrics endpoint with an empty database, expecting zeroed metrics."""
        response = client.get("/api/metrics")
        assert response.status_code == 200
        data = response.json()
        assert data["overall_csi_score"] == 0.0
        assert data["avg_effectiveness_score"] == 0.0
        assert data["total_conversations_analyzed"] == 0

    def test_get_metrics_with_data(self, client: TestClient, test_db_session: Session):
        """Test the metrics endpoint with sample conversation data."""
        test_db_session.add(Conversation(
            fb_chat_id="CSI_TEST_1",
            csi_score=8.5, effectiveness_score=9, efficiency_score=8, effort_score=8, empathy_score=9
        ))
        test_db_session.add(Conversation(
            fb_chat_id="CSI_TEST_2",
            csi_score=7.5, effectiveness_score=8, efficiency_score=7, effort_score=7, empathy_score=8
        ))
        test_db_session.commit()

        client.post("/api/metrics/recalculate")

        response = client.get("/api/metrics")
        assert response.status_code == 200
        data = response.json()
        assert data["total_conversations_analyzed"] == 2
        assert data["overall_csi_score"] == 8.0
        assert data["avg_effectiveness_score"] == 8.5

@pytest.mark.usefixtures("test_db_setup")
class TestCSIConversationsEndpoint:
    """Test the /api/conversations endpoint for CSI scores."""

    def test_get_conversations_with_csi_data(self, client: TestClient, test_db_session: Session):
        """Test that the conversations endpoint returns the new CSI fields."""
        test_db_session.add(Conversation(
            fb_chat_id="CSI_CONV_1",
            csi_score=9.2, effectiveness_score=10, efficiency_score=9, effort_score=9, empathy_score=9
        ))
        test_db_session.commit()

        response = client.get("/api/conversations")
        assert response.status_code == 200
        data = response.json()
        assert len(data["conversations"]) == 1
        convo = data["conversations"][0]
        assert convo["fb_chat_id"] == "CSI_CONV_1"
        assert convo["csi_score"] == 9.2

    def test_get_conversations_csi_filtering(self, client: TestClient, test_db_session: Session):
        """Test filtering conversations by CSI score."""
        test_db_session.add(Conversation(fb_chat_id="CSI_LOW", csi_score=4.0))
        test_db_session.add(Conversation(fb_chat_id="CSI_HIGH", csi_score=9.0))
        test_db_session.commit()

        response = client.get("/api/conversations?min_csi_score=8.0")
        assert response.status_code == 200
        data = response.json()
        assert len(data["conversations"]) == 1
        assert data["conversations"][0]["fb_chat_id"] == "CSI_HIGH"

    def test_get_conversations_csi_sorting(self, client: TestClient, test_db_session: Session):
        """Test sorting conversations by CSI score."""
        test_db_session.add(Conversation(fb_chat_id="CSI_LOW_2", csi_score=3.0))
        test_db_session.add(Conversation(fb_chat_id="CSI_HIGH_2", csi_score=9.5))
        test_db_session.commit()

        response = client.get("/api/conversations?sort_by=csi_score&sort_order=desc")
        assert response.status_code == 200
        data = response.json()
        assert len(data["conversations"]) == 2
        assert data["conversations"][0]["fb_chat_id"] == "CSI_HIGH_2"
