# API Contract: Conversation Explorer

**Version:** 1.0
**Status:** Proposed

This document outlines the proposed API endpoints required to power the "Conversation Explorer" feature in the PowerPulse frontend.

---

## 1. Overview

The Conversation Explorer allows users to browse and inspect individual daily analyses of conversations within a specific date range. The workflow is as follows:
1.  The user selects a date range.
2.  The frontend calls the `GET /api/explorer/analyses` endpoint to fetch a paginated list of all daily analyses within that range, including their calculated metrics and topics.
3.  The frontend displays this data in a table.
4.  The user clicks a "View Transcript" button for a specific entry in the table.
5.  The frontend calls the `GET /api/explorer/transcript/{daily_analysis_id}` endpoint to fetch the full message log for that specific day and conversation, which is then displayed in a modal or detail view.

---

## 2. Endpoints

### Endpoint 1: Get Daily Analyses for Explorer Table

Fetches a paginated list of daily analyses with their associated metrics for a given date range.

- **URL:** `/api/explorer/analyses`
- **Method:** `GET`
- **Query Parameters:**
    - `start_date` (string, required): The start of the date range in `YYYY-MM-DD` format.
    - `end_date` (string, required): The end of the date range in `YYYY-MM-DD` format.
    - `page` (integer, optional, default: `1`): The page number to retrieve.
    - `page_size` (integer, optional, default: `50`): The number of records per page.

- **Success Response (200 OK):**

```json
{
  "pagination": {
    "page": 1,
    "page_size": 50,
    "total_items": 1234,
    "total_pages": 25
  },
  "data": [
    {
      "daily_analysis_id": 101,
      "conversation_id": "6173bd56f751bf0740f105c6",
      "customer_name": "Nchirenje",
      "analysis_date": "2025-08-12",
      "csi_score": 85.5,
      "effectiveness_score": 9.2,
      "efficiency_score": 8.8,
      "effort_score": 7.5,
      "empathy_score": 9.1,
      "common_topics": ["token error", "billing issue", "technical support"]
    },
    {
      "daily_analysis_id": 102,
      "conversation_id": "6173bea0d99d10108c3abefb",
      "customer_name": "Leah Olanga",
      "analysis_date": "2025-08-12",
      "csi_score": 42.1,
      "effectiveness_score": 3.1,
      "efficiency_score": 5.2,
      "effort_score": 6.1,
      "empathy_score": 2.9,
      "common_topics": ["power outage", "no lights", "complaint"]
    }
  ]
}
```

### Endpoint 2: Get Daily Conversation Transcript

Fetches the full message transcript for a single daily analysis.

- **URL:** `/api/explorer/transcript/{daily_analysis_id}`
- **Method:** `GET`
- **Path Parameter:**
    - `daily_analysis_id` (integer, required): The unique ID of the daily analysis record.

- **Success Response (200 OK):**

```json
{
  "messages": [
    {
      "timestamp": "2025-08-12T10:00:00Z",
      "direction": "to_company",
      "content": "My new tokens hapo nikifeed in inasema failed"
    },
    {
      "timestamp": "2025-08-12T10:02:15Z",
      "direction": "to_client",
      "content": "Please change the CIU batteries for new ones preferably heavy duty ones."
    },
    {
      "timestamp": "2025-08-12T10:03:00Z",
      "direction": "to_company",
      "content": "The red ones. Let me change now"
    }
  ]
}
```

- **Error Response (404 Not Found):**

```json
{
  "detail": "Analysis with ID {daily_analysis_id} not found."
}
```
