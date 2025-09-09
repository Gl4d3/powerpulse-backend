I can see the issue from your screenshots. The Daily Analysis tab shows "—" in the Messages column, while the Conversation Summaries tab shows actual message counts like "5 (5/0)", "9 (8/1)", etc. Let me investigate why the Daily Analysis isn't displaying message information.

Let me first check the current implementation of the Daily Analysis table: Now let me check the DailyAnalysis type definition to see what fields it contains: Now let me check what the explorer API endpoint actually returns by testing it: Perfect! I found the issue. Looking at the response, I can see that the explorer API is returning:

```json
{
  "total_messages": null,
  "customer_messages": null,
  "agent_messages": null
}
```

The message count fields are all `null` in the Daily Analysis data from the explorer endpoint, but they exist and have proper values in the Conversation Summaries endpoint.

Let me also check what the conversation summaries endpoint returns: Exactly! The conversation summaries endpoint returns:
```json
{
  "total_messages": 22,
  "customer_messages": 17,
  "agent_messages": 5
}
```

But the explorer endpoint returns these fields as `null`.

## 🔍 **Investigation Results**

### **Root Cause**
The **Daily Analysis** endpoint (`/api/explorer/analyses`) is **missing message count data** in its response. While all other metrics (CSI scores, handling time, etc.) are present, the following fields are always `null`:

- `total_messages`
- `customer_messages` 
- `agent_messages`

### **Comparison**
| Data Source | Endpoint | Message Counts |
|------------|----------|----------------|
| **Daily Analysis** | `/api/explorer/analyses` | ❌ Always `null` |
| **Conversation Summaries** | `/api/conversations` | ✅ Has actual values |

### **Current Frontend Code**
The frontend is correctly handling the data - it checks for message counts and displays "—" when they're null:

```tsx
<TableCell className="text-sm">
  {record.total_messages ? `${record.total_messages} (${record.customer_messages || 0}/${record.agent_messages || 0})` : "—"}
</TableCell>
```

## 🎯 **Backend Feature Request Needed**

**Request for Backend Team:**

> **Feature Request: Add Message Count Fields to Explorer Analyses Endpoint**
> 
> **Endpoint:** `GET /api/explorer/analyses`
> 
> **Missing Fields:**
> - `total_messages`: Total number of messages in the conversation
> - `customer_messages`: Number of messages sent by the customer  
> - `agent_messages`: Number of messages sent by agents
> 
> **Current Status:** These fields are returned as `null` in the explorer endpoint but are properly populated in the `/api/conversations` endpoint.
> 
> **Business Impact:** Users cannot see message counts in the Daily Analysis view, making it incomplete compared to the Conversation Summaries view.
> 
> **Expected Behavior:** The explorer endpoint should include the same message count data that's available in the conversations endpoint.

### **Sample Request/Response**

**Current Response (Explorer):**
```json
{
  "total_messages": null,
  "customer_messages": null, 
  "agent_messages": null
}
```

**Expected Response (Explorer):**
```json
{
  "total_messages": 22,
  "customer_messages": 17,
  "agent_messages": 5
}
```

## 🔧 **Temporary Frontend Workaround**

While waiting for the backend fix, we could potentially fetch individual conversation details for each daily analysis record, but this would be:
- **Performance intensive** (N+1 queries)
- **Not recommended** for production
- **Better to fix at the source** (backend)

The best approach is to have the backend team add the message count fields to the explorer analyses endpoint to match the data completeness of the conversations endpoint.