# Plan: Prompt Enhancement & Assumed CSI Service

**Owner:** Gemini
**Status:** In Progress

This document outlines the two-track strategic plan to enhance the PowerPulse Analytics backend.

---

## **Track 1: Main Prompt Replacement**

**Goal:** Replace the existing AI prompt for micro-metric generation with the improved, more structured version from `docs/improved-prompt.txt`. This is a low-effort, high-impact change that improves the clarity and reliability of the AI's instructions without requiring changes to the data parsing logic.

### **To-Do Checklist**

- [x] **1. Replace Prompt Text:** Swap the prompt string in `services/gemini_service.py` with the content from `docs/improved-prompt.txt`.
- [ ] **2. Verification:** Run a full end-to-end test by uploading a sample file and verifying that the worker processes the job successfully and populates the database with the correct metrics. **(Blocked)**

---

## **Track 2: New `assumed_csi` Service**

**Goal:** Create a new, separate, manually-triggered service dedicated solely to generating an `assumed_csi` score. This service will use its own specialized prompt, run independently, and populate a new `assumed_csi` column in the `daily_analyses` table.

### **To-Do Checklist**

- [ ] **1. Database & Model Changes:**
    - [ ] Modify `models.py`: Add a `job_type` field to the `Job` model.
    - [ ] Modify `models.py`: Add a nullable float field `assumed_csi` to the `DailyAnalysis` model.
    - [ ] Generate and apply a new Alembic migration for the schema changes.
- [ ] **2. Create New `assumed_csi_service.py`:**
    - [ ] Create the new service file.
    - [ ] Implement the function to call the Gemini API with a dedicated prompt asking for the `assumed_csi` score.
    - [ ] Implement the logic to parse the response and update the `DailyAnalysis` record.
- [ ] **3. Create Manual Trigger Endpoint:**
    - [ ] Create a new `POST /api/jobs/generate-assumed-csi` endpoint in `routes/jobs.py`.
    - [ ] Implement logic to create jobs with the new `ASSUMED_CSI_GENERATION` job type.
- [ ] **4. Update Worker Logic:**
    - [ ] Modify `worker.py` to check the `job_type` and route tasks to the appropriate service (`batch_service` or the new `assumed_csi_service`).
- [ ] **5. Verification:**
    - [ ] Write unit tests for the new service and API endpoint.
    - [ ] Perform an end-to-end test by calling the new endpoint and verifying the `assumed_csi` field is populated correctly in the database.
