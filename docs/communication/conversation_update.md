# API Update: The `/api/conversations` Endpoint Has Been Modernized

Hi Team,

This is an announcement regarding an important update to the `GET /api/conversations` and `GET /api/conversations/{chat_id}` endpoints.

To align with our modern analytics structure, we have replaced the legacy metrics in the response object with the more detailed and accurate four-pillar scores.

## What's Changed?

The following fields have been **removed** from the `ConversationResponse` object:

-   `avg_sentiment_score`
-   `fcr`

The following fields have been **added**:

-   `avg_csi_score` (this remains)
-   `avg_effectiveness_score`
-   `avg_efficiency_score`
-   `avg_effort_score`
-   `avg_empathy_score`

## Reason for Change

This change brings the conversations summary in line with the rest of our analytics, which are based on the four pillars of customer satisfaction. This provides a more nuanced and accurate view of conversation performance.

## Action Required

Please update any UI components that consume these endpoints to use the new fields. You should now display the four pillar score averages instead of the legacy sentiment and FCR metrics.

## Example Response

### Before:

```json
{
  "chat_id": "12345",
  "username": "John Doe",
  "avg_sentiment_score": 8.5,
  "avg_csi_score": 78.5,
  "fcr": true,
  "topics": ["billing", "outage"],
  "..."
}
```

### After:

```json
{
  "chat_id": "12345",
  "username": "John Doe",
  "avg_csi_score": 78.5,
  "avg_effectiveness_score": 8.2,
  "avg_efficiency_score": 7.5,
  "avg_effort_score": 8.8,
  "avg_empathy_score": 6.9,
  "topics": ["billing", "outage"],
  "..."
}
```

Thanks!
