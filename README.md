# PowerPulse Analytics

A production-ready customer satisfaction analytics backend built with FastAPI. It processes customer service chat logs, using **Google Gemini AI** to perform a sophisticated, daily-granularity analysis and calculate a detailed Customer Satisfaction Index (CSI).

## Core Features

### ✅ Advanced CSI Analytics (Daily Granularity)
- **AI-Powered Micro-Metrics**: Extracts 8 distinct metrics from each day's conversation using **Google Gemini 1.5 Flash**, including sentiment, resolution, and customer effort.
- **Four Pillars of Service**: Calculates daily scores for **Effectiveness, Efficiency, Effort, and Empathy**.
- **Weighted CSI Score**: Aggregates the four pillars into a final, weighted daily CSI score for nuanced performance tracking.
- **Historical Trend Analysis**: Provides daily trend data for CSI and all underlying metrics.

### ✅ Production-Grade Architecture
- **Alembic Database Migrations**: Manages all database schema changes safely and automatically.
- **Asynchronous Job Processing**: Handles large file uploads in the background without blocking the API, managed by a concurrency-limited job queue.
- **Format-Agnostic Ingestion**: Intelligently parses multiple JSON formats, including raw database extracts and pre-grouped conversation files.
- **Robust Error Handling**: Includes exponential backoff and retry logic for AI API calls and graceful handling of job failures.
- **Multi-AI Support**: Configurable to switch between Google Gemini and OpenAI GPT.
- **Detailed Logging**: Separates application trace logs from server logs for clean and effective debugging.

### ✅ API Endpoints
- `POST /api/upload-json` - Upload chat log JSON files for processing.
- `GET /api/progress/{upload_id}` - Track the real-time progress of a file upload.
- `GET /api/metrics` - Retrieve the latest aggregated dashboard metrics (CSI, pillars, etc.).
- `GET /api/charts/csi-trend` - Fetch historical data for CSI and pillar scores, formatted for charts.
- `GET /api/charts/sentiment-trend` - Fetch historical sentiment trend data.
- `GET /api/explorer/analyses` - **NEW**: Get a paginated list of daily analyses for the Conversation Explorer.
- `GET /api/explorer/transcript/{daily_analysis_id}` - **NEW**: Get the message transcript for a specific daily analysis.
- `GET /api/download` - Export raw data tables to timestamped CSV files.

## Quick Start

### Prerequisites
- Python 3.10+
- An active Google Gemini API key (with the Generative Language API enabled and a billing account attached to the project).

### Installation & Setup
```bash
# 1. Clone the repository
git clone <repository-url>
cd PowerPulse

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure your environment
# Copy the .env.example to .env and add your GEMINI_API_KEY
cp .env.example .env
# -> nano .env

# 4. Apply database migrations
alembic upgrade head

# 5. Run the server
uvicorn main:app --reload
```

## How It Works: The Data Pipeline
1.  **Upload**: A user uploads a JSON file containing raw message data.
2.  **Parse & Group**: The system intelligently detects the JSON format and groups all messages by `conversation_id` and then by `date`.
3.  **Create Daily Analysis Records**: For each day a conversation has messages, a `DailyAnalysis` record is created in the database.
4.  **Batch & Job Creation**: These new `DailyAnalysis` records are grouped into batches, and a `Job` is created for each batch.
5.  **Background AI Processing**: A background worker picks up each job. It sends the daily message batches to the Gemini API to extract the 8 qualitative micro-metrics.
6.  **Metric Calculation**:
    - The system calculates quantitative time-based metrics (e.g., response times).
    - It then calculates the four pillar scores (Effectiveness, Effort, Efficiency, Empathy).
    - Finally, it computes the weighted daily CSI score.
7.  **Database Persistence**: All scores are saved to the `daily_analyses` table.
8.  **API Aggregation**: The API endpoints read from this table to provide aggregated metrics and historical trends.

## API Usage Example

### Upload a chat data file for processing:
```bash
curl -X POST "http://localhost:8000/api/upload-json" \
  -F "file=@path/to/your/data.json"
```
*The API will immediately return an `upload_id`. Use this ID to track progress.*

### Check the progress of your upload:
```bash
curl "http://localhost:8000/api/progress/your-upload-id"
```

### Get the main dashboard metrics:
```bash
curl "http://localhost:8000/api/metrics"
```

## Environment Variables
- `GEMINI_API_KEY` - **Required**. Your Google Gemini API key.
- `AI_CONCURRENCY` - Max number of concurrent API calls to make. Defaults to `2` to respect free-tier rate limits.
- `BATCH_SIZE` - Number of daily analyses to group into a single job. Defaults to `20`.
- `DATABASE_URL` - Connection string for the database. Defaults to `sqlite:///./powerpulse.db`.

## Testing
```bash
# Run all unit and integration tests
pytest

# Or run a specific test file
pytest tests/unit/test_analytics_service.py -v
```
