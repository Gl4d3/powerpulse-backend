# Plan: docs & schema tracking (template)

Use this file (or create a `docs/plan-{short-name}.md`) for any medium/long-running work that affects schema, config, or pipeline semantics. Keep entries short and append-only.

## Title: docs & schema tracking template

- Owner: <your-name>
- Created: 2025-08-20
- Purpose: track schema/config changes, migration notes, test status, and small task checklists

---

## Schema snapshot (append each time models.py or schemas.py change)

### 2025-08-20 - initial snapshot
- Source: `models.py` and `schemas.py`
- Note: default SQLite, core models: Conversation, Message, ProcessedChat, Metric
- Actions: none

## Change log (append entries here)

### [UNREGISTERED] 2025-08-20 - plan created
- Added tracking policy and initial snapshot

## Current tasks
- [ ] Add automated schema-diff tool or script to generate snapshots
- [ ] Add migration notes when altering `models.py`
- [ ] Keep `repository_lifecycle.md` updated with pipeline/semantic changes

## Migration notes (template)
- When changing a model column name or type:
  - Add new column with nullable default
  - Backfill data in a short-lived migration
  - Swap code to write/read new column
  - Remove old column after one release cycle

## Testing notes
- Minimal smoke test (manual): upload `tests/fixtures/sample_conversations.json` through the upload endpoint and confirm DB rows and metrics
- Unit tests: add/modify tests under `tests/unit` for any code that touches schema
- Integration tests: add tests under `tests/integration` for end-to-end verification

## Notes & decisions
- All schema-related changes must be recorded here before merging PRs that modify `models.py` or `schemas.py`.
- For quick fixes, create a new plan file `docs/plan-{short-name}.md` and reference it in the PR description.

---

Append more entries below as work progresses.
