"""
Unit tests for the new Customer Satisfaction Index (CSI) calculation logic
in the Analytics Service.
"""
import unittest
from unittest.mock import Mock
from models import Conversation
from services.analytics_service import calculate_and_set_csi_score, CSI_WEIGHTS

class TestCSICalculation(unittest.TestCase):

    def test_calculate_and_set_csi_score_happy_path(self):
        """Test that the CSI score is calculated correctly with valid inputs."""
        conv = Conversation(
            effectiveness_score=8.0,
            efficiency_score=9.0,
            effort_score=7.0,
            empathy_score=8.5
        )

        calculate_and_set_csi_score(conv)

        expected_score = (
            (8.0 * CSI_WEIGHTS['effectiveness']) +
            (9.0 * CSI_WEIGHTS['efficiency']) +
            (7.0 * CSI_WEIGHTS['effort']) +
            (8.5 * CSI_WEIGHTS['empathy'])
        )

        self.assertIsNotNone(conv.csi_score)
        self.assertAlmostEqual(conv.csi_score, round(expected_score, 2))

    def test_csi_score_is_none_if_any_pillar_is_missing(self):
        """Test that the CSI score is None if any of the pillar scores are missing."""
        conv = Conversation(
            effectiveness_score=8.0,
            efficiency_score=9.0,
            # effort_score is missing
            empathy_score=8.5
        )

        calculate_and_set_csi_score(conv)

        self.assertIsNone(conv.csi_score)

    def test_csi_score_with_zero_values(self):
        """Test that the CSI score is calculated correctly when pillar scores are zero."""
        conv = Conversation(
            effectiveness_score=0.0,
            efficiency_score=0.0,
            effort_score=0.0,
            empathy_score=0.0
        )

        calculate_and_set_csi_score(conv)

        self.assertIsNotNone(conv.csi_score)
        self.assertEqual(conv.csi_score, 0.0)

    def test_csi_score_with_max_values(self):
        """Test that the CSI score is calculated correctly when pillar scores are at their max (10)."""
        conv = Conversation(
            effectiveness_score=10.0,
            efficiency_score=10.0,
            effort_score=10.0,
            empathy_score=10.0
        )

        calculate_and_set_csi_score(conv)

        # The sum of weights is 1.0, so the score should be 10.
        self.assertIsNotNone(conv.csi_score)
        self.assertAlmostEqual(conv.csi_score, 10.0)

if __name__ == '__main__':
    unittest.main()
