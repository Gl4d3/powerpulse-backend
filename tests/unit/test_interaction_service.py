"""
Unit tests for interaction detection service.
Tests the implemented interaction boundary detection logic.
"""
import pytest
from datetime import datetime, timedelta
from typing import List, Dict

from services.interaction_service import InteractionService, InteractionSegment, InteractionDetectionConfig


class TestInteractionDetection:
    """Test suite for interaction boundary detection logic."""

    def test_detect_time_gap_interactions(self):
        """
        Test detection of interactions split by 4+ hour gaps.
        
        Based on Daniel W* sample:
        - Interaction 1: Aug 18, 10:55-14:58 (resolved + thanks)
        - 4-day gap
        - Interaction 2: Aug 22, 09:09+ (new complaint)
        """
        # Sample messages simulating Daniel W* pattern
        messages = [
            {
                "id": 1,
                "social_create_time": datetime(2025, 8, 18, 10, 55, 25),
                "message_content": "Hello",
                "direction": "to_company"
            },
            {
                "id": 2, 
                "social_create_time": datetime(2025, 8, 18, 14, 58, 32),
                "message_content": "Power restored",
                "direction": "to_company"
            },
            {
                "id": 3,
                "social_create_time": datetime(2025, 8, 18, 14, 58, 35), 
                "message_content": "Thanks",
                "direction": "to_company"
            },
            {
                "id": 4,
                "social_create_time": datetime(2025, 8, 22, 9, 9, 36),
                "message_content": "Hello",
                "direction": "to_company"
            },
            {
                "id": 5,
                "social_create_time": datetime(2025, 8, 22, 9, 10, 51),
                "message_content": "We have another power outage again same place",
                "direction": "to_company"
            }
        ]
        
        # Expected: 2 interactions detected
        # Interaction 1: messages 1-3 (Aug 18) - resolution + thanks
        # Interaction 2: messages 4-5 (Aug 22) - 4-day gap + new issue
        
        service = InteractionService()
        interactions = service.detect_interactions(messages)
        
        assert len(interactions) == 2
        assert interactions[0].start_message_id == 1
        assert interactions[0].end_message_id == 3
        assert interactions[0].boundary_method == "time_gap_after_closure"
        assert interactions[1].start_message_id == 4  
        assert interactions[1].end_message_id == 5
        assert interactions[1].boundary_method == "conversation_end"

    def test_detect_resolution_keyword_interactions(self):
        """
        Test detection based on resolution closure language.
        
        Keywords: "power restored", "thanks", "resolved", "working now", "problem solved"
        """
        messages = [
            {
                "id": 1,
                "social_create_time": datetime(2025, 8, 18, 10, 0, 0),
                "message_content": "No power in our area",
                "direction": "to_company"
            },
            {
                "id": 2,
                "social_create_time": datetime(2025, 8, 18, 10, 30, 0),
                "message_content": "We have logged your complaint",
                "direction": "to_client"
            },
            {
                "id": 3,
                "social_create_time": datetime(2025, 8, 18, 15, 0, 0),
                "message_content": "Power is back, thanks for the help",
                "direction": "to_company"
            }
        ]
        
        # Expected: 1 complete interaction with resolution detected
        # Should detect "thanks" as closure signal
        
        service = InteractionService()
        interactions = service.detect_interactions(messages)
        
        assert len(interactions) == 1
        assert interactions[0].start_message_id == 1
        assert interactions[0].end_message_id == 3
        assert interactions[0].interaction_type == "outage"  # Should classify as outage

    def test_detect_same_day_multiple_interactions(self):
        """
        Test multiple interactions on same calendar day.
        
        Based on Judy K* sample:
        - Interaction 1: 13:03-13:49 (logged complaint)
        - 6-hour gap same day  
        - Interaction 2: 20:25-20:32 (new outage)
        """
        messages = [
            {
                "id": 1,
                "social_create_time": datetime(2025, 8, 21, 13, 3, 50),
                "message_content": "Hey guys. The power has gone off",
                "direction": "to_company"
            },
            {
                "id": 2,
                "social_create_time": datetime(2025, 8, 21, 13, 49, 59),
                "message_content": "Your complaint has been logged under reference number 13491805",
                "direction": "to_client"
            },
            {
                "id": 3,
                "social_create_time": datetime(2025, 8, 21, 20, 25, 53),
                "message_content": "Hello guys. We have no power again",
                "direction": "to_company"
            },
            {
                "id": 4,
                "social_create_time": datetime(2025, 8, 21, 20, 32, 15),
                "message_content": "We're actively following up with our team",
                "direction": "to_client"
            }
        ]
        
        # Expected: 2 interactions on same day
        # Interaction 1: messages 1-2 (complaint logged = closure) 
        # Interaction 2: messages 3-4 (6+ hour gap + "again" keyword)
        
        service = InteractionService()
        interactions = service.detect_interactions(messages)
        
        assert len(interactions) == 2
        # First interaction should end after complaint logged
        assert interactions[0].start_message_id == 1
        assert interactions[0].end_message_id == 2
        # Second interaction should start with "again" message
        assert interactions[1].start_message_id == 3
        assert interactions[1].end_message_id == 4

    def test_detect_escalation_patterns(self):
        """
        Test detection of escalation signals creating new interactions.
        
        Based on Cliff A* sample with "Attention" escalation signals.
        """
        messages = [
            {
                "id": 1,
                "social_create_time": datetime(2025, 8, 17, 21, 36, 10),
                "message_content": "Attention",
                "direction": "to_company"
            },
            {
                "id": 2,
                "social_create_time": datetime(2025, 8, 17, 21, 36, 18),
                "message_content": "No power at iduku primary",
                "direction": "to_company"
            },
            {
                "id": 3,
                "social_create_time": datetime(2025, 8, 17, 23, 28, 16),
                "message_content": "Your complaint has been logged under reference 13470029",
                "direction": "to_client"
            },
            {
                "id": 4,
                "social_create_time": datetime(2025, 8, 19, 19, 50, 59),
                "message_content": "Attention",  # Escalation signal
                "direction": "to_company"
            },
            {
                "id": 5,
                "social_create_time": datetime(2025, 8, 19, 19, 51, 12),
                "message_content": "No power again",
                "direction": "to_company"
            }
        ]
        
        # Expected: 2 interactions
        # Interaction 1: messages 1-3 (initial complaint + logged)
        # Interaction 2: messages 4-5 (escalation with "Attention" + time gap)
        
        assert len(messages) == 5
        pytest.skip("Implementation pending in Phase 2")

    def test_ai_fallback_trigger_conditions(self):
        """
        Test when AI fallback should be triggered for complex cases.
        
        Conditions:
        - >20 messages AND no clear rule-based splits
        - Ambiguous conversation patterns
        """
        # Create a long conversation with no clear boundaries
        messages = []
        base_time = datetime(2025, 8, 18, 10, 0, 0)
        
        for i in range(25):  # 25 messages (>20 threshold)
            messages.append({
                "id": i + 1,
                "social_create_time": base_time + timedelta(minutes=i * 10),
                "message_content": f"Message {i + 1} with no clear resolution pattern",
                "direction": "to_company" if i % 2 == 0 else "to_client"
            })
        
        # Expected: AI fallback should be triggered
        # No time gaps >4h, no resolution keywords, >20 messages
        
        assert len(messages) == 25
        pytest.skip("Implementation pending in Phase 2")

    def test_topic_shift_detection(self):
        """
        Test detection of topic changes within conversations.
        
        Topic transitions: "outage" → "billing", "prepaid" → "postpaid"
        """
        messages = [
            {
                "id": 1,
                "social_create_time": datetime(2025, 8, 18, 10, 0, 0),
                "message_content": "Power outage in our area",
                "direction": "to_company"
            },
            {
                "id": 2,
                "social_create_time": datetime(2025, 8, 18, 15, 0, 0),
                "message_content": "Power restored, thank you",
                "direction": "to_company"
            },
            {
                "id": 3,
                "social_create_time": datetime(2025, 8, 18, 16, 0, 0),
                "message_content": "Also, I have a billing question about my prepaid meter",
                "direction": "to_company"
            },
            {
                "id": 4,
                "social_create_time": datetime(2025, 8, 18, 16, 30, 0),
                "message_content": "Please check your meter balance",
                "direction": "to_client"
            }
        ]
        
        # Expected: 2 interactions
        # Interaction 1: messages 1-2 (outage resolved)
        # Interaction 2: messages 3-4 (billing topic shift)
        
        assert len(messages) == 4
        pytest.skip("Implementation pending in Phase 2")

    def test_reference_number_pattern_detection(self):
        """
        Test detection of new reference numbers indicating separate interactions.
        
        Pattern: "13459714" → "13495277" suggests new complaint
        """
        messages = [
            {
                "id": 1,
                "social_create_time": datetime(2025, 8, 18, 10, 0, 0),
                "message_content": "Power issue reported",
                "direction": "to_company"
            },
            {
                "id": 2,
                "social_create_time": datetime(2025, 8, 18, 10, 30, 0),
                "message_content": "Complaint recorded under reference 13459714",
                "direction": "to_client"
            },
            {
                "id": 3,
                "social_create_time": datetime(2025, 8, 22, 9, 0, 0),
                "message_content": "Another outage in same area",
                "direction": "to_company"
            },
            {
                "id": 4,
                "social_create_time": datetime(2025, 8, 22, 9, 30, 0),
                "message_content": "New complaint logged under reference 13495277",
                "direction": "to_client"
            }
        ]
        
        # Expected: 2 interactions based on different reference numbers
        
        assert len(messages) == 4
        pytest.skip("Implementation pending in Phase 2")


