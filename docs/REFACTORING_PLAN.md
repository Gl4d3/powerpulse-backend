# PowerPulse Backend: Refactoring & Analytics Plan

This document outlines the strategic plan to refine data processing accuracy and implement a new time-based analytics feature.

## 1. Understanding the Goal

The primary objective is to enhance the backend by addressing three key areas:
1.  **Fix Overly Aggressive Filtering:** Correct the auto-reply filter to be more precise, ensuring valid messages are not discarded.
2.  **Enrich Conversation Data:** Implement logic to correctly calculate and populate `total_messages`, `customer_messages`, and `agent_messages` for each conversation.
3.  **Implement Historical Analytics:** Create a new API endpoint that provides daily aggregated averages for all CSI micro and macro metrics over a specified date range, using the message timestamp (`social_create_time`) as the authoritative date.

---

## 2. Phased Execution Plan

### Phase 1: Bug Fixes & Data Enrichment
- [ ] **Refine Message Filter:**
    - [ ] In `services/file_service_optimized.py`, modify the `_validate_message` function.
    - [ ] Change the filter logic from a broad substring check (`"*977#" in message_content`) to an exact match for the full auto-reply sentence: `"Thank you for reaching out! Did you know that you can now dial *977# to report a power outage or get your last three tokens instantly?"`.

- [ ] **Implement Message Counts:**
    - [ ] In `services/file_service_optimized.py`, locate the section where `Conversation` and `Message` objects are created in memory.
    - [ ] After all messages for a conversation have been processed and appended, add logic to calculate the counts:
        - `total_messages`: Total number of messages in the `conversation.messages` list.
        - `customer_messages`: Count of messages where `direction` is `'to_company'`.
        - `agent_messages`: Count of messages where `direction` is `'to_client'`.
    - [ ] Set these calculated values on the `conversation` object before it is committed to the database.

### Phase 2: Time-Based Analytics Feature
- [ ] **Update Pydantic Schemas:**
    - [ ] In `schemas.py`, create two new Pydantic models:
        - `DailyMetricsResponse`: A model to represent the aggregated metrics for a single day. It will include a `date` field and fields for the average of all 9 micro and macro metrics (e.g., `avg_csi_score`, `avg_resolution_achieved`, etc.).
        - `HistoricalMetricsResponse`: A container model that holds a list of `DailyMetricsResponse` objects.

- [ ] **Create New Analytics Service Function:**
    - [ ] In `services/analytics_service.py`, create a new function: `get_historical_csi_metrics(db: Session, start_date: date, end_date: date)`.
    - [ ] This function will perform a SQLAlchemy query that:
        - Joins the `Conversation` and `Message` tables.
        - Filters messages where `social_create_time` is between the `start_date` and `end_date`.
        - Groups the results by the date of the `social_create_time`.
        - Calculates the daily average for all 9 CSI metrics.
        - Returns the data structured to match the new Pydantic schemas.

- [ ] **Create New API Endpoint:**
    - [ ] In `routes/metrics.py`, create a new endpoint: `GET /api/metrics/historical`.
    - [ ] The endpoint will accept two query parameters: `start_date` and `end_date`.
    - [ ] It will call the `get_historical_csi_metrics` service function with the provided dates.
    - [ ] It will return the results, serialized using the `HistoricalMetricsResponse` schema.

### Phase 3: Final Verification
- [ ] **Bug Fix Verification:**
    - [ ] Create a specific test file with conversations that should and should not be filtered by the new logic.
    - [ ] Process the file and verify that the message counts and conversation data in the database are correct.
- [ ] **Feature Verification:**
    - [ ] Write unit tests for the `get_historical_csi_metrics` function with mock data to ensure the aggregation logic is correct.
    - [ ] Perform an end-to-end test by calling the new `GET /api/metrics/historical` endpoint with a valid date range and confirming the response is accurate and well-formed.
