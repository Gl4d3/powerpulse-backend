## Responding to Frontend API Audit & Path Forward

**Audience:** Frontend Team
**From:** Backend Team
**Date:** 2025-09-05

---

Hi Frontend Team,

Thank you for this incredibly detailed and helpful API audit. Your findings are spot on, and the confusion is entirely understandable. The backend has been in a state of transition as we moved from an older, simpler metric system to the new, daily-granularity CSI model. Your audit has correctly identified the exact points of friction caused by this transition.

Let us provide a clear explanation for the issues you're seeing and propose a definitive path forward that will resolve these inconsistencies.

### The Core Issue: Two Competing Data Models

The root cause of the strange data (like missing CSI scores and old dates) is that two different data models currently co-exist in the backend:

1.  **Legacy Model (Deprecated):** The original system calculated a single `sentiment_score` and `satisfaction_score` and stored them directly on the main `Conversation` database object. The data you are seeing from August 22nd is likely the only data that was ever processed using this old system.

2.  **New CSI Model (Current):** The new system is far more detailed. It creates a `DailyAnalysis` record for *every day* a conversation is active. It stores the nine micro-metrics, the four CSI pillars, and the final `csi_score` on these daily records. **This is the source of truth for all current and future analytics.**

The `GET /api/conversations` endpoint is currently broken because it was attempting to stitch together data from both models, leading to the confusing results you observed.

---

### Answering Your Questions

Let's address your specific questions with this context in mind:

**1. Are `/api/explorer/*` endpoints available? We need them for the daily analysis table view.**

> **Yes, absolutely.** The `GET /api/explorer/analyses` endpoint is the new, correct, and stable endpoint you should use. It was designed specifically for the main table view you're building. It provides direct, paginated access to the `DailyAnalysis` records.

**2. Is `/api/conversations/{chat_id}/daily` working? We're getting 404s.**

> You are correct, it is not working. Our investigation confirms this endpoint was documented but **never implemented**. This was an oversight in our documentation. The correct, working endpoint for getting the transcript for a single day's analysis is `GET /api/explorer/transcript/{daily_analysis_id}`.

**3. Should we be using `/api/explorer/analyses` instead of `/api/conversations` for the main table?**

> **Yes. For your immediate needs, please switch to `GET /api/explorer/analyses`.** This will unblock you and give you the clean, daily-granularity data you expect. Think of `/explorer` as the primary source for any view that shows a list of daily records.

**4. Is `/api/agents` deprecated or should it be documented?**

> Our investigation shows this endpoint **does not exist** in the current backend codebase. It is likely a remnant from a very old version. We recommend removing any calls to `/api/agents` from the frontend.

---

### The Path Forward

To permanently fix these issues, the backend team will execute the following strategic plan:

**Phase 1: Full Deprecation of Legacy Metrics (Backend Task)**
*   We will completely remove the code that calculates the old `sentiment_score` and `satisfaction_score`.
*   We will create a database migration to drop these legacy columns from the `conversations` table, cleaning up the schema for good.

**Phase 2: Fix and Redefine `/api/conversations` (Backend Task)**
*   We will refactor the `GET /api/conversations` endpoint. Its new purpose will be to provide a **high-level summary of entire conversations**. Instead of showing daily data, each item it returns will represent one conversation, with the CSI scores correctly averaged from all of its associated daily analyses.
*   This will make it the perfect endpoint for a future dashboard view like "All Conversations" or "Agent Performance Overview".

**Phase 3: Documentation Overhaul (Backend Task)**
*   We will update the API documentation to reflect all these changes, clearly defining the purpose of `/conversations` (aggregated summaries) vs. `/explorer` (granular daily data).

### Your Next Steps (Frontend)

1.  **Switch to the Explorer API:** For your main data table, please switch your data fetching to use `GET /api/explorer/analyses`.
2.  **Use Explorer for Transcripts:** For drilling down to see a day's messages, please use `GET /api/explorer/transcript/{daily_analysis_id}`.
3.  **Remove Agent Endpoint:** Please remove any code that calls the non-existent `/api/agents` endpoint.

We believe this plan will resolve the current errors, unblock your development, and create a much more logical and consistent API for us to build upon. Thank you again for bringing this to our attention with such clarity.

Best,

The Backend Team
Gemini 2.5 Flash-Lite	15	250,000	1,000
