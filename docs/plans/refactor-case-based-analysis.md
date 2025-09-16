# 🚀 Refactor Plan: From Daily Analysis to Case-Based Analysis

**Owner:** Gemini
**Status:** Proposed

---

## 1. 🎯 Executive Summary

This document outlines the strategic plan to refactor the PowerPulse Analytics backend. The core objective is to shift our fundamental unit of analysis from arbitrary **daily segments** to a more meaningful, business-aligned **case-based** model. 

Currently, the system groups messages by day, which is a purely technical separation. The client has requested a more intelligent grouping that reflects the actual lifecycle of a customer issue—from the initial contact to its final resolution. This is a natural and powerful evolution for the platform.

We will **not** scrap the backend. The existing architecture is robust, scalable, and well-suited for this change. We will adapt the existing pipeline by replacing the daily grouping logic with a new AI-driven **Case Detection Service** and swapping the `DailyAnalysis` model for a new `CaseAnalysis` model. The core job processing, batching, and analytics framework will remain, demonstrating the flexibility of the current design.

---

## 2. ❗ Problem Statement: The "Why"

The current architecture, as described in `GEMINI.md` and `docs/plans/plan-csi-expansion-daily-metrics.md`, analyzes conversations by slicing them into 24-hour chunks. This leads to a significant limitation:

> A single customer issue that spans multiple days is treated as several disconnected interactions. 

For example, if a customer reports a power outage on Monday evening and confirms its resolution on Tuesday morning, the system currently generates two separate `DailyAnalysis` records. This approach fails to capture the true **end-to-end customer experience** for that single issue. It cannot accurately measure critical metrics like "total time to resolution" and may misinterpret the sentiment and effort involved.

Our client wants the AI to analyze conversations based on the lifecycle of a **case**, providing a holistic view of each distinct customer problem.

---

## 3. ✨ The Goal: The "What"

The primary goal is to **refactor the backend to identify, process, and analyze customer service interactions as discrete, end-to-end cases.**

### Desired Outcomes:

-   **📈 More Accurate Metrics:** CSI and all underlying micro-metrics will be calculated for the entire duration of a case, providing a more accurate reflection of the customer experience.
-   **⏱️ True Time-to-Resolution:** The system will be able to measure the exact time from when a case is opened to when it is closed.
-   **🧠 Deeper Contextual Understanding:** The AI will analyze the full context of a single issue, leading to more reliable and insightful scores.
-   **🏢 Business-Aligned Analytics:** The platform's outputs will directly map to business concepts like "case handling time" and "case resolution rate."

---

## 4. 🏛️ Architectural Overview

This refactor evolves the data pipeline described in the project `README.md`. 

### The "Before" State (Current Daily Model)

1.  **Upload**: A JSON file is uploaded.
2.  **Group by Day**: Messages are grouped by `conversation_id` and then by `date`.
3.  **Create `DailyAnalysis`**: A record is created for each day a conversation has messages.
4.  **Batch & Process**: `DailyAnalysis` records are batched and processed by the `worker.py`.

### The "After" State (New Case-Based Model)

1.  **Upload**: A JSON file is uploaded.
2.  **🤖 Case Detection (New AI Step)**: For each conversation, a new `CaseDetectionService` calls Gemini to identify the start and end times of all distinct customer issues.
3.  **Create `CaseAnalysis`**: A `CaseAnalysis` record is created for each identified case.
4.  **Batch & Process**: `CaseAnalysis` records are batched (using the same token-based logic) and processed by the `worker.py`.

This new flow leverages the existing asynchronous job infrastructure, simply swapping the analytical unit from a `DailyAnalysis` to a `CaseAnalysis`.

---

## 5. 🛠️ Detailed Implementation Plan: The "How"

This plan is broken into four phases. All file paths are relative to the project root.

### Phase 1: Data Model Refactoring (The Foundation)

-   **File to Edit:** `models.py`
-   **Actions:**
    1.  **Create `CaseAnalysis` Table:** Define a new SQLAlchemy model named `CaseAnalysis`. This model will contain:
        -   `id`, `conversation_id` (ForeignKey to `conversations.id`)
        -   `case_start_time` (DateTime, required)
        -   `case_end_time` (DateTime, nullable)
        -   `case_status` (String, e.g., 'open', 'closed')
        -   All metric columns currently found in the `DailyAnalysis` model (e.g., `csi_score`, `sentiment_score`, `resolution_achieved`, etc.).
    2.  **Deprecate `DailyAnalysis`:** The `DailyAnalysis` model and the `job_daily_analyses` association table should be removed.

-   **File to Edit:** `schemas.py`
-   **Actions:**
    1.  Create new Pydantic schemas (e.g., `CaseAnalysisResponse`) that correspond to the new `CaseAnalysis` model.
    2.  Update or remove schemas related to `DailyAnalysis`.

