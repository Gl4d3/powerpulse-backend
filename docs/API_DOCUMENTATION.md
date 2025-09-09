# PowerPulse API Documentation

This document provides a comprehensive overview of the PowerPulse Analytics API endpoints, including request parameters, response schemas, and example usage.

**Base URL:** `http://localhost:8000`

---

## Table of Contents

1. [Authentication](#authentication)
2. [API Testing](#api-testing)
3. [Upload](#upload)
4. [Metrics & Dashboards](#metrics--dashboards)
5. [Charting](#charting)
6. [Conversations](#conversations)
7. [Exporting](#exporting)
8. [Job Progress](#job-progress)
9. [Conversation Explorer](#conversation-explorer)

---

## 1. Authentication

The current version of the API does not require authentication.

---

## 2. API Testing

### `GET /api/test-api-key`

Test the currently configured AI service API key (Gemini or OpenAI based on settings).

- **Sample Response (`APIKeyTestResponse`):**

  ```json
  {
    "service": "gemini",
    "api_key_valid": true,
    "message": "API key is valid and working",
    "model_used": "gemini-1.5-flash",
    "test_response": "Hello! I'm working correctly.",
    "error_details": null
  }
  ```

### `GET /api/test-gemini`

Test the Gemini API key specifically.

- **Sample Response (`APIKeyTestResponse`):**

  ```json
  {
    "service": "gemini",
    "api_key_valid": true,
    "message": "Gemini API key is valid",
    "model_used": "gemini-1.5-flash",
    "test_response": "Hello from Gemini!",
    "error_details": null
  }
  ```

### `GET /api/test-openai`

Test the OpenAI API key specifically.

- **Sample Response (`APIKeyTestResponse`):**

  ```json
  {
    "service": "openai",
    "api_key_valid": true,
    "message": "OpenAI API key is valid",
    "model_used": "gpt-4o-mini",
    "test_response": "Hello from OpenAI!",
    "error_details": null
  }
  ```

---

## 3. Upload

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

### `GET /api/upload-status`

Get the status of all recent uploads.

- **Sample Response:**

  ```json
  {
    "uploads": [
      {
        "upload_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
        "status": "completed",
        "created_at": "2025-09-02T10:00:00Z"
      }
    ]
  }
  ```

---

## 4. Metrics & Dashboards

### `GET /api/metrics`

Provides all the aggregated KPIs needed to render the main dashboard, calculated from all `DailyAnalysis` records with completed CSI analysis.

- **Query Parameters:**
  - `start_date` (string, optional): Start date for the filter range (format: `YYYY-MM-DD`).
  - `end_date` (string, optional): End date for the filter range (format: `YYYY-MM-DD`).

- **Response Schema:**
  - `csi` (float): Overall Customer Satisfaction Index (0-100 scale)
  - `resolution_quality` (float): Effectiveness pillar score (0-100 scale)
  - `service_timeliness` (float): Efficiency pillar score (0-100 scale)
  - `customer_ease` (float): Effort pillar score (0-100 scale)
  - `interaction_quality` (float): Empathy pillar score (0-100 scale)
  - `sentiment_score` (float): Average sentiment score across all daily analyses
  - `sentiment_shift` (float): Average sentiment shift across conversations
  - `resolution_achieved` (float): Average resolution achieved score
  - `fcr_score` (float): Average first call resolution score
  - `ces` (float): Average customer effort score
  - `first_response_time` (float): Average first response time in seconds
  - `avg_response_time` (float): Average response time in seconds
  - `total_handling_time` (float): Average total handling time in minutes
  - `sample_count` (integer): Number of unique conversations with CSI analysis
  - `deltas` (object, nullable): Period-over-period changes (future feature)
  - `pillar_weights` (object): Weights used in CSI calculation

- **Sample Response (`CSIMetricsResponse`):**

  ```json
  {
    "csi": 36.14,
    "resolution_quality": 18.10,
    "service_timeliness": 38.47,
    "customer_ease": 52.80,
    "interaction_quality": 46.58,
    "sentiment_score": 4.34,
    "sentiment_shift": -0.023,
    "resolution_achieved": 1.94,
    "fcr_score": 1.68,
    "ces": 3.83,
    "first_response_time": 6528.99,
    "avg_response_time": 6787.88,
    "total_handling_time": 201.72,
    "sample_count": 2950,
    "deltas": null,
    "pillar_weights": {
      "effectiveness": 0.35,
      "effort": 0.25,
      "efficiency": 0.25,
      "empathy": 0.15
    }
  }
  ```

### `POST /api/metrics/recalculate`

Force recalculation of all cached metrics from the database.

- **Sample Response (`CSIMetricsResponse`):**

  ```json
  {
    "csi": 36.14,
    "resolution_quality": 18.10,
    "service_timeliness": 38.47,
    "customer_ease": 52.80,
    "interaction_quality": 46.58,
    "sentiment_score": 4.34,
    "sentiment_shift": -0.023,
    "resolution_achieved": 1.94,
    "fcr_score": 1.68,
    "ces": 3.83,
    "first_response_time": 6528.99,
    "avg_response_time": 6787.88,
    "total_handling_time": 201.72,
    "sample_count": 2950,
    "deltas": null,
    "pillar_weights": {
      "effectiveness": 0.35,
      "effort": 0.25,
      "efficiency": 0.25,
      "empathy": 0.15
    }
  }
  ```

### `GET /api/metrics/daily`

Get historical daily metrics for trend analysis.

- **Query Parameters:**
  - `start_date` (string, required): Start date for the range (format: `YYYY-MM-DD`).
  - `end_date` (string, required): End date for the range (format: `YYYY-MM-DD`).

- **Sample Response (`HistoricalMetricsResponse`):**

  ```json
  {
    "metrics": [
      {
        "date": "2025-08-01",
        "csi": 85.5,
        "sentiment": 8.2,
        "fcr_percentage": 75.0,
        "sample_count": 45
      }
    ]
  }
  ```

---

## 5. Charting

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

### `GET /api/charts/csi-trend`

Provides time-series data for the CSI trend chart.

- **Query Parameters:**
  - `start_date` (string, required): Start date for the trend data (format: `YYYY-MM-DD`).
  - `end_date` (string, required): End date for the trend data (format: `YYYY-MM-DD`).

- **Sample Response:**

  ```json
  [
    { "date": "2025-08-01", "csi": 85.1 },
    { "date": "2025-08-02", "csi": 87.3 }
  ]
  ```

### `GET /api/charts/sentiment-distribution`

Provides sentiment distribution data (positive, neutral, negative) for chart visualization.

- **Query Parameters:**
  - `start_date` (string, optional): Start date for the filter range (format: `YYYY-MM-DD`).
  - `end_date` (string, optional): End date for the filter range (format: `YYYY-MM-DD`).

- **Response Schema:**
  - `positive` (float): Proportion of positive sentiment scores (>=7)
  - `neutral` (float): Proportion of neutral sentiment scores (4-7)
  - `negative` (float): Proportion of negative sentiment scores (<=4)

- **Sample Response:**

  ```json
  {
    "positive": 0.137,
    "neutral": 0.255,
    "negative": 0.609
  }
  ```

### `GET /api/charts/topic-frequency`

Provides the top topics by frequency for chart visualization, limited to prevent overwhelming the frontend.

- **Query Parameters:**
  - `start_date` (string, optional): Start date for the filter range (format: `YYYY-MM-DD`).
  - `end_date` (string, optional): End date for the filter range (format: `YYYY-MM-DD`).
  - `limit` (integer, optional, default: 30): Maximum number of topics to return.

- **Sample Response:**

  ```json
  [
    { "topic": "power outage", "frequency": 1104 },
    { "topic": "meter number", "frequency": 655 },
    { "topic": "Power outage", "frequency": 404 },
    { "topic": "account number", "frequency": 384 },
    { "topic": "location details", "frequency": 288 }
  ]
  ```

---

## 6. Conversations & Explorer: Understanding the Difference

**IMPORTANT NOTE FOR FRONTEND:** The API provides two distinct sets of endpoints for accessing conversation data. Please read the following descriptions carefully.

- **`/api/explorer/*` (Use This For Detailed Views):** These are the primary endpoints for accessing the raw results of the new, daily-granularity analysis. Use `GET /api/explorer/analyses` to populate tables where each row represents a single day of analysis for a conversation. Use `GET /api/explorer/transcript/{daily_analysis_id}` to drill down into a specific day's messages. These endpoints are stable and provide the most accurate, up-to-date data.

- **`/api/conversations/*` (Use This For Aggregated Summaries):** These endpoints provide a high-level, aggregated summary for an entire conversation across all of its active days. For example, the `avg_csi_score` is the average of all daily CSI scores for that conversation. Use these endpoints when you need a single, summarized record for a conversation, not a day-by-day breakdown.

### `GET /api/conversations`

Provides a paginated list of conversation summaries, aggregated from their daily analysis data.

- **Query Parameters:**
  - `page` (integer, optional, default: `1`): The page number to retrieve.
  - `page_size` (integer, optional, default: `10`): The number of conversations per page.

- **Response Schema (`ConversationResponse`):**
  - `chat_id` (string): The Facebook chat identifier.
  - `username` (string, nullable): Customer's name.
  - `avg_csi_score` (float, nullable): Average CSI score across all analyzed days (0-10 scale).
  - `avg_effectiveness_score` (float, nullable): Average Effectiveness pillar score across all analyzed days (0-10 scale).
  - `avg_efficiency_score` (float, nullable): Average Efficiency pillar score across all analyzed days (0-10 scale).
  - `avg_effort_score` (float, nullable): Average Effort pillar score across all analyzed days (0-10 scale).
  - `avg_empathy_score` (float, nullable): Average Empathy pillar score across all analyzed days (0-10 scale).
  - `topics` (array of strings): All unique topics discussed in the conversation.
  - `agents` (array of objects): All unique agents who interacted with the customer.
  - `created_at` (datetime, nullable): Timestamp when the conversation record was first created.
  - `total_messages` (integer, nullable): Total number of messages in the conversation.
  - `customer_messages` (integer, nullable): Number of messages from the customer.
  - `agent_messages` (integer, nullable): Number of messages from agents.
  - `first_message_time` (datetime, nullable): Timestamp of the very first message.
  - `last_message_time` (datetime, nullable): Timestamp of the very last message.

- **Sample Response (`ConversationListResponse`):**

  ```json
  {
    "conversations": [
      {
        "chat_id": "6174faccde2cc1d76cb26ccd",
        "username": "Gifted Gracious Shimz",
        "avg_csi_score": 3.28,
        "avg_effectiveness_score": 8.2,
        "avg_efficiency_score": 7.5,
        "avg_effort_score": 8.8,
        "avg_empathy_score": 6.9,
        "topics": ["power outage", "repeated issues", "restoration"],
        "agents": [
          {
            "username": "Collins",
            "email": "CollinsKimutaiBett@kplc.co.ke"
          }
        ],
        "created_at": "2025-08-26T10:00:00Z",
        "total_messages": 13,
        "customer_messages": 10,
        "agent_messages": 3,
        "first_message_time": "2025-08-26T10:00:00Z",
        "last_message_time": "2025-08-26T15:30:00Z"
      }
    ],
    "total": 2950,
    "page": 1,
    "page_size": 1,
    "total_pages": 2950
  }
  ```

### `GET /api/conversations/{chat_id}`

Provides a comprehensive aggregated summary for a single conversation.

- **Path Parameter:**
  - `chat_id` (string, required): The Facebook chat ID of the conversation.

- **Response Schema:** Same as the `ConversationResponse` object above.

### `GET /api/conversations/{chat_id}/messages`

## 7. Exporting

### `GET /api/download`

Downloads conversation or message data in CSV format.

- **Query Parameters:**
  - `export_type` (string, optional, default: `conversations`): The type of data to export. Valid options: `conversations`, `messages`, `all`.

### `GET /api/download/metrics`

Downloads aggregated metrics data in CSV format.

- **Query Parameters:**
  - `start_date` (string, optional): Start date for the export range (format: `YYYY-MM-DD`).
  - `end_date` (string, optional): End date for the export range (format: `YYYY-MM-DD`).

---

## 8. Job Progress

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

### `GET /api/progress`

Get progress for all recent uploads.

- **Sample Response:**

  ```json
  {
    "uploads": [
      {
        "upload_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
        "status": "completed",
        "progress_percentage": 100.0,
        "last_update": "2025-08-27T01:35:00Z"
      }
    ]
  }
  ```

### `DELETE /api/progress/{upload_id}`

Delete progress tracking for a specific upload.

- **Path Parameter:**
  - `upload_id` (string, required): The unique ID of the upload to delete.

- **Sample Response:**

  ```json
  {
    "message": "Progress tracking deleted successfully",
    "upload_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef"
  }
  ```

---

## 9. Conversation Explorer

### `GET /api/explorer/analyses`

Fetches a paginated list of daily analyses with their associated metrics for a given date range.

Example curl request:

```bash
curl -X GET "http://localhost:8000/api/explorer/analyses?start_date=2025-08-01&end_date=2025-08-31&page=1&page_size=50"
```

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
      }
    ]
  }
  ```

### `GET /api/explorer/transcript/{daily_analysis_id}`

Fetches the full message transcript for a single daily analysis.

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
      }
    ]
  }
  ```

---

## 10. Jobs

Endpoints for monitoring and managing the background analysis jobs.

### `GET /api/jobs/`

List all analysis jobs with pagination and status filtering.

- **Query Parameters:**
  - `status` (string, optional): Filter jobs by status (e.g., `pending`, `running`, `completed`, `failed`, `retryable_failure`).
  - `page` (integer, optional, default: 1): Page number.
  - `page_size` (integer, optional, default: 20): Number of jobs per page.

- **Sample Response (`PaginatedJobResponse`):**

  ```json
  {
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total_items": 150,
      "total_pages": 8
    },
    "data": [
      {
        "id": 101,
        "upload_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
        "task_name": "default_csi_analysis",
        "status": "completed",
        "run_at": "2025-09-06T14:00:00Z",
        "retry_count": 0,
        "max_retries": 3,
        "created_at": "2025-09-06T13:59:00Z",
        "started_at": "2025-09-06T14:00:00Z",
        "completed_at": "2025-09-06T14:01:30Z",
        "last_error": null
      }
    ]
  }
  ```

### `GET /api/jobs/{job_id}`

Retrieve the detailed status of a single job.

- **Path Parameter:**
  - `job_id` (integer, required): The ID of the job.

- **Sample Response (`JobDetailsResponse`):**

  ```json
  {
    "id": 102,
    "upload_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
    "task_name": "default_csi_analysis",
    "status": "failed",
    "run_at": "2025-09-06T14:05:00Z",
    "retry_count": 3,
    "max_retries": 3,
    "created_at": "2025-09-06T14:02:00Z",
    "started_at": "2025-09-06T14:05:00Z",
    "completed_at": "2025-09-06T14:05:10Z",
    "last_error": "Max retries exceeded. PermanentApiError: Gemini API client error (HTTP 400): Invalid request",
    "result": {
      "error": "PermanentApiError: Gemini API client error (HTTP 400): Invalid request",
      "traceback": "..."
    }
  }
  ```

### `POST /api/jobs/{job_id}/retry`

Manually retry a job that has the status 'failed'. This resets the status to 'pending' and clears the error information.

- **Path Parameter:**
  - `job_id` (integer, required): The ID of the failed job to retry.

- **Sample Response (`JobRetryResponse`):**

  ```json
  {
    "job_id": 102,
    "new_status": "pending",
    "message": "Job 102 has been successfully queued for a retry."
  }
  ```-567890abcdef"
  }
  ```

### `GET /api/upload-status`

Get the status of all recent uploads.

- **Sample Response:**

  ```json
  {
    "uploads": [
      {
        "upload_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
        "status": "completed",
        "created_at": "2025-09-02T10:00:00Z"
      }
    ]
  }
  ```


---

## Error Responses

All endpoints may return error responses in the following format:

```json
{
  "detail": "Error message describing what went wrong",
  "status_code": 400
}
```

Common HTTP status codes:
- `200 OK` - Successful request
- `202 Accepted` - Request accepted (for async operations)
- `400 Bad Request` - Invalid request parameters
- `404 Not Found` - Resource not found
- `422 Unprocessable Entity` - Validation error
- `500 Internal Server Error` - Server error

---

## Notes

- All date parameters should be in `YYYY-MM-DD` format
- All timestamps in responses are in ISO 8601 format with UTC timezone
- Pagination parameters `page` and `page_size` are available on list endpoints
- The API supports CORS for frontend integration
- File uploads are limited to 50MB
- Rate limiting may apply to prevent abuse
- **Conversation endpoints only return conversations with completed CSI analysis** (approximately 2,950 out of 4,293 total conversations)
- CSI scores are calculated from daily analysis data and may not be available for all conversations
- Topic frequency data is aggregated from all analyzed conversations with CSI data

**Date Field Clarification:**
- `created_at`: Date the conversation record was created (usually the time of the first message)
- `first_message_time`: Timestamp of the first message in the conversation
- `last_message_time`: Timestamp of the last message in the conversation
- `analysis_date` (in daily_analyses): Date the batch analysis was run for metrics aggregation
- `social_create_time` (in messages): Actual time each message was sent