class TestInteractionAnalysisModel:
    """Test suite for InteractionAnalysis model (to be implemented in Phase 3)."""

    def test_interaction_analysis_model_creation(self):
        """Test InteractionAnalysis model fields and relationships."""
        # Will test model creation, field validation, and relationships
        # after implementation in Phase 3
        pytest.skip("Model implementation pending in Phase 3")

    def test_interaction_analysis_csi_calculation(self):
        """Test CSI calculation for interaction-based analysis."""
        # Will test that CSI calculation works with interaction boundaries
        # Same formula as daily analysis but with interaction-specific metrics
        pytest.skip("CSI calculation implementation pending in Phase 4")


class TestInteractionEndpoints:
    """Test suite for new interaction-based API endpoints (to be implemented in Phase 5)."""

    def test_upload_interaction_json_endpoint(self):
        """Test new upload endpoint processes interactions correctly."""
        # Will test POST /api/upload-interaction-json
        pytest.skip("Endpoint implementation pending in Phase 5")

    def test_interaction_explorer_endpoint(self):
        """Test interaction listing endpoint."""
        # Will test GET /api/explorer/interactions
        pytest.skip("Endpoint implementation pending in Phase 5")

    def test_interaction_transcript_endpoint(self):
        """Test individual interaction transcript endpoint."""
        # Will test GET /api/explorer/transcript/{interaction_analysis_id}
        pytest.skip("Endpoint implementation pending in Phase 5")


# Configuration constants for interaction detection
# These will be used in the actual implementation

INTERACTION_DETECTION_CONFIG = {
    "time_gap_hours": 4,  # Default gap threshold for new interactions
    "ai_fallback_message_threshold": 20,  # Trigger AI when >20 messages with no rules
    "resolution_keywords": [
        "power restored", "thanks", "resolved", "working now", "problem solved",
        "issue fixed", "back on supply", "restored", "sorted"
    ],
    "escalation_keywords": [
        "attention", "urgent", "again", "still", "not resolved", "escalate"
    ],
    "topic_keywords": {
        "outage": ["power", "outage", "blackout", "no electricity", "no supply"],
        "billing": ["bill", "payment", "account", "charges", "balance"],
        "prepaid": ["prepaid", "token", "vend", "top up"],
        "postpaid": ["postpaid", "monthly", "statement"]
    },
    "reference_number_pattern": r"1\d{7}"  # Kenya Power reference format
}