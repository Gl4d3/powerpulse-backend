# Backend expectations and frontend API contract

This document explains how the frontend API routes behave, what the external backend is expected to provide, and the data contracts used by the UI.

## Overview

- The frontend is a Next.js app with server API routes under `/app/api/**`.
- Some routes compute data locally (especially in development from seeded JSON files), while others proxy to an external backend.
- External backend base URL is configured in `lib/api-config.ts` as `http://localhost:8000`.
- When the backend is unavailable or returns empty data, routes provide safe, realistic fallbacks so the UI stays functional.

## Base URL and proxying

- `lib/api-config.ts` exposes:
  - `API_CONFIG.BASE_URL`: external backend base, default `http://localhost:8000`.
  - `API_CONFIG.ENDPOINTS`: relative paths (e.g., `/api/metrics`, `/api/download`, `/api/upload-json`).
- Helper `fetchFromBackend(endpoint, options)` composes `BASE_URL + endpoint` and returns JSON or throws on non-2xx.

Note: The value is hard-coded. To change the backend address, update `lib/api-config.ts` (or refactor to read from env if desired).

## Development data sources

Several API routes prefer local seed files when `NODE_ENV === 'development'`:

- `data/seeded_conversations.json` — grouped messages keyed by chat_id.
- `data/seeded_conversations_meta.json` — per-conversation metrics used for deterministic KPIs.

Meta entry schema (from `lib/aggregate-metrics.ts`):

```ts
interface MetaEntry {
  created_at: string
  sentiment_score?: number | null // 0–10
  satisfaction_score?: number | null // 0–10
  fcr?: boolean | null
  first_response_time_minutes?: number | null
  average_response_time_minutes?: number | null
  topics?: string[]
}
```

If seeds are missing, routes fall back to smaller local files (e.g., `data/snippet.json`, `data/grouped_chats.json`) or to the external backend.

## API routes and contracts

### GET /api/metrics

- Query params: `start_date`, `end_date` (ISO `yyyy-MM-dd` strings).
- In development: aggregates KPIs from `seeded_conversations_meta.json` and computes CSI + deltas (previous period inferred by range length).
- Otherwise: proxies to backend `${BASE_URL}/api/metrics` with the same query params.
- If backend returns empty or errors: returns realistic mock KPIs and computes CSI locally.

Response fields (server-preferred contract; all numbers unless stated):

- Core KPIs
  - `sentiment` (0–10, mean)
  - `csat_percentage` (0–100)
  - `fcr_percentage` (0–100)
  - `avg_response_time` (minutes)
  - `sentiment_distribution`: `{ positive: number, neutral: number, negative: number }` (fractions 0–1)
  - `topic_frequency`: `Array<{ topic: string; frequency: number }>`
- CSI and pillars (0–100)
  - `csi`
  - `resolution_quality`
  - `service_timeliness`
  - `customer_ease`
  - `interaction_quality`
  - `sample_count` (integer)
  - `deltas` (optional): `{ csi, resolution_quality, service_timeliness, customer_ease, interaction_quality }` (differences vs previous period)

Backend flexibility: If the backend provides only minimal fields (e.g., no `csi`/pillars), the frontend normalizes/enriches and computes CSI. Providing the CSI contract above is recommended to avoid drift.

Client usage: `lib/metrics-context.tsx` reads these fields, prefers `json.csi` and `json.deltas.csi`, and has graceful fallbacks (including deterministic client computation via `computeCSI`).

---

### GET /api/charts/sentiment-trend

- Query params: `start_date`, `end_date`.
- Dev behavior: computes daily average sentiment from `seeded_conversations_meta.json` over the requested range or last 30 days by default.
- Fallback: generates a synthetic 30-day trend.

Response: `Array<{ date: string (yyyy-MM-dd), sentiment: number | null }>`

---

### GET /api/charts/sentiment-distribution

- Returns a mock distribution in three buckets.
- Response: `Array<{ sentiment: "Positive" | "Neutral" | "Negative", count: number, percentage: number }>`

---

### GET /api/charts/topic-frequency

- Returns a mock set of most frequent topics.
- Response: `Array<{ topic: string, frequency: number }>`

---

### GET /api/conversations

- Query params:
  - `page` (default `1`)
  - `page_size` (default `10`)
  - `start_date`, `end_date` (accepted but not yet applied to filtering in the current implementation)
