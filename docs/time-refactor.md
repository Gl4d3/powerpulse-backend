# Urgent Workaround: Explorer Endpoint (`/api/explorer/analyses`)

**Date:** 2025-09-09
**Purpose:** This document outlines a temporary, urgent workaround applied to the `/api/explorer/analyses` endpoint to ensure a cleaner first page of results for a presentation. This is NOT a long-term solution and will be reverted/properly implemented as part of the main revamp plan.

## Changes Implemented (Temporary Workaround)

Modifications have been made to the `get_daily_analyses_with_details` function in `services/analytics_service.py`. These changes **only apply when `page=1`** in the API request.

1.  **Filtering for Non-Null Pillars:** The query now filters results to include only `DailyAnalysis` records where all four core pillars (`effectiveness_score`, `effort_score`, `efficiency_score`, `empathy_score`) are not null.
2.  **Filtering for Non-Null Handling Time:** The query further filters results to include only records where `total_handling_time` is not null.
3.  **Ordering by Message Count:** The results for the first page are now ordered by `total_messages` in descending order.

## Impact

-   The first page of results from `/api/explorer/analyses` will now prioritize records that have complete pillar data and handling time, and will be sorted by the number of messages.
-   This workaround does **not** fix the underlying issue of potentially null time metrics or incorrect dates for `DailyAnalysis` records. It merely filters and orders the first page to present a cleaner view.
-   This workaround does **not** affect any other pages of results or other API endpoints.

## Future Plan

This workaround will be removed once the comprehensive plan to fix the time metrics calculation and persistence (Phase 1 of the main revamp plan) is fully implemented and verified. The dynamic ordering feature will also be properly implemented as part of Phase 2 of the main revamp plan.
