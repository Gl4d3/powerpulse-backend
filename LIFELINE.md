# PowerPulse Application Lifeline

**Version:** 2.0
**Author:** Gemini
**Last Updated:** 2025-09-15

## 1. High-Level Data Flow

This document provides a deep, technical dive into the entire data processing pipeline of the PowerPulse application, from the moment a file is uploaded to the final database commit.

```mermaid
flowchart TD
    subgraph "API Process (main.py)"
        A[HTTP POST /api/upload-json] --> B(routes/upload.py);
        B --> C{services/file_service_optimized.py};
        C --> D(1. Parse & Group Data);
        D --> E(2. Create DailyAnalysis Objects);
        E --> F(services/batch_service.py);
        F --> G(3. Create Token-based Batches);
        G --> H{services/job_service.py\n`create_jobs_for_upload`};
        H --> I(4. Create Jobs in DB with 'pending' status);
        I --> J[Return upload_id to client];
    end

    subgraph "Worker Process (worker.py)"
        K[Main Loop: Poll Database every 5s] --> L{services/job_service.py\n`fetch_next_job`};
        L --> M{Found a Job?};
        M -- Yes --> N(Execute Job);
        M -- No --> K;
    end

    subgraph "Job Execution (services/job_service.py)"
        N --> O{services/gemini_service.py};
        O --> P(5. AI Analysis via Gemini API);
        P --> Q{services/time_metric_service.py};
        Q --> R(6. Calculate Time Metrics);
        R --> S{services/analytics_service.py};
        S --> T(7. Calculate CSI Score);
        T --> U(8. Update DB & Mark Job 'completed'/'failed');
        U --> K;
    end

    I -.-> K;
```

---

## 2. Step-by-Step Breakdown

### Step 1: File Ingestion and Parsing

1. **Route (`routes/upload.py`):** An HTTP POST request hits the `/api/upload-json` endpoint.
2. **Synchronous Processing:** The route directly calls `file_service_optimized.optimized_file_service.process_grouped_chats_json()` synchronously and returns an `upload_id` immediately after job creation (not background task execution).
3. **Format Sniffing:** The `_parse_and_normalize_input` function reads the raw file content. It intelligently detects the JSON structure (e.g., a raw array, a pre-grouped dictionary, or the single-key object from a database export) and transforms it into a standardized Python dictionary where keys are `chat_id`s and values are lists of message objects.

### Step 2: New Analysis Identification & Batching

1. **Isolate Daily Work:** The file service iterates through the normalized data and creates a dictionary of all possible `(chat_id, date)` pairs.
2. **Database Check:** It then performs a single, efficient database query to fetch all `(conversation.fb_chat_id, daily_analysis.analysis_date)` pairs that already exist in the database.
3. **Filtering:** By comparing the two sets, the service creates a final list of `DailyAnalysis` objects that are confirmed to be new and require processing.
4. **Object Creation:** The service creates `Conversation`, `Message`, and `DailyAnalysis` SQLAlchemy objects in memory for the new data.
5. **Batching (`services/batch_service.py`):** The list of new `DailyAnalysis` objects is passed to the `create_daily_analysis_batches` function. This function groups analyses into batches that do not exceed a `MAX_TOKENS_PER_BATCH` limit, ensuring all days for a single conversation stay in the same batch.

### Step 3: Job Creation and Worker Processing

1. **Job Creation (`services/job_service.py`):** For each batch of `DailyAnalysis` objects, a `Job` record is created in the database with a `pending` status.
2. **Worker Process (`worker.py`):** A separate worker process continuously polls the database every 5 seconds using `job_service.fetch_next_job()` to find pending jobs.
3. **Sequential Execution:** When a job is found, the worker executes it via `job_service.execute_job()` in a new database session, then continues polling for the next job.

### Step 4: AI Analysis (Inside a Job)

1. **Data Fetching:** Each running job fetches its batch of `DailyAnalysis` objects, including the full message text for each day.
2. **Prompt Creation (`services/gemini_service.py`):** The `_create_daily_analysis_batch_prompt` function constructs a single, large prompt containing the message data for all analyses in the batch.
3. **API Call:** The `_call_gemini_with_retry` function sends the prompt to the Google Gemini API. It includes logic for exponential backoff and retries upon failure.
4. **Response Parsing:** The gemini service robustly parses the JSON response from the AI, handling potential formatting errors and extracting metrics for each daily analysis.

### Step 5 & 6: Metric Calculation & CSI Aggregation

