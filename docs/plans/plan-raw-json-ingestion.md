# Plan: Ingest Raw JSON Data & Add Usage Metrics

**Owner:** Gemini
**Created:** 2025-08-27
**Purpose:** To refactor the backend to process raw, flat JSON data and to add detailed usage metrics for each AI analysis job.

---

## 1. Phased Execution Plan

### Phase 1: Enhance Database Schema (In Progress)
- [ ] **Update `models.py`:**
    - [ ] Add a `customer_name` column to the `Conversation` model.
    - [ ] Create a new `JobMetric` table to store usage data for each job. It will include columns for `job_id`, `token_usage`, `processing_time_seconds`, and `api_calls_made`.
- [ ] **Generate & Apply Database Migration:**
    - [ ] Run `alembic revision --autogenerate` to create the migration script for the schema changes.
    - [ ] Run `alembic upgrade head` to apply the migration.

### Phase 2: Implement Preprocessing Logic
- [ ] **Create Preprocessing Function:**
    - [ ] In `services/file_service_optimized.py`, create a new `_preprocess_and_group_raw_data` function to transform the flat JSON array into a grouped dictionary.
- [ ] **Integrate into Workflow:**
    - [ ] Modify the main `process_grouped_chats_json` function to use the new preprocessing step.
    - [ ] Update the logic that creates `Conversation` objects to populate the new `customer_name` field.

### Phase 3: Implement Usage Metrics Tracking
- [ ] **Update `services/gemini_service.py`:**
    - [ ] Modify the `analyze_daily_analyses_batch` method to return not just the analysis results, but also the token count from the API response.
- [ ] **Update `services/job_service.py`:**
    - [ ] In the `process_job` function, record the start and end time of the AI API call.
    - [ ] After the call, create a `JobMetric` record and populate it with the `job_id`, the token usage returned from the `gemini_service`, and the calculated processing time.

### Phase 4: API Exposure & Finalization
- [ ] **Create a New Metrics Endpoint (Optional):**
    - [ ] Consider creating a new endpoint, e.g., `GET /api/metrics/usage`, to expose aggregated usage data.
- [ ] **Update Documentation:**
    - [ ] Update `docs/DATABASE_SCHEMA.md` and `docs/API_DOCUMENTATION.md` to reflect all the new changes.

---
