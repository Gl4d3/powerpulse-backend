# PowerPulse Database Schema

This document provides a detailed overview of the tables in the PowerPulse application database, explaining the purpose of each table and how they interact in the data processing lifecycle.

---

## 1. High-Level Overview & Data Flow

The database is designed to support a robust, asynchronous data processing pipeline. Here is a summary of each table's role and how data flows through the system from file upload to final analysis.

### Table Explanations

#### `Conversation`
-   **Purpose:** This is the top-level container. Each row represents a single, unique customer conversation and primarily stores high-level metadata.
-   **Data Flow:** A `Conversation` record is created at the beginning of the file processing to act as a parent for all related messages and daily analyses.

#### `Message`
-   **Purpose:** This table is the **raw source of truth**. It stores the content of every single individual message from the uploaded chat logs.
-   **Data Flow:** Data is inserted into this table only once, during the initial file processing. Each message is linked back to its parent `Conversation`. This table is read by the AI analysis jobs but is not modified by them.

#### `DailyAnalysis`
-   **Purpose:** This is the **core analytics table**. It stores the full breakdown of all eight micro-metrics, four pillar scores, and the final CSI score for a *single day* within a conversation.
-   **Data Flow:** After messages are ingested, the system creates an empty `DailyAnalysis` record for each day of activity in a conversation. These empty records are then picked up by background jobs, which fill in the metric scores after getting the results from the AI.

#### `Job`
-   **Purpose:** This table is the **engine of the background processing system**. Each row represents a single, manageable "chunk" of work (a batch of `DailyAnalysis` records) that needs to be sent to the AI.
-   **Why it's important:** This makes the system robust and scalable. If one small batch fails, it doesn't crash the entire upload. It also allows for concurrency control to avoid rate-limiting.
-   **Data Flow:** After `DailyAnalysis` records are created, they are grouped into batches, and a `Job` record is created for each batch with a `pending` status. Background workers pick up these jobs, update their status to `in_progress`, and finally to `completed` or `failed`.

#### `ProcessedChat`
-   **Purpose:** This table acts as the system's **memory**, preventing it from doing the same work twice. It keeps a simple list of every `fb_chat_id` that has been successfully processed.
-   **Data Flow:** At the very beginning of an upload, this table is checked. If a conversation ID is found, that conversation is skipped. At the very end of a successful upload, the new conversation IDs are added to this table.

#### `Metric`
-   **Purpose:** This table is a **performance-enhancing cache**. It stores the final, pre-calculated KPIs (e.g., system-wide average CSI) that are displayed on the main dashboard.
-   **Data Flow:** This table is only written to at the very end of a successful upload. The `analytics_service` runs one final aggregation query over the entire `DailyAnalysis` table and saves the results here as simple key-value pairs. The main `GET /api/metrics` endpoint reads from this table to ensure a fast response.

---

## 2. Table Schemas

### `Conversation`
Stores high-level metadata for a single, unique customer conversation.

| Column Name | Data Type | Description |
| :--- | :--- | :--- |
| `id` | INTEGER | Primary Key |
| `fb_chat_id` | VARCHAR | The unique Facebook chat ID for the conversation. |
| `total_messages` | INTEGER | The total number of messages in the conversation. |
| `customer_messages` | INTEGER | The count of messages sent by the customer. |
| `agent_messages` | INTEGER | The count of messages sent by the agent. |
| `first_message_time` | DATETIME | Timestamp of the very first message in the conversation. |
| `last_message_time` | DATETIME | Timestamp of the most recent message in the conversation. |
| `common_topics` | JSON | A list of the most common topics identified in the conversation. |
| `created_at` | DATETIME | Timestamp when the record was created. |
| `updated_at` | DATETIME | Timestamp when the record was last updated. |

---

### `DailyAnalysis`
The core analytics table. Stores the full CSI breakdown for a single day within a conversation.

