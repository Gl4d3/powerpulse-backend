# PowerPulse Analytics Gemini Context (CSI Refactor v4.0 - BFF)

This document provides a comprehensive and technically accurate overview of the PowerPulse Analytics backend. It details the final architecture after a significant refactoring to a daily granularity CSI model and the implementation of a Backend for Frontend (BFF) pattern to serve a Next.js UI.

---
**IMPORTANT NOTE:** For detailed, human-readable API documentation, including sample requests and responses, refer to the official **[`docs/API_DOCUMENTATION.md`](./docs/API_DOCUMENTATION.md)**. This file is the canonical source for API contracts.
---

## 1. High-Level Architecture & Data Flow

The backend is a FastAPI application that processes customer service chat logs and serves a frontend with pre-aggregated, UI-specific data.

1.  **Upload:** A user uploads a JSON file via `POST /api/upload-json`. The `force_reprocess` query parameter can be used to bypass the cache of already-processed conversations.

2.  **Daily Grouping & Persistence:** The backend parses conversations and groups messages by date. For each day a conversation has activity, a `DailyAnalysis` record is created in the database.

3.  **Batching & AI Analysis:** The new `DailyAnalysis` records are batched and sent to a background job queue. A Google Gemini model analyzes each day's messages to extract eight **micro-metrics** (`sentiment_score`, `sentiment_shift`, `resolution_achieved`, `fcr_score`, `ces`, `first_response_time`, `avg_response_time`, `total_handling_time`).

4.  **Pillar & CSI Calculation:** For each `DailyAnalysis` record, four **macro-metric pillars** (Effectiveness, Effort, Efficiency, Empathy) are calculated from the micro-metrics. A final, weighted **CSI score** is then calculated from these pillars. All results are stored in the `DailyAnalysis` table.

5.  **BFF Aggregation & API Access:** The API routes act as a Backend for Frontend. They query the detailed `DailyAnalysis` table and perform on-the-fly aggregations to provide data in the exact format the frontend requires. This includes system-wide metrics for the main dashboard, time-series data for charts, and simplified, conversation-level summaries for list views.

---

## 2. Technical Deep Dive

### 2.1. Database (`models.py`)

-   **`Conversation` Model:** Now primarily stores metadata (`fb_chat_id`, message counts). The granular metric fields have been removed.
-   **`DailyAnalysis` Model:** The new core of the analytics engine. It stores the eight micro-metrics, four pillar scores, and the final CSI score for a single day within a conversation.

### 2.2. Core Logic (`services/`)

-   **`analytics_service.py`:** This service now contains two layers of logic:
    1.  `calculate_and_set_daily_csi_score`: The low-level function that calculates pillars and CSI for a single `DailyAnalysis` object based on the formulas from `gemini-refactor.md`.
    2.  Frontend-facing aggregation functions (e.g., `calculate_and_cache_csi_metrics`, `get_sentiment_trend`): These functions query the `DailyAnalysis` table to compute the specific, aggregated data structures required by the frontend API contract.

### 2.3. API Routes (`routes/`)

The API has been tailored to serve the frontend's needs directly.

-   **`routes/metrics.py` (`GET /api/metrics`):** Serves the main dashboard by aggregating all daily analyses to provide system-wide KPIs, including pillar scores renamed for the frontend (e.g., `effectiveness_score` -> `resolution_quality`).
-   **`routes/charts.py` (`GET /api/charts/sentiment-trend`):** A new, dedicated router that provides data pre-formatted for specific UI charts.
-   **`routes/conversations.py` (`GET /api/conversations`):** Provides a simplified, aggregated summary of each conversation, calculating averages from the underlying daily data to match the frontend's expected schema.

---

## 3. Development Environment

-   **Database:** The application is now configured to use a file-based SQLite database (`powerpulse.db`).
-   **Database Reset:** The `reset_database.py` script is used to clear and re-initialize the database schema after model changes. It can be run non-interactively with `python reset_database.py --force`.
-   **Logging:** SQLAlchemy's logging level has been set to `WARNING` to reduce noise during development.