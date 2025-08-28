# Plan: CSI Model Expansion & Daily Granularity Refactor

**Owner:** Gemini
**Created:** 2025-08-26
**Purpose:** To track the strategic implementation of two major architectural changes: the expansion of the CSI metrics model and the shift to per-day analysis granularity.

---

## 1. Understanding the Goal

The primary objective is to evolve the PowerPulse Analytics backend by implementing two major architectural changes. First, to significantly expand the Customer Satisfaction Index (CSI) model by incorporating a larger set of micro and macro metrics as detailed in the `gemini-refactor.md` document. Second, to fundamentally shift the analysis from a per-conversation basis to a per-conversation, per-day basis. This will enable the tracking of daily trends within a single, long-running customer interaction, with the new, more granular metrics being calculated for each day and then aggregated. The final implementation must expose this new, richer dataset via the API.

---

## 2. Phased Execution Plan

### Phase 1: Schema and Data Model Overhaul (In Progress)
- [ ] **Update `models.py`:**
    - [ ] Introduce a new `DailyAnalysis` table with a foreign key to the `Conversation` table.
    - [ ] The new table will contain a `date` column and columns for all new micro and macro metrics defined in `gemini-refactor.md`.
    - [ ] The existing metric columns on the `Conversation` model will be removed, retaining only a final, overall aggregated CSI score.
- [ ] **Update `schemas.py`:**
    - [ ] Create new Pydantic schemas (`DailyAnalysisResponse`, etc.) corresponding to the new `DailyAnalysis` model.
    - [ ] Update existing schemas to reflect the changes, ensuring backward compatibility where necessary.
- [ ] **Develop Database Migration Plan:**
    - [ ] Outline a clear, step-by-step database migration script.

### Phase 2: Refactor Data Processing and Batching Pipeline
- [ ] **Modify `services/file_service_optimized.py`:**
    - [ ] Add logic to group a conversation's messages by day based on `social_create_time`.
- [ ] **Create a New "Daily Analysis" Service:**
    - [ ] Implement a new service (`services/daily_analysis_service.py`) responsible for creating the `DailyAnalysis` objects in the database from the day-grouped messages.
- [ ] **Rework `services/batch_service.py`:**
    - [ ] The `create_batches` function will be modified to operate on pending `DailyAnalysis` objects instead of `Conversation` objects.

### Phase 3: Update AI and Analytics Services
- [ ] **Update `services/gemini_service.py`:**
    - [ ] Re-engineer the AI prompt to ask for the full list of new micro-metrics.
    - [ ] Update the response parsing logic to handle the new, more complex JSON structure.
- [ ] **Update `services/job_service.py`:**
    - [ ] The `process_job` function will be updated to store the AI results in the `DailyAnalysis` table.
- [ ] **Expand `services/analytics_service.py`:**
    - [ ] The core calculation logic will be moved to operate on `DailyAnalysis` objects.
    - [ ] A new function will be added to aggregate daily scores into an overall score on the parent `Conversation` object.

### Phase 4: API Exposure
- [ ] **Create New API Endpoints:**
    - [ ] Implement `GET /api/metrics/daily` for system-wide daily trends.
    - [ ] Implement `GET /api/conversations/{chat_id}/daily` for a conversation-specific daily breakdown.
- [ ] **Update Existing API Endpoints:**
    - [ ] Modify existing endpoints to reflect the new data model.

---

## 3. Verification Strategy
- **Unit Tests:** New tests will be written for daily grouping logic, new metric calculations, and new database models.
- **Integration Tests:** An end-to-end test will be created to verify the entire flow from file upload to API response, using a multi-day conversation file.
- **Manual Verification:** The database and API responses will be manually inspected to ensure correctness and accuracy.

---

## 4. Anticipated Challenges & Considerations
- **Complexity:** This is a significant architectural refactor, carrying a high risk of bugs.
- **Performance:** The introduction of daily analysis could impact performance. Queries and data processing will need to be optimized.
- **AI Prompt Engineering:** Reliably extracting a larger set of metrics from the AI will be challenging.
- **Backward Compatibility:** These are breaking changes. API versioning might be considered.
- **Documentation:** All relevant documentation (`GEMINI.md`, `API_DOCUMENTATION.md`) will require a complete overhaul.
