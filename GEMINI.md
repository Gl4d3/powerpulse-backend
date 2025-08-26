# PowerPulse Analytics Gemini Context (CSI Refactor v2.0)

This document provides a comprehensive overview of the PowerPulse Analytics backend, outlining the refactored architecture for calculating the Customer Satisfaction Index (CSI) using a granular, multi-layered metrics system.

---
**IMPORTANT NOTE:** For detailed information on API endpoints, request/response samples, and parameters, refer to the official **[`docs/API_DOCUMENTATION.md`](./docs/API_DOCUMENTATION.md)**. This file is the canonical source for API details and must be kept up-to-date with any changes.
---

## 1. High-Level Architecture & Data Flow

The PowerPulse Analytics backend is a FastAPI application designed to process and analyze customer service chat logs. The data flow is centered around a sophisticated CSI model that transforms qualitative chat data into quantitative, actionable insights.

1.  **Upload:** A user uploads a JSON file of chat conversations via the `POST /api/upload-json` endpoint.

2.  **Processing:** The backend processes the file in the background using an optimized, job-based system. Conversations are parsed, cleaned, and grouped into batches for efficient processing.

3.  **AI Analysis (Micro-Metrics Extraction):** Each conversation is sent to an AI service (Google Gemini) with a carefully engineered prompt. The AI's task is to analyze the conversation and extract five specific **micro-metrics**, returning them as a JSON object. The micro-metrics are:
    *   `resolution_achieved`: A score indicating if the customer's issue was resolved.
    *   `fcr_score`: A score for "First Contact Resolution," measuring if the issue was solved in a single interaction.
    *   `response_time_score`: A score reflecting the timeliness of the agent's responses.
    *   `customer_effort_score`: A score representing the amount of effort the customer had to expend.
    *   `empathy_score`: A score for the emotional tone and empathy demonstrated by the agent.

4.  **Database Persistence (Micro-Metrics):** The raw messages and the five extracted micro-metric scores are stored in a SQLite database in the `Conversation` table.

5.  **Macro-Metrics Calculation (The Four Pillars):** The application then calculates four higher-level **macro-metrics**, also known as the **Four Pillars of Service Quality**, using weighted averages of the micro-metrics.
    *   **Effectiveness:** Calculated from `resolution_achieved` and `fcr_score`.
    *   **Efficiency:** Calculated from `response_time_score`.
    *   **Effort:** Calculated from `customer_effort_score`.
    *   **Empathy:** Calculated from `empathy_score`.
    These four pillar scores are also stored in the `Conversation` table.

6.  **Final CSI Calculation:** The final, weighted **Customer Satisfaction Index (CSI)** is calculated from the four pillar scores and stored.

7.  **Metrics Aggregation:** All scores (micro-metrics, pillars, and final CSI) are aggregated across all conversations and cached for quick retrieval.

8.  **API Access:** The processed data, individual scores, and aggregated metrics are exposed to the user through various API endpoints.

---

## 2. Technical Deep Dive (Post-Refactor)

This section provides a detailed walkthrough of the codebase after the micro-metrics refactor.

### 2.1. Database (`models.py`)

The `Conversation` model will be updated to store the full spectrum of the CSI analysis:

-   **Micro-Metric Scores:** Five new `Float` columns are added: `resolution_achieved`, `fcr_score`, `response_time_score`, `customer_effort_score`, and `empathy_score`.
-   **Pillar Scores:** The four `Float` columns for the pillars remain: `effectiveness_score`, `efficiency_score`, `effort_score`, and `empathy_score`.
-   **Final Score:** The `csi_score` column stores the final weighted CSI score and is indexed for faster querying.

### 2.2. Data Schemas (`schemas.py`)

Pydantic schemas will be updated to expose the new data model:

-   **`ConversationResponse`:** This model will be expanded to include all nine new CSI-related fields (5 micro, 4 macro) to expose them in the API.
-   **`CSIMetricsResponse`:** This response model will be updated to serve aggregated metrics for the overall CSI, the four pillars, and potentially the five micro-metrics.

### 2.3. API Routes (`routes/`)

-   **`routes/metrics.py`:** The `GET /api/metrics` endpoint will return the updated `CSIMetricsResponse`.
-   **`routes/conversations.py`:** The `GET /api/conversations` endpoint will be updated to allow sorting and filtering based on any of the new micro-metric or pillar scores.
-   **`routes/export.py`:** The `GET /api/download` endpoint will be updated to include all new metric fields in the CSV export.

### 2.4. Core Logic (`services/`)

-   **`services/gemini_service.py` (AI Client):**
    -   The core prompt will be re-engineered to instruct the AI model to analyze conversations and return a JSON object containing the five specified micro-metrics.
    -   Response parsing logic will be updated to handle the new, more complex JSON structure.

-   **`services/job_service.py` (Job Execution):**
    -   The `process_job` function will take the five micro-metric scores from `gemini_service` and store them in the corresponding columns in the `Conversation` table.
    -   It will then trigger the `analytics_service` to calculate the pillar and final CSI scores.

-   **`services/analytics_service.py` (Metrics Calculation):**
    -   **`calculate_and_set_csi_score`:** This function will be heavily modified. It will first calculate the four pillar scores for a conversation using the newly available micro-metrics. It will then use those pillar scores to calculate the final weighted `csi_score`.
    -   **`calculate_and_cache_csi_metrics`:** This function will be updated to aggregate all levels of the new metrics system and cache the results.
