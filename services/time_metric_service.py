# This file contains the logic for calculating time-based metrics.

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from models import DailyAnalysis, Message

logger = logging.getLogger(__name__)

def calculate_time_metrics_for_daily_analysis(daily_analysis: DailyAnalysis) -> Dict[str, Optional[float]]:
    """
    Calculates time-based metrics for a single DailyAnalysis object.

    Args:
        daily_analysis: The DailyAnalysis object, with its messages pre-loaded.

    Returns:
        A dictionary containing the calculated time metrics.
    """
    messages = sorted(
        [m for m in daily_analysis.conversation.messages if m.social_create_time.date() == daily_analysis.analysis_date.date()],
        key=lambda m: m.social_create_time
    )

    if not messages:
        return {
            "first_response_time": None,
            "avg_response_time": None,
            "total_handling_time": None,
        }

    # Total Handling Time (in minutes)
    total_handling_time = (messages[-1].social_create_time - messages[0].social_create_time).total_seconds() / 60

    # First Response Time and Average Response Time
    first_response_time = None
    response_times = []
    customer_message_time = None

    for msg in messages:
        if msg.direction == 'to_company':
            if customer_message_time is None:
                customer_message_time = msg.social_create_time
        elif msg.direction == 'to_client' and customer_message_time:
            response_delta = (msg.social_create_time - customer_message_time).total_seconds()
            if first_response_time is None:
                first_response_time = response_delta
            response_times.append(response_delta)
            customer_message_time = None # Reset after an agent responds

    avg_response_time = sum(response_times) / len(response_times) if response_times else None

    return {
        "first_response_time": first_response_time,
        "avg_response_time": avg_response_time,
        "total_handling_time": total_handling_time,
    }
