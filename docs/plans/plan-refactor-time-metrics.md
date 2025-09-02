# Plan: Refactor Time-Based Metrics Calculation

**Owner:** Gemini
**Created:** 2025-08-28
**Purpose:** To refactor the backend to calculate time-based metrics (`first_response_time`, `avg_response_time`, `total_handling_time`) within our own code instead of asking the AI. This will increase accuracy, reduce API costs, and improve performance.

---

## 1. Phased Execution Plan

### Phase 1: Create Time Calculation Service (In Progress)
- [ ] **Create `services/time_metric_service.py`:**
    - [ ] Create a new service file dedicated to these calculations.
    - [ ] Implement a function `calculate_time_metrics_for_daily_analysis(daily_analysis: DailyAnalysis) -> Dict`.
    - [ ] This function will contain the logic to accurately calculate `first_response_time`, `avg_response_time`, and `total_handling_time` from the message timestamps within the `daily_analysis` object.

### Phase 2: Modify AI Service
- [ ] **Update `services/gemini_service.py`:**
    - [ ] Modify the `_create_daily_analysis_batch_prompt` function to remove `first_response_time`, `avg_response_time`, and `total_handling_time` from the requested JSON structure.
    - [ ] Update the `_create_fallback_result_daily` function to remove these fields from the fallback object.

### Phase 3: Integrate into Job Service
- [ ] **Update `services/job_service.py`:**
    - [ ] Import the new `time_metric_service`.
    - [ ] In the `process_job` function, after receiving a successful analysis from the AI, call the new `calculate_time_metrics_for_daily_analysis` function.
    - [ ] Update the `DailyAnalysis` object with the accurate, calculated time metrics before committing to the database.

### Phase 4: Verification
- [ ] **Run a new test upload.**
- [ ] **Export the `daily_analyses` table to CSV.**
- [ ] **Verify that the time-based metric columns are populated with correct, script-calculated values.**
- [ ] **Confirm that the `result` column in the `jobs` table no longer contains the time-based metrics from the AI.**

---
