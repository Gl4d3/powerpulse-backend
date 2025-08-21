# Gemini Agent Working Protocol

This document outlines the operational guidelines, repository lifecycle, and testing procedures to be followed in our collaboration.

## 1. Core Directives

The following rules will be strictly followed during our interactions:

-   **Continuous Schema & Config Awareness:** I will constantly reference `models.py`, `schemas.py`, `config.py`, and `database.py` to ensure all code changes are consistent with the existing data structures and configurations.
-   **Documentation First:** All significant changes will be documented.
    -   The `docs/repository_lifecycle.md` file will be updated if the core pipeline or component responsibilities change.
    -   For any long-running task, a new plan file will be created by copying `docs/plan-docs-tracking.md` to `docs/plan-{task-name}.md`. This file will be used to track progress, schema changes, and migration notes.

## 2. Repository Lifecycle

The PowerPulse backend follows a six-stage data processing pipeline:

1.  **File Upload:** A JSON file containing conversations is uploaded via the API.
2.  **AI Analysis:** The AI service (Gemini) analyzes each conversation for sentiment, customer satisfaction, and first-contact resolution (FCR).
3.  **Database Storage:** The original conversations and their corresponding AI analysis results are saved to the database.
4.  **Metrics Calculation:** Aggregated metrics are recalculated based on the new data.
5.  **Cache Update:** The newly calculated metrics are cached for fast dashboard access.
6.  **Database Commit:** All changes from the transaction are permanently saved to the database.

A more detailed breakdown of file responsibilities and data schemas can be found in `docs/repository_lifecycle.md`.

## 3. Task & Progress Tracking

For any task that involves multiple steps or changes to the codebase, the following process will be used:

1.  **Create Plan:** A new plan file will be created from the template: `cp docs/plan-docs-tracking.md docs/plan-{task-name}.md`.
2.  **Track Progress:** The plan file will be updated with notes, schema snapshots, and status updates as work is completed.

This ensures a clear and persistent record of all changes.

## 4. Testing

To ensure the stability and correctness of the codebase, the following testing options are available.

**Proposed Next Steps (Pick one):**

1.  **Quick Smoke Test:** Run static checks and unit tests. This is the recommended first step.
    ```bash
    pip install -r requirements-test.txt; pytest tests/unit -q
    ```
2.  **Full Test Suite:** Run the complete test suite, including both unit and integration tests. This is more comprehensive but takes longer.
    ```bash
    pip install -r requirements-test.txt; pytest -q
    ```
3.  **E2E Smoke Test:** Run a manual end-to-end pipeline test by uploading a sample file to the running server. This verifies the entire workflow.
    ```bash
    python main.py & sleep 2; curl -X POST http://localhost:8000/api/upload-json -F "file=@tests/fixtures/sample_conversations.json" -F "force_reprocess=false"
    ```

Please confirm which testing option you would like to proceed with.
