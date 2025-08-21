# PowerPulse Analytics

A production-ready customer satisfaction analytics backend built with FastAPI that processes Facebook Direct Messages to generate business intelligence metrics using **Google Gemini AI** for sentiment analysis.

## Features

### ✅ Core Analytics
- **Sentiment Analysis**: AI-powered analysis of customer messages using **Google Gemini 1.5 Flash**
- **CSAT Calculation**: Customer satisfaction percentage tracking
- **FCR Metrics**: First Contact Resolution rate analysis  
- **Response Time Analytics**: Agent response time tracking and averages
- **Topic Extraction**: Automatic identification of conversation topics

### ✅ Production Enhancements
- **Autoresponse Filtering**: Automatically filters out messages containing "*977#"
- **Date Range Filtering**: Support for start_date/end_date parameters in API endpoints
- **AI Processing Cache**: Prevents reprocessing with ProcessedChat tracking
- **Retry Logic**: Exponential backoff for AI API failures (max 2 retries)
- **Force Reprocess**: Optional reanalysis of previously processed conversations
- **Multi-AI Support**: Switch between Google Gemini and OpenAI GPT

### ✅ API Endpoints
- `POST /api/upload-json` - Upload Facebook chat JSON files
- `GET /api/metrics` - Business intelligence dashboard metrics  
- `GET /api/conversations` - Paginated conversation list with filtering
- `GET /api/conversations/{chat_id}` - Individual conversation details
- `GET /api/download` - CSV export functionality

### ✅ Data Processing
- **JSON Format**: Processes grouped_chats format (FB_CHAT_ID as key, message arrays as values)
- **Message Validation**: Filters invalid messages and autoresponses
- **Batch Processing**: Efficient AI API usage through batched requests
- **Database Persistence**: SQLite with PostgreSQL compatibility

## Quick Start

### Using Python directly:
```bash
# Install dependencies
pip install -r requirements.txt

# Set AI service configuration
export GEMINI_API_KEY="your-gemini-key-here"  # Recommended
export AI_SERVICE="gemini"  # or "openai" for GPT

# Run the server
python main.py
```

### Using Docker:
```bash
# Build and run
docker-compose up --build

# Or build manually
docker build -t powerpulse-analytics .
docker run -p 8000:8000 -e GEMINI_API_KEY="your-key" powerpulse-analytics
```

## AI Service Configuration

### Google Gemini (Recommended)
- **Model**: Gemini 1.5 Flash
- **Benefits**: Generous free tier, fast performance, no quota issues
- **Setup**: Set `GEMINI_API_KEY` and `AI_SERVICE="gemini"`

### OpenAI GPT (Alternative)
- **Model**: GPT-4o-mini
- **Benefits**: High accuracy, extensive training data
- **Setup**: Set `OPENAI_API_KEY` and `AI_SERVICE="openai"`

## API Usage Examples

### Upload Facebook chat data:
```bash
curl -X POST "http://localhost:8000/api/upload-json" \
  -F "file=@grouped_chats.json" \
  -F "force_reprocess=false"
```

### Get metrics with date filtering:
```bash
curl "http://localhost:8000/api/metrics?start_date=2025-08-12&end_date=2025-08-13"
```

### Get conversations with filtering:
```bash
curl "http://localhost:8000/api/conversations?satisfied_only=true&page_size=10"
```

### Export data to CSV:
```bash
curl "http://localhost:8000/api/download?export_type=conversations" -o export.csv
```

## Data Format

Expected JSON format for uploads:
```json
{
  "FB_CHAT_ID_1": [
    {
      "FB_CHAT_ID": "FB_CHAT_ID_1",
      "MESSAGE_CONTENT": "Customer message content",
      "DIRECTION": "to_company",
      "SOCIAL_CREATE_TIME": "2025-08-12T10:00:00.000Z",
      "AGENT_USERNAME": null,
      "AGENT_EMAIL": null
    },
    {
      "MESSAGE_CONTENT": "Agent response",
      "DIRECTION": "to_client",
      "SOCIAL_CREATE_TIME": "2025-08-12T10:02:00.000Z",
      "AGENT_USERNAME": "AGENT_ID",
      "AGENT_EMAIL": "agent@company.com"
    }
  ]
}
```

