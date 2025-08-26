# PowerPulse Backend: Investigation and Refactoring Plan

This document outlines the strategic plan to diagnose the database persistence issue, refactor the metrics calculation logic, and update all relevant documentation.

## 1. Understanding the Goal

The primary objective is to diagnose and fix a bug preventing the backend from saving data to the database. A secondary, major objective is to refactor the core analytics logic to use a more granular "micro-metrics" model for calculating the Customer Satisfaction Index (CSI). This involves updating the AI prompts, database models, services, and API endpoints. Finally, all project documentation, especially `GEMINI.md`, must be updated to reflect the new architecture.

## 2. Core Issues & Plan Overview

- **Bug:** Data from file uploads is not being persisted in the `powerpulse.db` database.
- **Architectural Flaw:** The current model asks the LLM for high-level "macro" metrics. The new architecture requires the LLM to provide five lower-level "micro" metrics, which will then be used to calculate the four weighted macro "pillar" scores, and finally the overall CSI score.
- **Documentation:** `GEMINI.md` is outdated and does not reflect the intended functionality.

---

## 3. Phased Execution Plan

### Phase 1: Setup & Initial Diagnosis
- [x] **Backup Database:** Move the existing `powerpulse.db` to a `backup/` folder. The application will generate a new, clean database on startup.
- [x] **Review `investigation.md`:** Analyze previous findings to avoid repeating work.
- [x] **Review Logs:** Check the `logs/` directory for any obvious errors related to database writes, API calls, or background jobs.
- [x] **Smoke Test API:** Use the running backend on `localhost:8000` to confirm the `/api/upload-json` endpoint is reachable and initiates a job.

### Phase 2: Code Path Analysis (Bug Investigation)
- [x] **Trace Data Flow:** Follow the code path from `routes/upload.py` to `services/job_service.py`.
- [x] **Analyze DB Interaction:** Scrutinize `database.py` for session management and inspect how the session is used within `services/job_service.py`.
- [x] **Check Error Handling:** Look for any `try...except` blocks that might be silently catching and ignoring exceptions during the database commit process.
- [x] **Verify Model Matching:** Ensure the data object being created in `job_service.py` matches the schema in `models.py`.

### Phase 3: Bug Fix & Verification
- [x] **Formulate Hypothesis:** Based on the analysis, determine the likely root cause of the database write failure.
- [x] **Implement Fix:** Apply the necessary code changes to resolve the issue.
- [x] **Verify Fix (E2E Test):**
    - [x] Upload `csi_test_data.json` via the API.
    - [x] Query the database directly or use an API endpoint (`/api/conversations`) to confirm the new data is present.

### Phase 4: Documentation Review
- [x] **Analyze `GEMINI.md`:** Read the current `GEMINI.md` and identify all sections that are incorrect based on the new metrics architecture.
- [x] **Analyze `CSI_refactor.md`:** Review this document for any related inaccuracies.

### Phase 5: Plan New Metrics Architecture
- [x] **Define Micro-Metrics:** Finalize the list of 5 micro-metrics to be extracted by the LLM.
    - **Effectiveness:** `resolution_achieved`, `fcr_score` (First Contact Resolution)
    - **Efficiency:** `response_time_score`
    - **Effort:** `customer_effort_score`
    - **Empathy:** `empathy_score`
- [x] **Define Macro-Metrics (Pillars):** Define the formulas for calculating the four pillars from the micro-metrics. For example, `effectiveness_score` will be a weighted average of `resolution_achieved` and `fcr_score`.
- [x] **Define Final CSI Score:** Define the formula for the final weighted average of the four pillars to calculate the `csi_score`.

---

### Phase 6: Refactor AI Service & Prompts
- [ ] **Update `services/gemini_service.py`:**
    - [ ] Re-engineer the main prompt to instruct the LLM to return a JSON object with the 5 defined micro-metrics.
    - [ ] Update the response parsing logic to handle the new JSON structure.

### Phase 7: Refactor Database and Schemas
- [ ] **Update `models.py`:**
    - [ ] Add new `Float` columns to the `Conversation` model for each of the 5 micro-metrics (e.g., `resolution_achieved`, `fcr_score`, etc.).
- [ ] **Update `schemas.py`:**
    - [ ] Update `ConversationResponse` to include the new micro-metrics.
    - [ ] Create or update a `CSIMetricsResponse` to potentially include average micro-metric scores if desired.

### Phase 8: Refactor Core Analytics Service
- [ ] **Update `services/analytics_service.py`:**
    - [ ] Modify `calculate_and_set_csi_score` to first calculate the four macro pillar scores from the new micro-metrics stored on the `Conversation` object.
    - [ ] Update the function to then calculate the final `csi_score` from the newly calculated pillar scores.
    - [ ] Update `calculate_and_cache_csi_metrics` to aggregate the new micro and macro metrics correctly.

### Phase 9: Refactor Job Service
- [ ] **Update `services/job_service.py`:**
    - [ ] Update `process_job` to correctly retrieve the 5 micro-metrics from the `gemini_service` response.
    - [ ] Ensure the service correctly populates the new columns in the `Conversation` model object before calling `analytics_service`.

### Phase 10: Update API and Export Logic
- [ ] **Update `routes/`:**
    - [ ] Update `routes/conversations.py` to allow filtering and sorting by the new micro-metrics if required.
    - [ ] Update `routes/metrics.py` to expose the new aggregated metrics.
- [ ] **Update `routes/export.py`:**
    - [ ] Modify the CSV export logic to include columns for all new micro-metrics.

### Phase 11: Final Verification & Documentation Deployment
- [ ] **Run Full E2E Test:** Execute a full application flow test with the refactored logic.
- [ ] **Run Regression Tests:** Execute the entire test suite in `tests/` to ensure no existing functionality has broken.
- [ ] **Update `GEMINI.md`:** Replace the content of the root `GEMINI.md` with the corrected, up-to-date documentation reflecting the new architecture.
- [ ] **Final Review:** Read through the `INVESTIGATION_PLAN.md` and ensure all checklist items are marked as complete.
