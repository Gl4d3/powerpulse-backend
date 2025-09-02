# PowerPulse Backend: Scalability & Asynchronicity Refactor Plan

This document outlines the strategic plan to re-architect the backend's data processing pipeline to be fully asynchronous and scalable for large datasets.

## 1. Understanding the Goal

The primary objective is to fix two critical architectural flaws that prevent the system from handling large file uploads effectively:
1.  **Flawed Batching Logic:** The system fails to split large uploads into multiple, smaller jobs, leading to a single massive job that overwhelms the AI service, triggers rate-limiting, and results in fallback scores.
2.  **Synchronous API Endpoint:** The `POST /api/upload-json` endpoint blocks until all processing is complete, preventing users from getting an immediate `upload_id` to track the status of long-running tasks.

This refactor will make the system truly asynchronous, robust, and ready for large-scale use.

---

## 2. Phased Execution Plan

### Phase 1: Fix Batching and Rate-Limiting
- [x] **Introduce and Enforce Batch Size:**
    - [x] Inspect `config.py` for a `BATCH_SIZE` setting. If it doesn't exist, add it with a default value of `20`.
    - [x] Refactor the `create_batches` function in `services/batch_service.py` to strictly adhere to the `BATCH_SIZE`.
- [x] **Ensure Multi-Job Creation:**
    - [x] Review the logic in `services/file_service_optimized.py` to ensure it correctly iterates over multiple batches and creates a distinct job for each one.

### Phase 2: Decouple the Upload Endpoint
- [x] **Generate ID First:**
    - [x] Modify the `upload_json` endpoint in `routes/upload.py` to generate a `upload_id` immediately upon request.
- [x] **Return Immediately & Delegate to Background Task:**
    - [x] The endpoint will immediately return a response containing the `upload_id`.
    - [x] The core processing logic will be moved into a new, separate function.
    - [x] This new function will be passed to FastAPI's `BackgroundTasks` to be executed after the response is sent.
- [x] **Refactor the Service to Accept ID:**
    - [x] The `optimized_file_service.process_grouped_chats_json` function will be refactored to accept the `upload_id` as a parameter.

### Phase 3: Documentation Update
- [x] **Update `API_DOCUMENTATION.md`:**
    - [x] Add a note to the `POST /api/upload-json` endpoint documentation explaining its new asynchronous nature and the importance of using the `/api/progress/{upload_id}` endpoint.

### Phase 4: Final Verification
- [ ] **Process Large File:**
    - [ ] Upload the large `grouped_chats_1755190636068.json` file.
- [ ] **Verify Asynchronous Response:**
    - [ ] Confirm that the `/api/upload-json` endpoint returns a response in under a second.
    - [ ] Immediately query the `/api/progress/{upload_id}` endpoint and verify the status is "in_progress" or "pending".
- [ ] **Verify Correct Processing:**
    - [ ] Check the logs for any `429 Too Many Requests` errors.
    - [ ] Query the `jobs` table to confirm that multiple jobs were created for the single upload.
    - [ ] Query the `conversations` table to confirm that real, varied CSI scores have been saved, not the fallback values.