| Column Name | Data Type | Description |
| :--- | :--- | :--- |
| `id` | INTEGER | Primary Key |
| `conversation_id` | INTEGER | Foreign Key to the `Conversation` table. |
| `analysis_date` | DATETIME | The specific day for which this analysis was performed. |
| `sentiment_score` | FLOAT | (Micro-Metric) The overall sentiment score for the day (0-10). |
| `sentiment_shift` | FLOAT | (Micro-Metric) The change in sentiment during the day (-5 to +5). |
| `resolution_achieved` | FLOAT | (Micro-Metric) Score indicating if the issue was resolved (0-10). |
| `fcr_score` | FLOAT | (Micro-Metric) Score for First Contact Resolution (0-10). |
| `ces` | FLOAT | (Micro-Metric) Customer Effort Score (1-7, lower is better). |
| `first_response_time` | FLOAT | (Micro-Metric) First response time in seconds. |
| `avg_response_time` | FLOAT | (Micro-Metric) Average response time in seconds. |
| `total_handling_time` | FLOAT | (Micro-Metric) Total agent handling time in minutes. |
| `effectiveness_score` | FLOAT | (Pillar Score) Calculated from `resolution_achieved` and `fcr_score`. |
| `effort_score` | FLOAT | (Pillar Score) Calculated from the inverted `ces`. |
| `efficiency_score` | FLOAT | (Pillar Score) Calculated from the scaled time metrics. |
| `empathy_score` | FLOAT | (Pillar Score) Calculated from `sentiment_score` and `sentiment_shift`. |
| `csi_score` | FLOAT | The final, weighted CSI score for the day. |

---

### `Message`
Stores the content of every individual message within a conversation.

| Column Name | Data Type | Description |
| :--- | :--- | :--- |
| `id` | INTEGER | Primary Key |
| `fb_chat_id` | VARCHAR | The Facebook chat ID the message belongs to. |
| `conversation_id` | INTEGER | Foreign Key to the `Conversation` table. |
| `message_content` | TEXT | The actual text content of the message. |
| `direction` | VARCHAR | `to_company` or `to_client`. |
| `social_create_time` | DATETIME | The original timestamp from the social media platform. |
| `agent_info` | JSON | Information about the agent who sent the message. |

---

### `Job`
Represents a background job for processing a batch of `DailyAnalysis` records.

| Column Name | Data Type | Description |
| :--- | :--- | :--- |
| `id` | INTEGER | Primary Key |
| `upload_id` | VARCHAR | The unique ID of the file upload this job belongs to. |
| `status` | VARCHAR | The current status of the job (e.g., `pending`, `in_progress`, `completed`, `failed`). |
| `created_at` | DATETIME | Timestamp when the job was created. |
| `completed_at` | DATETIME | Timestamp when the job finished. |
| `result` | JSON | Stores the results of the job, including any errors and tracebacks. |

---

### `Metric`
A simple key-value table for caching system-wide aggregated metrics for the main dashboard.

| Column Name | Data Type | Description |
| :--- | :--- | :--- |
| `id` | INTEGER | Primary Key |
| `metric_name` | VARCHAR | The unique name of the metric (e.g., `overall_csi_score`). |
| `metric_value` | FLOAT | The calculated value of the metric. |
| `metric_metadata` | JSON | Any additional context for the metric. |
| `calculated_at` | DATETIME | Timestamp when the metric was last calculated. |

---

### `ProcessedChat`
A tracking table to prevent the reprocessing of conversations that have already been analyzed.

| Column Name | Data Type | Description |
| :--- | :--- | :--- |
| `id` | INTEGER | Primary Key |
| `fb_chat_id` | VARCHAR | The unique Facebook chat ID that has been processed. |
| `processed_at` | DATETIME | Timestamp when the chat was last processed. |
| `message_count` | INTEGER | The number of messages that were in the chat when it was processed. |

---

### Association Tables

#### `job_daily_analyses`
A many-to-many link table that connects a `Job` to the `DailyAnalysis` records it is responsible for processing.

| Column Name | Data Type | Description |
| :--- | :--- | :--- |
| `job_id` | INTEGER | Foreign Key to the `Job` table. |
| `daily_analysis_id` | INTEGER | Foreign Key to the `DailyAnalysis` table. |
