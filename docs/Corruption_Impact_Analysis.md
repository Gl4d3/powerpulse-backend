# Corruption Impact Analysis

## 1. Introduction and Root Cause

This document details the system-wide impact of a critical bug in the data ingestion logic found in `services/file_service_optimized.py`. 

The root cause was that if a `DailyAnalysis` record for a specific conversation and date already existed, the service would discard any new messages for that same day from subsequent file uploads. This created "orphaned" `DailyAnalysis` records that were disconnected from their underlying message data, leading to widespread data inconsistency.

## 2. Affected Endpoints and Impact Assessment

The following is a list of all API endpoints that consume data from the `daily_analyses` table and an analysis of how their responses were compromised.

### `GET /api/explorer/analyses`

-   **How it was affected (Most Severe):** This endpoint was the most directly impacted. Its primary function is to fetch `DailyAnalysis` records and then link them back to the messages that occurred on that specific day.
-   **Impact on Metrics:** When the endpoint encountered an orphaned `DailyAnalysis` record, its query to find matching messages would fail. This resulted in the response you saw:
    -   `total_messages`, `customer_messages`, and `agent_messages` were always `0`.
    -   The `analysis_date` appeared irrelevant because it did not match any of the actual message timestamps for that conversation.

### `GET /api/charts/csi-trend` and other Trend Endpoints

-   **How it was affected:** These endpoints query the `daily_analyses` table and `GROUP BY analysis_date` to calculate average scores over time.
-   **Impact on Metrics:** These endpoints produced **misleading trend charts**. They would correctly calculate an average CSI score for the orphaned records, but they would group all of them under the *incorrect* `analysis_date`. This would create false spikes or dips on dates that had no actual relation to the underlying data, making all time-series analysis unreliable.

### `GET /api/metrics`

-   **How it was affected:** This endpoint calculates system-wide averages for all metrics by querying the `daily_analyses` table.
-   **Impact on Metrics:** The overall aggregate scores were skewed. The orphaned records, with their own CSI and pillar scores, were included in the global average, pulling it up or down inaccurately. The `sample_count` was also inflated by including these invalid records.

### `GET /api/conversations`

-   **How it was affected:** This endpoint calculates the lifetime average metrics for each conversation by aggregating all of its associated `DailyAnalysis` records.
-   **Impact on Metrics:** The lifetime averages for any conversation with orphaned analysis records were incorrect. The scores from the orphaned records were factored into the average, corrupting the summary for that entire conversation.

### `GET /api/charts/topic-frequency` & `GET /api/charts/sentiment-distribution`

-   **How it was affected:** These endpoints query `daily_analyses` records, often within a specific date range.
-   **Impact on Metrics:** The results were polluted. A query for a specific date range could incorrectly include orphaned records that were mis-dated to fall within that range. This would skew the topic and sentiment data with information from conversations that did not actually happen during the queried period.

## 3. Conclusion

The ingestion bug created a silent data corruption that compromised the integrity of every single endpoint that relies on daily analytical data. The only way to ensure trustworthy metrics across the entire platform was to fix the ingestion logic and re-process the source data on a clean slate to guarantee the link between a `DailyAnalysis` summary and its underlying `Message` data is never broken.
