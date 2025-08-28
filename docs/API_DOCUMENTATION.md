is # PowerPulse API Documentation

This document provides a comprehensive overview of the PowerPulse Analytics API endpoints, including request parameters, response schemas, and example usage.

**Base URL:** `http://localhost:8000`

---

## Table of Contents
1.  [Authentication](#authentication)
2.  [Upload](#upload)
3.  [Metrics & Dashboards](#metrics--dashboards)
4.  [Charting](#charting)
5.  [Conversations](#conversations)
6.  [Exporting](#exporting)
7.  [Job Progress](#job-progress)

---

## 1. Authentication
The current version of the API does not require authentication.

---

## 2. Upload

### `POST /api/upload-json`
Accepts a JSON file of conversations, validates it, and starts the analysis process in the background.

- **Status Code:** `202 Accepted`
- **Request Body:** `multipart/form-data`
  - `file` (required): The `.json` file containing the chat data.
  - `force_reprocess` (boolean, optional, default: `false`): If `true`, the system will re-analyze chats that have been processed before.

- **Sample Response (`UploadResponse`):**
  ```json
  {
    "success": true,
    "message": "File upload accepted. Processing has started in the background.",
    "conversations_processed": 0,
    "messages_processed": 0,
    "processing_time_seconds": 0,
    "upload_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef"
  }
  ```

---

## 3. Metrics & Dashboards

### `GET /api/metrics`
Provides all the aggregated KPIs needed to render the main dashboard, calculated from all `DailyAnalysis` records.

- **Query Parameters:**
  - `start_date` (string, optional): Start date for the filter range (format: `YYYY-MM-DD`).
  - `end_date` (string, optional): End date for the filter range (format: `YYYY-MM-DD`).

- **Sample Response (`CSIMetricsResponse`):**
  ```json
  {
    "sentiment": 8.5,
    "csat_percentage": 92.3,
    "fcr_percentage": 75.0,
    "avg_response_time": 5.2,
    "sentiment_distribution": {
      "positive": 0.8,
      "neutral": 0.15,
      "negative": 0.05
    },
    "topic_frequency": [
      { "topic": "Billing Inquiry", "frequency": 42 },
      { "topic": "Power Outage", "frequency": 28 }
    ],
    "csi": 88.5,
    "resolution_quality": 90.1,
    "service_timeliness": 85.4,
    "customer_ease": 82.0,
    "interaction_quality": 91.8,
    "sample_count": 150,
    "deltas": null
  }
  ```

---

## 4. Charting

### `GET /api/charts/sentiment-trend`
Provides time-series data for the sentiment trend chart.

- **Query Parameters:**
  - `start_date` (string, required): Start date for the trend data (format: `YYYY-MM-DD`).
  - `end_date` (string, required): End date for the trend data (format: `YYYY-MM-DD`).

- **Sample Response:**
  ```json
  [
    { "date": "2025-08-01", "sentiment": 8.1 },
    { "date": "2025-08-02", "sentiment": 8.3 }
  ]
  ```

---

## 5. Conversations

### `GET /api/conversations`
Provides a paginated list of conversation summaries, aggregated from their daily analysis data.

- **Query Parameters:**
  - `page` (integer, optional, default: `1`): The page number to retrieve.
  - `page_size` (integer, optional, default: `10`): The number of conversations per page.

- **Sample Response (`ConversationListResponse`):**
  ```json
  {
    "conversations": [
      {
        "chat_id": "fb_chat_id_123",
        "sentiment_score": 9.1,
        "satisfaction_score": 95.5,
        "fcr": true,
        "topics": ["Billing Inquiry", "Payment"],
        "created_at": "2025-08-26T10:00:00Z",
        "agent_username": null,
        "agent_email": null
      }
    ],
    "total": 1,
    "page": 1,
    "page_size": 10,
    "total_pages": 1
  }
  ```

### `GET /api/conversations/{chat_id}`
Provides an aggregated summary for a single conversation.

- **Path Parameter:**
  - `chat_id` (string, required): The Facebook chat ID of the conversation.

- **Sample Response (`ConversationResponse`):**
  ```json
  {
    "chat_id": "fb_chat_id_123",
    "sentiment_score": 9.1,
    "satisfaction_score": 95.5,
    "fcr": true,
    "topics": ["Billing Inquiry", "Payment"],
    "created_at": "2025-08-26T10:00:00Z",
    "agent_username": null,
    "agent_email": null
  }
  ```

### `GET /api/conversations/{chat_id}/daily`
Provides the detailed, day-by-day analysis for a single conversation.

- **Path Parameter:**
  - `chat_id` (string, required): The Facebook chat ID of the conversation.

- **Sample Response (`List[DailyAnalysisResponse]`):**
  ```json
  [
    {
      "analysis_date": "2025-08-26T00:00:00",
      "sentiment_score": 8.5,
      "sentiment_shift": 1.0,
      "resolution_achieved": 9.0,
      "fcr_score": 10.0,
      "ces": 6.5,
      "first_response_time": 120.0,
      "avg_response_time": 180.0,
      "total_handling_time": 15.0,
      "effectiveness_score": 9.5,
      "effort_score": 9.1,
      "efficiency_score": 8.8,
      "empathy_score": 9.0,
      "csi_score": 92.5
    }
  ]
  ```

---

## 6. Exporting

### `GET /api/download`
Downloads conversation or message data in CSV format.

- **Query Parameters:**
  - `export_type` (string, optional, default: `conversations`): The type of data to export. Valid options: `conversations`, `messages`, `all`.

---

## 7. Job Progress

### `GET /api/progress/{upload_id}`
Get real-time progress for a specific upload.

- **Path Parameter:**
  - `upload_id` (string, required): The unique ID returned by the `/api/upload-json` endpoint.

- **Sample Response:**
  ```json
  {
    "upload_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
    "status": "processing",
    "progress_percentage": 50.0,
    "current_stage": "ai_analysis",
    "processed_conversations": 50,
    "total_conversations": 100,
    "details": "Processing 5 analysis jobs...",
    "start_time": "2025-08-27T01:30:00Z",
    "last_update": "2025-08-27T01:30:30Z",
    "duration_seconds": 30.0,
    "statistics": {
      "filtered_autoresponses": 10,
      "gpt_calls_made": 5,
      "errors_count": 0
    },
    "errors": []
  }
  ```