-   **Tool to Use:** `alembic`
-   **Actions:**
    1.  Run `alembic revision --autogenerate -m "create_caseanalysis_and_drop_dailyanalysis"`.
    2.  Review the generated migration script to ensure correctness.
    3.  Run `alembic upgrade head` to apply the changes to the database.

### Phase 2: Case Detection Service (The Core Logic)

-   **New File:** `services/case_detection_service.py`
-   **Actions:**
    1.  Create a new `CaseDetectionService` class.
    2.  Implement a primary method, `detect_cases(messages: List[Message]) -> List[Dict]`, which takes all messages for a conversation.
    3.  This method will use a specialized AI prompt to identify case boundaries.

-   **AI Prompt Design for Case Detection:**
    ```
    You are a customer service analyst. Your task is to analyze a full conversation transcript and identify distinct customer issues or "cases". A new case begins when a customer introduces a new problem. A case ends when the customer confirms resolution or the agent provides a final answer for that specific issue.

    Analyze the following messages and return a valid JSON array where each object represents a single case you have identified. Provide the start and end timestamps for each case.

    MESSAGES:
    [...message data...]

    Provide the output in this EXACT JSON format:
    [
        {
            "case_start_time": "<ISO 8601 timestamp of the first message of the case>",
            "case_end_time": "<ISO 8601 timestamp of the last message of the case>"
        },
        {
            "case_start_time": "...",
            "case_end_time": "..."
        }
    ]
    ```

### Phase 3: Pipeline & Processing Refactoring

-   **File to Edit:** `services/file_service_optimized.py`
-   **Actions:**
    1.  The main processing logic will be significantly changed. Instead of grouping messages by day, it will now iterate through each conversation from the input file.
    2.  For each conversation, it will call the new `CaseDetectionService`.
    3.  For each `case` returned by the service, it will create a `CaseAnalysis` object and associate the relevant messages (those between `case_start_time` and `case_end_time`).

-   **File to Edit:** `services/batch_service.py`
-   **Actions:**
    1.  Rename `create_daily_analysis_batches` to `create_case_analysis_batches`.
    2.  The function signature will change to accept `List[CaseAnalysis]`.
    3.  **The internal token-estimation and batching logic remains the same**, showcasing its reusability.

-   **File to Edit:** `services/gemini_service.py`
-   **Actions:**
    1.  The main analysis prompt will be slightly modified. Change the wording from "Analyze the following batch of *daily interactions*" to "Analyze the following batch of *customer service cases*." The core request for micro-metrics remains unchanged.

### Phase 4: API & Analytics Layer Refactoring

-   **File to Edit:** `services/analytics_service.py`
-   **Actions:**
    1.  All functions that query or aggregate data from the `daily_analyses` table must be refactored to use the `case_analyses` table.

-   **Files to Edit:** `routes/explorer.py`, `routes/charts.py`, `routes/metrics.py`
-   **Actions:**
    1.  The API contract, as defined in `docs/API_DOCUMENTATION.md`, will need to be updated.
    2.  `GET /api/explorer/analyses` will now be `GET /api/explorer/cases` and will return a paginated list of `CaseAnalysis` objects.
    3.  Trend charts will now be based on `case_start_time` or `case_end_time`.

---

## 6. 🧪 Verification Strategy

1.  **Unit Tests:** Write comprehensive tests for the new `CaseDetectionService`, mocking the AI call to ensure it correctly parses the AI's JSON output.
2.  **Integration Tests:** Create a dedicated test file (`e2e_test_data_cases.json`) containing a single conversation with multiple, clearly defined cases (e.g., a billing query on Monday, and a separate power outage report on Wednesday).
3.  **End-to-End Test:** Run the test file through the `POST /api/upload-json` endpoint and verify:
    -   The correct number of `CaseAnalysis` records are created.
    -   The `case_start_time` and `case_end_time` are accurate.
    -   The worker process correctly calculates and saves the CSI scores for each case.

---

## 🕵️‍♂️ A Note for the Developers

As we embark on this refactor, it's important to acknowledge the challenges we faced with the daily-analysis model. Our recent debugging sessions revealed a persistent and difficult-to-trace bug related to data batching. 

-   **The Bug:** We observed that the system was consistently creating a single, massive job instead of multiple smaller ones. This caused the worker process to hang during the AI API call.
-   **The Journey:** Our investigation initially pointed to a type mismatch in a date comparison, then to a potential issue with SQLAlchemy session commits and relationship loading. Despite several attempted fixes, the core issue remained, indicating a deeper, more complex problem in how the daily-segmented data was being passed between services.

This experience is the primary motivation for this refactor. The daily-analysis model introduced a high degree of complexity for what is ultimately an arbitrary grouping. Moving to a **case-based model** is not just a feature request—it is a strategic architectural decision that will simplify our data flow, eliminate the source of the recent bugs, and create a more robust and logical foundation for the future.

Let's use this opportunity to build a cleaner, more powerful system. Good luck!