- Dev behavior: builds conversation summaries from `seeded_conversations.json` and aligns scores/topics/timestamps with `seeded_conversations_meta.json` when available for consistency. Fallback to `data/snippet.json`.
- Pagination is applied after building the summary list.

Response shape:

```json
{
  conversations: Array<{
    chat_id: string
    sentiment_score: number | null
    satisfaction_score: number | null
    fcr?: boolean
    topics: string[]
    created_at: string
    agent_username?: string
    agent_email?: string
    ai_summary?: string
  }>,
  total: number,
  page: number,
  page_size: number,
  total_pages: number
}
```

Note: Date filtering is planned; until implemented, the API accepts `start_date`/`end_date` but does not filter.

---

### GET /api/conversations/[id]

- Path param: `id` (chat_id).
- Dev behavior: loads the message array for the given `id` from `seeded_conversations.json` (or `grouped_chats.json`) and augments with scores from meta when available. If local read fails, proxies to backend `${BASE_URL}/api/conversations/{id}`.
- Topics are derived deterministically if not present to keep the UI stable.

Response shape:

```ts
{
  chat_id: string,
  messages: Array<{
    MESSAGE_CONTENT: string | null,
    DIRECTION: "to_company" | "to_client",
    SOCIAL_CREATE_TIME?: string,
    AGENT_USERNAME?: string,
    AGENT_EMAIL?: string
  }>,
  sentiment_score: number,
  satisfaction_score: number,
  fcr?: boolean,
  topics: string[],
  gpt_insights?: {
    summary?: string,
    key_points?: string[],
    suggested_actions?: string[],
    resolution_status?: string
  },
  created_at: string,
  updated_at: string
}
```

Client normalization: If the backend returns a raw `messages` array (without wrapper fields), the UI normalizes it into the above shape with defaults.

---

### GET /api/download

- Query params: `export_type` (default `conversations`).
- Proxies to backend `${BASE_URL}/api/download?export_type=...`.
- Returns `text/csv` with appropriate `Content-Disposition` header for download.

---

### POST /api/upload-json

- Accepts `multipart/form-data` with fields:
  - `file`: the uploaded JSON file (grouped messages format: map of `FB_CHAT_ID` to array of messages)
  - `force_reprocess` (optional, boolean; default `false`)
- Proxies to backend `${BASE_URL}/api/upload-json` and forwards the form data unchanged.

Backend is expected to handle size limits, parse the grouped format, and process or cache results according to `force_reprocess`.

---

### GET /api/agents

- Returns a mocked list of agents (local only; no backend dependency). Useful for UI demos.

Response: `Array<{ id: string, name: string, email: string }>`

## Backend expectations summary

The external backend (default `http://localhost:8000`) should ideally provide:

- `GET /api/metrics` supporting `start_date`/`end_date` and returning the CSI contract (recommended):
  - `csi`, `resolution_quality`, `service_timeliness`, `customer_ease`, `interaction_quality`, `sample_count`, optional `deltas`.
  - Core KPIs: `sentiment`, `csat_percentage`, `fcr_percentage`, `avg_response_time`, `sentiment_distribution`, `topic_frequency`.
- `GET /api/conversations` (optional for now; frontend currently serves locally) with pagination and optional date filtering.
- `GET /api/conversations/{id}` returning either the detailed wrapper object above or at least a `messages` array (the client normalizes both).
- `GET /api/download?export_type=...` returning CSV text.
- `POST /api/upload-json` receiving `multipart/form-data` (`file`, `force_reprocess`).

Graceful degradation: If `GET /api/metrics` returns a minimal payload, the UI computes CSI on the client; for errors, the UI shows fallbacks/skeletons.

## Error handling & timeouts

- All routes catch and log errors, responding with `500` JSON `{ error: string }` on failure.
- Charts and context fetches use abortable requests to avoid race conditions when filters or date ranges change.
- Client components display skeletons and lightweight error states.

## Notes for contributors

- If you add filtering to `/api/conversations`, follow the `start_date`/`end_date` convention used elsewhere and filter by `created_at`.
- If you change pillar names/weights, update both the backend response and `lib/metrics-context.tsx` to keep normalization consistent.
- Consider moving `API_CONFIG.BASE_URL` to an environment variable for deployments.

{
      "daily_analysis_id": 20,
      "sentiment_score": 5,
      "sentiment_shift": 0,
      "resolution_achieved": 5,
      "fcr_score": 5,
      "ces": 4,
      "first_response_time": null,
      "avg_response_time": null,
      "total_handling_time": null,
      "error": "analysis_failed"
}