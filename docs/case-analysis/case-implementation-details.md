# 🕵️‍♂️ Case Analysis: Implementation Deep Dive & Client Requirements

**Owner:** Gemini
**Status:** Planning
**Companion Doc:** [Refactor Plan: From Daily Analysis to Case-Based Analysis](./case-based-analysis.md)

---

## 1. 🎯 Purpose of This Document

This document is a technical supplement to the high-level refactoring plan. Its goal is to provide a detailed guide for developers on **how** we will implement the "case" entity and, most importantly, to define **what specific information we require from the client** to make this implementation successful.

A "case" is a business concept, not just a technical one. A successful implementation depends on translating the client's nuanced understanding of their customer interactions into concrete, programmable rules.

---

## 2. 🤔 Defining a "Case": A Questionnaire for the Client

Before a single line of code is written for the core logic, we must have clear, unambiguous answers to the following questions. The success of this entire feature hinges on the clarity of these definitions. The questions below are crucial for configuring the AI-powered case detection.

### Core Definitions

1.  **What event signals the START of a new case?**
    *   **Scenario A: Inactivity.** A customer sends a message after a long period of silence.
        *   **❓ Question:** What should this period of inactivity be? (e.g., 12 hours, 24 hours, 48 hours?) Our recommendation is **24 hours**.
    *   **Scenario B: New Topic.** A customer changes the subject mid-conversation.
        *   **❓ Question:** Do you want to treat this as a new case, or as part of the existing one? We recommend treating it as a **new case** to accurately measure the effort for each distinct issue. Our AI can be trained to spot these topic changes.

2.  **What event signals the END of a case?**
    *   **Scenario A: Customer Confirmation.** The customer explicitly confirms their issue is resolved (e.g., "Thank you, it's working now," "That's all I needed").
        *   **❓ Question:** Is this a reliable signal for closing a case? (Almost certainly yes).
    *   **Scenario B: Agent Confirmation.** An agent states the case is closed (e.g., "I'm glad I could help. I'm closing this ticket now.").
        *   **❓ Question:** Do your agents have standard procedures for closing conversations? If so, can you provide examples?
    *   **Scenario C: Inactivity After Solution.** An agent provides a solution, and the customer does not reply.
        *   **❓ Question:** How long should we wait before considering the case implicitly closed? (e.g., 48 hours, 72 hours?) Our recommendation is **48 hours**.

### Edge Case Scenarios

1.  **Re-opened Cases:** A customer replies to a conversation thread for a case that was previously marked "closed."
    *   **❓ Question:** Should this be treated as **re-opening the original case** (which would negatively affect the "time to resolution" metric) or as **creating a brand new case**?
    *   **Our Recommendation:** Treat it as a new case but link it to the original. We can add a `reopened_from_case_id` field to our data model to track this.

2.  **Multi-Issue Conversations:** A customer discusses a billing problem and a technical issue in the same continuous chat.
    *   **❓ Question:** Should this be one case or two?
    *   **Our Recommendation:** Two separate cases. The AI prompt outlined in the main refactor plan is designed to detect these boundaries and is the ideal tool for this scenario.

3.  **Abandoned Conversations:** A customer asks a question but never replies to the agent's first response.
    *   **❓ Question:** How should this be handled? Should it be closed automatically after a certain time? What should its resolution status be?
    *   **Our Recommendation:** Close the case after the standard inactivity timeout (e.g., 48 hours) and assign it a status like "Abandoned."

---

## 3. 🛠️ Proposed Architecture: A Two-Option System

Based on our discussion, we will pivot from a "refactor" to an "expansion." We will implement a **two-option system** where the new case-based analysis exists in parallel with the original daily analysis system. This is a safer, additive approach that provides maximum flexibility.

### The Two Entry Points:

1.  **`POST /api/upload-json` (Existing Endpoint):**
    *   **Behavior:** This endpoint's functionality will **remain unchanged**.
    *   **Logic:** It will continue to parse conversations, group messages by day, and create `DailyAnalysis` records. The existing worker will process these jobs as it always has.
    *   **Result:** Provides the familiar daily-granularity metrics for existing dashboards.

2.  **`POST /api/upload-cases-json` (New Endpoint):**
    *   **Behavior:** This new endpoint will be the entry point for the intelligent case-based analysis.
    *   **Logic:**
        1.  It will receive a JSON file and pass the conversations to the new `services/case_detection_service.py`.
        2.  This service will use the AI-powered approach (guided by the client's answers to the questionnaire above) to identify case boundaries.
        3.  Instead of creating `DailyAnalysis` records, it will create records in the new `Case` and `CaseAnalysis` tables.
    *   **Result:** Provides a deep, end-to-end analysis of entire customer cases, exposed via new API endpoints (e.g., `/api/cases/*`).

This dual-system architecture allows the client to choose the desired analysis type at the time of upload and completely isolates the new feature from the existing, stable system.

---

## 4. 🗂️ Actionable Phased Task List

**Phase 1: Client & Project Alignment**
*   [ ] **Task:** Schedule a meeting with the client to review the "Questionnaire for the Client" section.
*   [ ] **Task:** Finalize the business rules for case identification based on client feedback.
*   [ ] **Task:** Update this document with the client's final decisions.

**Phase 2: Data Model Foundation (Additive)**
*   [ ] **Task:** Create a new branch for the feature (e.g., `feat/case-based-analysis`).
*   [ ] **Task:** Modify `models.py` to **add** the new `Case` and `CaseAnalysis` tables. **Do not remove** the existing `DailyAnalysis` model.
*   [ ] **Task:** Add new Pydantic schemas to `schemas.py` for the case-based API responses.
*   [ ] **Task:** Generate and review the Alembic migration script to add the new tables to the database.

**Phase 3: Core Logic Implementation**
*   [ ] **Task:** Create the new file `services/case_detection_service.py`.
*   [ ] **Task:** Implement the AI-powered detection logic based on the finalized client rules.
*   [ ] **Task:** Write comprehensive unit tests for the `CaseDetectionService`.

**Phase 4: New Pipeline and API**
*   [ ] **Task:** Create a new file `routes/cases.py` to house the new `POST /api/upload-cases-json` endpoint and any `GET` endpoints for retrieving case data.
*   [ ] **Task:** Implement the ingestion logic within the new endpoint to call the `CaseDetectionService` and create `CaseAnalysis` jobs.
*   [ ] **Task:** Update the `worker.py` to handle a new job type for processing `CaseAnalysis` records.
*   [ ] **Task:** Update `main.py` to include the new `cases` router.

**Phase 5: Verification**
*   [ ] **Task:** Create new end-to-end tests specifically for the `/api/upload-cases-json` endpoint.
*   [ ] **Task:** Run the full existing test suite to ensure the new code has not caused any regressions in the daily analysis system.
