## Responded Questions regarding the follow up for Backend Team

Contract clarifications

- Conversation transcript: Which endpoint returns the full message list for a chat? Can `GET /api/conversations/{chat_id}` include `messages: [...]` with fields { MESSAGE_CONTENT, DIRECTION, SOCIAL_CREATE_TIME, AGENT_USERNAME, AGENT_EMAIL }? If not, provide a dedicated `/messages` endpoint.
- Date filtering on conversations: Will `GET /api/conversations` support `start_date`/`end_date`? Our UI filters by date across charts and table.
- Field scales & units:
  - `satisfaction_score` in conversations: scale 0–10, correct? (UI shows "x/10").
  - `sentiment` (metrics): scale 0–10 (mean), correct?
  - `sentiment_distribution` values are fractions (0–1), not percentages, correct?
  - `avg_response_time` unit is minutes, correct?
  - `fcr` in conversations: boolean, correct? Any case where it’s numeric/score?
- Timezone & format: All date/time fields in UTC ISO (e.g., 2025-08-26T10:00:00Z)? For sentiment-trend, date is `YYYY-MM-DD`.
- Pagination limits: Max `page_size` supported? Total count always returned?
- Rate limits/errors: Expected 4xx/5xx and payload shapes for error responses; any 429 behavior we should surface?
- CORS/Auth: Will production require auth headers/tokens? If so, header names and token placement.
- Upload constraints: Max file size, expected grouped JSON format (field names), and strict validation rules.
- CSV export variants: Any `export_type` other than `conversations` we should plan for?

Data model alignment

- Pillar definitions: Are pillar weights stable as provided, or subject to change? If changing, can backend return weights in `/api/metrics` for display?
- Daily analysis mapping: For `/api/conversations/{chat_id}/daily`, can we expect consistent presence of all fields (effectiveness_score, effort_score, etc.)? Any nulls to handle?

---

## Backend Team Responses

### Contract Clarifications

-   **Conversation Transcript:** Great question. The main `/api/conversations/{chat_id}` endpoint provides an *aggregated summary* for the UI cards. To get the full message list, you will need to make a separate call to a new endpoint: `GET /api/conversations/{chat_id}/messages`. We will implement this endpoint to return the `messages` array exactly as you've specified.

-   **Date Filtering on Conversations:** No, the main `GET /api/conversations` endpoint currently does not support date filtering. The aggregation required is complex, and adding date filtering would be a significant performance hit. We recommend using the date filter on the `/api/metrics` and `/api/charts/*` endpoints and treating the conversation list as a general, non-date-filtered view.

-   **Field Scales & Units:**
    -   `satisfaction_score`: **Incorrect.** This score is on a **0–100** scale to align with the main CSI score on the dashboard. It is the aggregated daily CSI, scaled up.
    -   `sentiment` (in metrics): **Correct.** This is the mean sentiment score on a 0–10 scale.
    -   `sentiment_distribution`: **Correct.** The values are fractions between 0 and 1.
    -   `avg_response_time`: **Correct.** The unit is minutes.
    -   `fcr` in conversations: **Correct.** It is a boolean representing if First Contact Resolution was achieved on *any day* of the conversation.

-   **Timezone & Format:** **Correct.** All `datetime` fields are UTC ISO 8601 strings. All `date` fields (like in the sentiment trend) are `YYYY-MM-DD`.

-   **Pagination Limits:** The maximum `page_size` is **100**. The `total` count of conversations is always returned in the `/api/conversations` response body.

-   **Rate Limits/Errors:** Standard HTTP status codes are used. For a validation error (e.g., bad date format), you'll get a `400` or `422` with a `{"detail": "error message"}` payload. For server errors, you'll get a `500`. There is no user-facing rate limiting (`429`) on the API itself.

-   **CORS/Auth:** CORS is currently configured to allow all origins (`*`). There is **no authentication** required at this time.

-   **Upload Constraints:**
    -   Max file size: **50MB**.
    -   Format: A single JSON object where keys are `FB_CHAT_ID` strings and values are arrays of message objects.
    -   Required message fields: `MESSAGE_CONTENT` (string), `DIRECTION` (`to_company` or `to_client`), `SOCIAL_CREATE_TIME` (ISO 8601 string).

-   **CSV Export Variants:** Yes, the `GET /api/download` endpoint supports `export_type` query param with the following options: `conversations`, `messages`, and `all`.

### Data Model Alignment

-   **Pillar Definitions:** The pillar weights are stable for now but are defined in the backend's configuration. They are subject to change as we refine the model. We will add the current weights to the `GET /api/metrics` response so you can display them dynamically if desired.

-   **Daily Analysis Mapping:** You can expect all metric fields (`effectiveness_score`, etc.) to be consistently present in the `/api/conversations/{chat_id}/daily` response. However, their values can be `null` if the AI analysis fails for that specific day or if there isn't enough data to compute the metric (e.g., no agent response means `avg_response_time` will be `null`). Your UI should gracefully handle `null` values for any of the score fields.
