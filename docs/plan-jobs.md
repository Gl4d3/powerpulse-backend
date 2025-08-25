# Plan: AI Request Batching and Job System

**Objective:** Refactor the AI request flow to use a job-based batching system. This will prevent rate-limiting errors by controlling concurrency and grouping conversations into larger, token-aware jobs.

**Date:** 2025-08-21

---

## 1. Schema & Config Changes

### `config.py`
-   Add `MAX_TOKENS_PER_JOB`: Maximum estimated tokens per batch request to the AI service. (Default: `16000`)
-   Add `AI_CONCURRENCY`: Global limit for concurrent requests to any AI service. (Default: `5`)

### `models.py`
-   Create a new `Job` table (`jobs`):
    -   `id`: Primary key.
    -   `upload_id`: Foreign key to the upload process.
    -   `status`: TEXT (e.g., 'pending', 'in_progress', 'completed', 'failed').
    -   `created_at`: DATETIME.
    -   `completed_at`: DATETIME (nullable).
    -   `result`: JSON (nullable).
-   Create a new association table `job_conversations`:
    -   `job_id`: Foreign key to `jobs.id`.
    -   `conversation_id`: Foreign key to `conversations.id`.

### `schemas.py`
-   Create `JobCreate`, `Job`, and `JobUpdate` Pydantic schemas corresponding to the `Job` model.

---

## 2. Implementation Plan

### Step 1: Core Components
-   **[ ] `config.py`:** Add `MAX_TOKENS_PER_JOB` and `AI_CONCURRENCY`.
-   **[ ] `models.py` & `schemas.py`:** Implement the `Job` model and schemas.
-   **[ ] `database.py`:** Ensure the new tables are created.

### Step 2: Batching Service
-   **[ ] Create `services/batch_service.py`:**
    -   Implement `estimate_token_count(conversation)`: A function to estimate the token size of a conversation. A simple proxy is `len(text) / 4`.
    -   Implement `create_batches(conversations)`:
        -   Takes a list of conversations.
        -   Groups them into batches, ensuring the total estimated tokens in each batch does not exceed `MAX_TOKENS_PER_JOB`.
        -   Returns a list of lists, where each inner list is a batch of conversations.

### Step 3: Job Service & Concurrency Control
-   **[ ] Create `services/job_service.py`:**
    -   Initialize a global `asyncio.Semaphore` with the value from `config.AI_CONCURRENCY`.
    -   Implement `create_jobs_for_upload(upload_id, batches)`:
        -   Creates `Job` records in the database for each batch.
        -   Populates the `job_conversations` association table.
    -   Implement `process_job(job_id)`:
        -   The core worker function.
        -   Acquires the semaphore.
        -   Fetches job details and its conversations from the DB.
        -   Calls the appropriate AI service (`gemini_service` or `gpt_service`) with the batch of conversations.
        -   Updates the `Job` status and stores the result.
        -   Releases the semaphore.

### Step 4: Refactor AI Services
-   **[ ] `services/gemini_service.py` & `services/gpt_service.py`:**
    -   Create a new method `analyze_conversations_batch(conversations)`:
        -   Takes a list of conversations.
        -   Constructs a single prompt that instructs the AI to process all conversations in the batch and return a JSON array of results.
        -   Parses the JSON response from the AI into a list of analysis results.
        -   Handles potential errors in the AI response.

### Step 5: Orchestration
-   **[ ] `services/file_service_optimized.py`:**
    -   Modify the main processing logic (`process_uploaded_file` or similar).
    -   After creating `Conversation` objects, call the `BatchService` to create batches.
    -   Call the `JobService` to create and queue the jobs.
    -   Instead of awaiting all AI calls directly, it will now await the completion of all jobs for the upload. This could be a simple loop that calls `process_job` for each created job ID.

---

## 5. Test Failures & Action Plan

**Objective:** After the initial refactoring, the test suite is failing with multiple errors. This section outlines the categories of failures and the plan to fix them.

**Date:** 2025-08-21

### Failure Categories

1.  **Outdated Unit Tests:** The majority of failures are due to tests that were not updated after the refactoring. This affects:
    -   `tests/unit/test_gemini_service.py`
    -   `tests/unit/test_gpt_service.py`
    -   `tests/unit/test_models.py`
    -   `tests/unit/test_schemas.py`

2.  **Incorrect Mocking:** The integration test `tests/integration/test_job_system.py` is failing because the mock patch target for the AI services is incorrect.

3.  **Incorrect Pydantic Model Usage:** The test in `tests/unit/test_metrics_calculation.py` is failing because it uses dictionary-style access on a Pydantic model instead of attribute access.

### Action Plan

1.  **Fix Model and Schema Tests:** Update the tests in `test_models.py` and `test_schemas.py` to use the correct attribute names and data structures.
2.  **Fix AI Service Tests:** Update the tests for `gemini_service.py` and `gpt_service.py` to reflect the new `analyze_conversations_batch` method.
3.  **Fix Metrics Calculation Test:** Correct the Pydantic model usage in `test_metrics_calculation.py`.
4.  **Fix Integration Test:** Correct the mock patch target in `test_job_system.py`.