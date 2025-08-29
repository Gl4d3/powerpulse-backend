# Plan: Fix API Rate Limit Issue

**Owner:** Gemini
**Created:** 2025-08-29
**Purpose:** To fix the root cause of the Google API key suspension by reducing the application's request concurrency to comply with the API's rate limits.

---

## 1. Phased Execution Plan

### Phase 1: Code Correction (In Progress)
- [ ] **Reduce `AI_CONCURRENCY`:**
    - [ ] In `config.py`, lower the `AI_CONCURRENCY` setting from `50` to a safe value of `2`.
- [ ] **Add Intelligent Delay:**
    - [ ] In `services/job_service.py`, add a small `asyncio.sleep(1)` in the main job processing loop to ensure requests are spaced out.

### Phase 2: API Key Reactivation
- [ ] **Contact Google Support:**
    - [ ] The user will need to contact Google Cloud support regarding the suspended API key.
- [ ] **Provide Explanation:**
    - [ ] Inform them that an application bug was causing unintentional rate-limiting violations and that the issue has been identified and fixed.

---
