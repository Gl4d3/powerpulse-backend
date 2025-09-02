# PowerPulse Analytics Gemini Context (CSI Refactor v2.0)

This Markdown file serves as the primary context for the PowerPulse Analytics backend, providing persistent instructions for AI-driven analysis and CSI calculation. It loads hierarchically (global > project > local) to customize behavior for chat log processing. Use this as a system prompt or reference for Gemini CLI integrations, tailoring outputs to utility-sector CX metrics.

For API details, see **[`docs/API_DOCUMENTATION.md`](./docs/API_DOCUMENTATION.md)**—the source of truth for endpoints and samples.

## Overview and Instructions
PowerPulse Analytics is a FastAPI backend for analyzing customer service chats in utilities like Kenya Power. It refactors CSI around four pillars derived from research: 
1. **Empathy/Interaction Quality** (How the interaction made the customer feel; weight: 15%—lowest correlation at 0.6-0.8, but enhances emotional insights).
2. **Effectiveness/Resolution Quality** (Was the issue solved; weight: 35%—highest rank with 0.8-1.0 correlation to satisfaction).
3. **Effort/Customer Ease** (How easy was resolution; weight: 25%—strong 0.7-0.92 link to retention).
4. **Efficiency/Service Timeliness** (How fast/streamlined; weight: 25%—0.6-0.7 correlation, threshold-sensitive).

CSI = Σ (Pillar Score × Weight), normalized to 100. Sub-metrics feed pillars via averages (e.g., FCR and resolution for Effectiveness). Prioritize Effectiveness for utilities; test weights with regression on your data for optimization.

## Data Flow and Processing
1. **Upload**: POST /api/upload-json ingests JSON chats.
2. **Parsing**: Group by FB_CHAT_ID, clean content.
3. **AI Extraction**: Use Gemini API with prompt: "Analyze chat for: sentiment_score (0-10), sentiment_shift (-5 to +5), resolution_achieved (0-10), fcr_score (0-10 if single interaction), ces (1-7, lower better), first_response_time (seconds), avg_response_time (seconds), total_handling_time (minutes)."
4. **Storage**: Save raw + micro-metrics in SQLite Conversation table.
5. **Pillar Calculation**: Effectiveness = avg(resolution, FCR); Effort = CES (inverted); Efficiency = avg(times, inverted); Empathy = avg(sentiment, shift).
6. **CSI Aggregation**: Weighted sum per chat, then global average.
7. **Caching/Export**: Aggregate for dashboards; CSV includes all levels.

## Pillar Deep Dive and Rankings
Pillars ranked by satisfaction correlation (from meta-analyses):
- **Effectiveness (Rank 1, 35% weight)**: Sub-metrics: resolution_achieved (issue solved?), fcr_score (one-contact fix?). Benchmarks: 70-80% FCR for 15% CSAT boost.
- **Effort (Rank 2, 25% weight)**: Sub-metric: ces (effort level). Low CES (<3) predicts 92% retention.
- **Efficiency (Rank 3, 25% weight)**: Sub-metrics: first_response_time, avg_response_time, total_handling_time. Threshold: <4 hours for 80% satisfaction.
- **Empathy (Rank 4, 15% weight)**: Sub-metrics: sentiment_score, sentiment_shift. Positive shifts uplift CSAT by 10-20%.

Adjust weights if data shows variants (e.g., +5% to Effort for loyalty focus).

## Code Structure
- **models.py**: Add columns for all sub-metrics and pillars.
- **schemas.py**: Expand responses to include micro/macro.
- **routes/**: Update metrics/conversations/export for new fields.
- **services/gemini_service.py**: Prompt engineering for JSON output.
- **services/analytics_service.py**: Weighted calculations; e.g., `csi = (effectiveness * 0.35) + (effort * 0.25) + ...`

## Examples
- Prompt Example: "From chat: [transcript]. Score resolution_achieved (0-10 if solved), etc."
- CSI Calc: For scores 8 (Effectiveness), 7 (Effort), 9 (Efficiency), 6 (Empathy): CSI = 79.

Update this file for custom contexts in Gemini CLI.