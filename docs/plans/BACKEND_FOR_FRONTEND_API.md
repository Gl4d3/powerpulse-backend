# Backend for Frontend (BFF) API Contract

This document provides the official API contract that the PowerPulse backend exposes to the frontend. All endpoints and schemas are tailored to meet the specific needs of the UI as defined in the frontend's API contract.

## Base URL
The base URL for all API endpoints is the root of the application (e.g., `http://localhost:8000`).

---

## 1. Main Dashboard Metrics

### `GET /api/metrics`
Provides all the aggregated KPIs needed to render the main dashboard.

- **Query Parameters:**
  - `start_date` (string, optional): Start date for the filter range (format: `YYYY-MM-DD`).
  - `end_date` (string, optional): End date for the filter range (format: `YYYY-MM-DD`).

- **Response Body (`CSIMetricsResponse`):**
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

## 2. Charting Endpoints

### `GET /api/charts/sentiment-trend`
Provides time-series data for the sentiment trend chart.

- **Query Parameters:**
  - `start_date` (string, required): Start date for the trend data (format: `YYYY-MM-DD`).
  - `end_date` (string, required): End date for the trend data (format: `YYYY-MM-DD`).

- **Response Body:**
  ```json
  [
    { "date": "2025-08-01", "sentiment": 8.1 },
    { "date": "2025-08-02", "sentiment": 8.3 },
    { "date": "2025-08-03", "sentiment": 8.2 }
  ]
  ```

### `GET /api/charts/csi-trend`
Provides time-series data for the main CSI and pillar score trend chart.

- **Query Parameters:**
  - `start_date` (string, required): Start date for the trend data (format: `YYYY-MM-DD`).
  - `end_date` (string, required): End date for the trend data (format: `YYYY-MM-DD`).

- **Response Body:**
  ```json
  [
    {
      "date": "2025-08-01",
      "csi_score": 88.5,
      "effectiveness_score": 9.1,
      "effort_score": 8.5,
      "efficiency_score": 8.9,
      "empathy_score": 9.0
    },
    {
      "date": "2025-08-02",
      "csi_score": 89.1,
      "effectiveness_score": 9.2,
      "effort_score": 8.6,
      "efficiency_score": 9.0,
      "empathy_score": 9.1
    }
  ]
  ```

---

## 3. Conversation Endpoints

### `GET /api/conversations`
Provides a paginated list of conversation summaries.

- **Query Parameters:**
  - `page` (integer, optional, default: `1`): The page number to retrieve.
  - `page_size` (integer, optional, default: `10`): The number of conversations per page.

- **Response Body (`ConversationListResponse`):**
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

- **Response Body (`ConversationResponse`):**
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
Provides the detailed, day-by-day analysis for a single conversation. This can be used to power more detailed views in the UI.

- **Path Parameter:**
  - `chat_id` (string, required): The Facebook chat ID of the conversation.

- **Response Body (`List[DailyAnalysisResponse]`):**
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

## 4. Utility Endpoints

### `POST /api/upload-json`
Uploads a JSON file of chat conversations for processing.

- **Request Body:** `multipart/form-data`
  - `file`: The `.json` file to upload.
  - `force_reprocess` (boolean, optional): Set to `true` to re-process chats that have been seen before.

### `GET /api/download`
Downloads conversation data in CSV format.

- **Query Parameters:**
  - `export_type` (string, optional, default: `conversations`): The type of data to export.

---

## 5. Job Progress

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