1. **Time Metrics (`services/time_metric_service.py`):** For each successfully analyzed item from the AI, the `job_service` calls `calculate_time_metrics_for_daily_analysis` to accurately calculate `first_response_time`, `avg_response_time`, and `total_handling_time` from the message timestamps.
2. **CSI Calculation (`services/analytics_service.py`):** The `job_service` then calls `calculate_and_set_daily_csi_score`. This function takes the AI-generated qualitative metrics and the script-calculated quantitative metrics and computes the four pillar scores (Effectiveness, Effort, Efficiency, Empathy), and finally, the overall weighted CSI score.

### Step 7: Database Persistence

1. **Update Records:** The `job_service` updates the `DailyAnalysis` records in the database with all the newly calculated metrics and scores.
2. **Final Commit:** The job marks itself as `completed` or `failed` and commits the changes to the database, concluding its lifecycle.
3. **Worker Continuation:** The worker process returns to polling for the next pending job, maintaining continuous processing until all jobs are complete.

---

## 3. Database Schema (ERD)

This diagram illustrates the relationships between the core tables in the `powerpulse.db` database.

```mermaid
erDiagram
    CONVERSATIONS {
        int id PK
        string fb_chat_id UK "Unique Facebook chat identifier"
        string customer_name "Customer's display name"
        int total_messages "Total message count"
        int customer_messages "Messages from customer"
        int agent_messages "Messages from agents"
        datetime first_message_time "Timestamp of first message"
        datetime last_message_time "Timestamp of last message"
        datetime created_at "Record creation time"
        datetime updated_at "Last update time"
    }

    DAILY_ANALYSES {
        int id PK
        int conversation_id FK
        datetime analysis_date "Date of this analysis"
        float sentiment_score "AI-generated sentiment (1-10)"
        float sentiment_shift "Change in sentiment"
        float resolution_achieved "Resolution score"
        float fcr_score "First Call Resolution score"
        float ces "Customer Effort Score"
        json common_topics "Array of topics discussed"
        float first_response_time "Seconds to first response"
        float avg_response_time "Average response time"
        float total_handling_time "Total handling time in minutes"
        float effectiveness_score "Pillar: Effectiveness (0-10)"
        float effort_score "Pillar: Effort (0-10)"
        float efficiency_score "Pillar: Efficiency (0-10)"
        float empathy_score "Pillar: Empathy (0-10)"
        float csi_score "Final CSI score (0-10)"
    }

    MESSAGES {
        int id PK
        string fb_chat_id "Facebook chat identifier"
        int conversation_id FK
        text message_content "Full message text"
        string direction "to_company or to_client"
        datetime social_create_time "Original message timestamp"
        json agent_info "Agent name and email (if applicable)"
        float sentiment_score "Message-level sentiment (1-10)"
        float sentiment_confidence "AI confidence (0-1)"
        json topics "Topics extracted from message"
        boolean is_first_contact "First message indicator"
        float response_time_minutes "Time to respond"
        datetime created_at "Record creation time"
        datetime updated_at "Last update time"
    }

    JOBS {
        int id PK
        string upload_id "Associated upload identifier"
        string task_name "Job type identifier"
        string status "pending, running, completed, failed, retryable_failure"
        datetime run_at "Scheduled execution time"
        int retry_count "Number of retry attempts"
        int max_retries "Maximum retry limit"
        datetime created_at "Job creation time"
        datetime started_at "Job start time"
        datetime completed_at "Job completion time"
        text last_error "Error message if failed"
        json result "Job execution results"
    }

    JOB_METRICS {
        int id PK
        int job_id FK
        int token_usage "AI API tokens consumed"
        float processing_time_seconds "Job execution duration"
        int api_calls_made "Number of API calls"
    }

    JOB_DAILY_ANALYSES {
        int job_id FK
        int daily_analysis_id FK
    }

    METRICS {
        int id PK
        string metric_name UK "Cached metric identifier"
        float metric_value "Computed metric value"
        json metric_metadata "Additional context data"
        datetime calculated_at "When metric was computed"
        datetime updated_at "Last update time"
    }

    CONVERSATIONS ||--o{ DAILY_ANALYSES : "has daily analyses"
    CONVERSATIONS ||--o{ MESSAGES : "contains messages"
    JOBS ||--o| JOB_METRICS : "has performance metrics"
    JOBS ||--o{ JOB_DAILY_ANALYSES : "processes batches"
    DAILY_ANALYSES ||--o{ JOB_DAILY_ANALYSES : "analyzed by jobs"
```
