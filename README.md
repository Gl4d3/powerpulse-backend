# PowerPulse Analytics

A production-ready customer satisfaction analytics backend built with FastAPI that processes Facebook Direct Messages to generate business intelligence metrics using OpenAI GPT-4o-mini for sentiment analysis.

## Features

### ✅ Core Analytics
- **Sentiment Analysis**: AI-powered analysis of customer messages using GPT-4o-mini
- **CSAT Calculation**: Customer satisfaction percentage tracking
- **FCR Metrics**: First Contact Resolution rate analysis  
- **Response Time Analytics**: Agent response time tracking and averages
- **Topic Extraction**: Automatic identification of conversation topics

### ✅ Production Enhancements
- **Autoresponse Filtering**: Automatically filters out messages containing "*977#"
- **Date Range Filtering**: Support for start_date/end_date parameters in API endpoints
- **GPT Processing Cache**: Prevents reprocessing with ProcessedChat tracking
- **Retry Logic**: Exponential backoff for OpenAI API failures (max 2 retries)
- **Force Reprocess**: Optional reanalysis of previously processed conversations

### ✅ API Endpoints
- `POST /api/upload-json` - Upload Facebook chat JSON files
- `GET /api/metrics` - Business intelligence dashboard metrics  
- `GET /api/conversations` - Paginated conversation list with filtering
- `GET /api/conversations/{chat_id}` - Individual conversation details
- `GET /api/download` - CSV export functionality

### ✅ Data Processing
- **JSON Format**: Processes grouped_chats format (FB_CHAT_ID as key, message arrays as values)
- **Message Validation**: Filters invalid messages and autoresponses
- **Batch Processing**: Efficient GPT API usage through batched requests
- **Database Persistence**: SQLite with PostgreSQL compatibility

## Quick Start

### Using Python directly:
```bash
# Install dependencies
pip install -r pyproject.toml

# Set OpenAI API key
export OPENAI_API_KEY="your-key-here"

# Run the server
python main.py
```

### Using Docker:
```bash
# Build and run
docker-compose up --build

# Or build manually
docker build -t powerpulse-analytics .
docker run -p 8000:8000 -e OPENAI_API_KEY="your-key" powerpulse-analytics
```

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

- `OPENAI_API_KEY` - Required for GPT analysis
- `DATABASE_URL` - SQLite/PostgreSQL connection string (default: sqlite:///./powerpulse.db)
- `MAX_FILE_SIZE` - Maximum upload size in bytes (default: 52428800 = 50MB)

## Architecture

- **FastAPI**: Modern Python web framework with automatic OpenAPI documentation
- **SQLAlchemy**: Database ORM with support for SQLite and PostgreSQL  
- **OpenAI GPT-4o-mini**: AI model for sentiment analysis and satisfaction scoring
- **Pandas**: Data processing and CSV export functionality
- **Docker**: Containerized deployment with health checks

## Production Features

- **Health Checks**: Docker health monitoring
- **Error Handling**: Comprehensive logging and error recovery
- **Rate Limiting**: Built-in GPT API retry logic
- **Scalability**: Async processing with background tasks
- **Monitoring**: Request logging and performance tracking

## Business Metrics

The system provides key customer service metrics:

- **CSAT Percentage**: % of satisfied customers (satisfaction_score >= 4)
- **FCR Rate**: % of issues resolved on first contact  
- **Average Response Time**: Mean agent response time in minutes
- **Sentiment Distribution**: Customer message sentiment analysis
- **Topic Analysis**: Most common conversation topics

## License

This project is proprietary software developed for customer satisfaction analytics.