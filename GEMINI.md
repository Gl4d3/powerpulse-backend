# PowerPulse Analytics Gemini Context (v5.0 - Conversation Explorer)

This document provides a comprehensive and technically accurate overview of the PowerPulse Analytics backend. It details the final architecture after a significant refactoring to a daily-granularity, token-based batching model and the addition of a new Conversation Explorer API.

---
**IMPORTANT NOTE:** For detailed, human-readable API documentation, including sample requests and responses, refer to the official **[`docs/API_DOCUMENTATION.md`](./docs/API_DOCUMENTATION.md)**. This file is the canonical source for API contracts.
---

## 1. High-Level Architecture & Data Flow

The backend is a FastAPI application that processes customer service chat logs and serves a frontend with both aggregated and granular, record-level data.

1.  **Upload:** A user uploads a JSON file via `POST /api/upload-json`. The system no longer uses a `force_reprocess` flag; instead, it automatically detects and processes only new, unanalyzed conversation-days.

2.  **Daily Grouping & Persistence:** The backend parses conversations and groups messages by date. For each day a conversation has activity, a `DailyAnalysis` record is created in the database if one does not already exist for that specific conversation and date.

3.  **Token-Based Batching & AI Analysis:** The new `DailyAnalysis` records are batched based on a configurable token limit (`MAX_TOKENS_PER_BATCH`), ensuring all days for a single conversation are grouped together. A background job queue processes these batches, sending them to a Google Gemini model to extract nine **micro-metrics** (`sentiment_score`, `sentiment_shift`, `resolution_achieved`, `fcr_score`, `ces`, `common_topics`, and three time-based metrics).

4.  **Pillar & CSI Calculation:** For each `DailyAnalysis` record, four **macro-metric pillars** (Effectiveness, Effort, Efficiency, Empathy) are calculated from the micro-metrics. A final, weighted **CSI score** is then calculated from these pillars. All results are stored in the `DailyAnalysis` table.

5.  **API Access (Dual-Mode):** The API now serves two distinct purposes:
    - **Aggregated Dashboards:** The `GET /api/metrics` and `GET /api/charts/*` endpoints provide system-wide, pre-aggregated data for the main UI dashboards.
    - **Conversation Explorer:** The new `GET /api/explorer/*` endpoints provide direct, paginated access to individual `DailyAnalysis` records and their corresponding message transcripts, allowing for detailed inspection and drill-down.

---

## 2. Technical Deep Dive

### 2.1. Database (`models.py`)

-   **`Conversation` Model:** Stores high-level metadata about a conversation (`fb_chat_id`, `customer_name`).
-   **`DailyAnalysis` Model:** The core of the analytics engine. It stores the nine micro-metrics, four pillar scores, and the final CSI score for a single day within a conversation. It now includes a `common_topics` JSON field.
-   **`ProcessedChat` Table:** This table has been **removed**. Uniqueness is now enforced by the combination of `conversation_id` and `analysis_date` in the `daily_analyses` table.

### 2.2. Core Logic (`services/`)

-   **`file_service_optimized.py`:** The main ingestion logic now checks for the existence of `DailyAnalysis` records before processing to prevent duplicates, completely replacing the old `force_reprocess` and `ProcessedChat` logic.
-   **`batch_service.py`:** This service has been refactored to implement token-based batching. It estimates the token count of each `DailyAnalysis` and groups them into batches that do not exceed a configurable limit.
-   **`analytics_service.py`:** This service now contains a third layer of logic to support the Conversation Explorer, providing functions to fetch paginated daily analyses and individual transcripts.

### 2.3. API Routes (`routes/`)

The API has been expanded with a new set of routes for detailed data exploration.

-   **`routes/metrics.py` & `routes/charts.py`:** These continue to serve the main aggregated dashboards.
-   **`routes/explorer.py` (`GET /api/explorer/*`):** A new, dedicated router that provides direct access to the granular, daily analysis data required by the Conversation Explorer feature.

---

## 3. Development Environment

-   **Database:** The application uses a file-based SQLite database (`powerpulse.db`) managed by Alembic for migrations.
-   **Configuration:** Key parameters like `MAX_TOKENS_PER_BATCH` and `BATCH_PROCESSING_DELAY_SECONDS` are now configurable in `config.py` to allow for fine-tuning of the processing pipeline.
-   **Database Reset:** The `reset_database.py` script remains available for clearing and re-initializing the database schema during development.