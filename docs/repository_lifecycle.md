## PowerPulse — Repository lifecycle & status

This document describes the runtime lifecycle of the PowerPulse backend, maps pipeline stages to repository files, records the current status expectations, and defines an ongoing documentation and schema/config tracking policy.

### High-level lifecycle (canonical)
1. File upload → JSON processing begins (validation, size check, dedupe)
2. Job Batching → Conversations are grouped into token-limited jobs for batch processing.
3. AI analysis → Gemini / GPT analyzes conversation jobs for sentiment, satisfaction, FCR.
4. Database storage → Conversation, Message and ProcessedChat rows written. Job statuses are updated.
5. Metrics calculation → Aggregated metrics (CSAT, FCR, response time, sentiment).
6. Cache update → Metric rows / Metric cache updated for fast reads.
7. Database commit → All changes persisted; progress tracker updated.

These stages correspond to code in the repository. Follow this lifecycle when debugging, testing or adding features.

### Files & responsibilities (map to lifecycle)
- Upload & routing: `routes/upload.py`, `routes/export.py` (upload endpoints, export)
- File processing: `services/file_service.py`, `services/file_service_optimized.py`, `services/file_service_backup.py`
- Job Management: `services/batch_service.py`, `services/job_service.py` (batching, queueing, and execution)
- AI adapters: `services/gpt_service.py`, `services/gpt_service_optimized.py`, `services/gemini_service.py`
- Progress and orchestration: `services/progress_tracker.py`, `routes/progress.py`
- Persistence & schema: `models.py`, `database.py`, `schemas.py`
- Analytics & metrics: `services/analytics_service.py`, `routes/metrics.py`
- App entrypoint: `main.py`, config: `config.py`

### Contract: pipeline inputs / outputs / error modes
- Inputs: uploaded JSON file in grouped_chats format (FB_CHAT_ID -> message list). See `README.md` for expected keys.
- Outputs: persisted `Conversation`, `Message`, `ProcessedChat` records and cached `Metric` rows; CSV export if requested.
- Error modes: AI API failures (rate limit / auth), malformed JSON, DB integrity errors (unique constraints), and transient network errors.

### Data shapes & important fields (summary)
- Message: FB_CHAT_ID, MESSAGE_CONTENT, DIRECTION (to_company/to_client), SOCIAL_CREATE_TIME, AGENT_USERNAME, AGENT_EMAIL
- Conversation: chat_id, first_message_time, last_message_time, message_count, avg_response_time_minutes, sentiment_score, satisfaction_score, first_contact_resolution
- ProcessedChat: fb_chat_id, upload_id, processed_at, ai_version

### Important environment/config variables to monitor
- `AI_SERVICE` ("gemini" or "openai") — selected AI backend
- `GEMINI_API_KEY`, `OPENAI_API_KEY` — credentials used by adapters
- `DATABASE_URL` — connection string (default sqlite:///./powerpulse.db)
- `MAX_FILE_SIZE` — upload guardrail (default 50MB)
- `MAX_TOKENS_PER_JOB` — The maximum number of tokens allowed in a single AI analysis job.
- `AI_CONCURRENCY` - The maximum number of concurrent requests to the AI service.

### Schema & config tracking policy (strict stage)
From this point forward we keep a strict, constant check on schema and persistent configuration. Implement these rules every time you change code, add features, or run tests:

1. Always inspect `models.py` and `schemas.py` for changes. If you change a model, add a short "schema snapshot" entry to the plan file (`docs/plan-docs-tracking.md`) with the diff and migration notes.
2. When changing environment-dependent behavior (AI_SERVICE, keys, DB URL, MAX_FILE_SIZE), update `config.py` and append the new settings and rationale to the plan file.
3. For any DB-affecting change, list the forward/backward compatibility impact and a brief migration plan in the plan file.
4. The docs file (`repository_lifecycle.md`) is the canonical runtime description and must be updated with any pipeline changes.

### Minimal QA / quality gates before merge
- Build / typecheck: run project's checks (Python 3.11 target). Confirm no syntax errors.
- Run unit tests: `pytest tests/unit/` (fast tests) → target 90% for unit coverage.
- Run integration tests: `pytest tests/integration/` (end-to-end path)
- Smoke test the pipeline: upload a small sample and verify DB rows and metrics.

### Edge cases to check in pipeline
- Autoresponse noise (e.g., strings like "*977#") — filtered during preprocessing
- Duplicate FB_CHAT_ID uploads — `ProcessedChat` prevents reprocessing unless forced
- Missing agent fields or null timestamps — skip/normalize; conversation-level fallbacks
- AI API quota / rate limits — exponential backoff and graceful fallback values. Now managed by the job queue.

### How to use this document
- Read before modifying services that touch processing, AI, or DB.
- Follow the schema/config policy above on every PR.
- When starting a longer project, create a plan file named `docs/plan-{short-name}.md` (examples below) and update it frequently.

### Example plan file names
- For analytics improvements: `docs/plan-analytics.md`
- For schema or DB change: `docs/plan-schema.md`
- For long-running refactor: `docs/plan-refactor-file-service.md`

---

Current status snapshot (date: 2025-08-20):
- AI service: Gemini support added; selection via `AI_SERVICE`.
- Processing: optimized batched processing implemented in `services/file_service_optimized.py`.
- Tests: testing harness and pytest config present under `tests/` and `run_tests.py`.
- DB: SQLite default; models in `models.py`.

Keep this file short and update it with changes to the pipeline stages or major design decisions.

## Quick checklists (for daily use)
- [ ] Did I check `models.py` and `schemas.py` for required changes?
- [ ] Did I append schema/config changes to a plan file under `docs/`?
- [ ] Did I update `repository_lifecycle.md` if the pipeline semantics changed?