## Environment Variables

- `GEMINI_API_KEY` - **Recommended**: Google Gemini API key
- `OPENAI_API_KEY` - Alternative: OpenAI API key
- `AI_SERVICE` - Choose "gemini" (default) or "openai"
- `DATABASE_URL` - SQLite/PostgreSQL connection string (default: sqlite:///./powerpulse.db)
- `MAX_FILE_SIZE` - Maximum upload size in bytes (default: 52428800 = 50MB)

## Architecture

- **FastAPI**: Modern Python web framework with automatic OpenAPI documentation
- **SQLAlchemy**: Database ORM with support for SQLite and PostgreSQL  
- **Google Gemini**: **Primary AI model** for sentiment analysis and satisfaction scoring
- **OpenAI GPT**: Alternative AI model (fallback option)
- **Pandas**: Data processing and CSV export functionality
- **Docker**: Containerized deployment with health checks

## Production Features

- **Health Checks**: Docker health monitoring
- **Error Handling**: Comprehensive logging and error recovery
- **Rate Limiting**: Built-in AI API retry logic
- **Scalability**: Async processing with background tasks
- **Monitoring**: Request logging and performance tracking
- **AI Flexibility**: Easy switching between Gemini and GPT

## Business Metrics

The system provides key customer service metrics:

- **CSAT Percentage**: % of satisfied customers (satisfaction_score >= 4)
- **FCR Rate**: % of issues resolved on first contact  
- **Average Response Time**: Mean agent response time in minutes
- **Sentiment Distribution**: Customer message sentiment analysis
- **Topic Analysis**: Most common conversation topics

## Dummy overview

This section explains the core metric calculations in plain language for non-technical stakeholders.

- Customer satisfaction (CSAT): the percentage of conversations judged "satisfied" (satisfaction score usually treated as satisfied when >= 4).
- First Contact Resolution (FCR): the percentage of conversations resolved on the first customer contact.
- Average Response Time: the typical time (in minutes) it takes an agent to reply to a customer message, averaged across conversations.
- Average Sentiment: the average sentiment score for customer messages (based on AI analysis), expressed as a numeric average.

## Techie specifics

Detailed, code-level notes for engineers maintaining the calculations.

- CSAT (code): computed in `services/analytics_service.py` by counting Conversation rows marked satisfied (e.g. `satisfaction_score >= 4` or `is_satisfied == True`) and dividing by total conversations. Formula: `csat_percentage = (satisfied_count / total_conversations) * 100`.

- FCR (code): computed in `services/analytics_service.py` by counting Conversation rows where `first_contact_resolution == True` and dividing by total conversations. Formula: `fcr_percentage = (fcr_count / total_conversations) * 100`.

- Average Response Time (code): per-conversation response times are calculated when processing uploads (see `services/file_service.py` and `services/file_service_optimized.py`). For each agent message, the service finds the most recent preceding customer message and computes the time difference (minutes). A conversation's `avg_response_time_minutes` is the mean of those diffs; analytics then uses a DB AVG across conversations (e.g. `AVG(conversations.avg_response_time_minutes)`).

- Average Sentiment (code): message-level sentiment is produced by the AI service (`services/gpt_service.py` or `services/gpt_service_optimized.py` / Gemini equivalents) and stored on `Message` records (field `sentiment_score`). Conversation-level sentiment (e.g. `avg_sentiment`) is derived from customer messages during conversation metric calculation (in `services/file_service*.py`). Analytics then averages conversations' sentiment via SQL AVG.


### Notes and edge cases

- Empty datasets: analytics code guards against division by zero by checking `total_conversations` before computing percentages.
- Null or missing scores: only messages/conversations with valid numeric sentiment or satisfaction values are included in averages.
- Autoresponse filtering and data cleaning: message preprocessing filters out autoresponses and invalid messages before metrics are computed (see `services/file_service*.py`).

## Testing

### Run unit tests

```bash
# Test Gemini service
python -m pytest tests/unit/test_gemini_service.py -v

# Test all services
python -m pytest tests/ -v

# Run diagnostics
python tests/test_diagnostics.py
```

## License

This project is proprietary software developed for customer satisfaction analytics.