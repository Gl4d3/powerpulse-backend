# Frontend Update: Enhanced Conversation Explorer Endpoint

Hi Team,

This document outlines the recent enhancements to the Conversation Explorer API endpoint: `GET /api/explorer/analyses`.

Based on feedback, we've enriched this endpoint to provide a comprehensive set of metrics for each daily analysis record. This change is designed to give you all the necessary data in a single call, simplifying frontend development and state management.

## Endpoint

`GET /api/explorer/analyses`

## What's New

The `data` array in the response now includes the following new fields for each daily analysis object:

### 1. All Micro-Metrics

You now have access to all the underlying metrics that are used to calculate the main CSI pillars:

*   `sentiment_score` (float): Overall customer sentiment for the day (0-10).
*   `sentiment_shift` (float): Change in sentiment from start to end of the day (-5 to +5).
*   `resolution_achieved` (float): Score indicating if the customer's issue was resolved (0-10).
*   `fcr_score` (float): First Contact Resolution score for that day (0-10).
*   `ces` (float): Customer Effort Score (1-7, where 1 is high effort and 7 is low effort).
*   `first_response_time` (float): Time in seconds for the first agent response.
*   `avg_response_time` (float): Average agent response time in seconds for the day.
*   `total_handling_time` (float): Total time in minutes spent by agents on the conversation for the day.

### 2. Total Conversation Duration

A new time-based metric has been added:

*   `conversation_duration` (float): The total duration of the **entire conversation** (from the very first to the very last message) in seconds. This is repeated for each daily analysis belonging to that conversation.

## Important Note

The endpoint will only return analysis records where the `csi_score` has been fully calculated and is not `null`.

## Example Response Object

Here is an example of what a single object in the `data` array now looks like:

```json
{
    "daily_analysis_id": 101,
    "conversation_id": "chat-xyz-123",
    "customer_name": "Jane Doe",
    "analysis_date": "2025-09-08",
    "csi_score": 8.5,
    "effectiveness_score": 9.0,
    "efficiency_score": 8.0,
    "effort_score": 7.5,
    "empathy_score": 9.5,
    "common_topics": ["Billing/Statement Request", "Power Outage Follow Up"],
    "conversation_duration": 86400.0,
    "sentiment_score": 8.2,
    "sentiment_shift": 1.5,
    "resolution_achieved": 9.0,
    "fcr_score": 10.0,
    "ces": 6.5,
    "first_response_time": 120.0,
    "avg_response_time": 180.0,
    "total_handling_time": 15.5
}
```

Please let me know if you have any questions.
