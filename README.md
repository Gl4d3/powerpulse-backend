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
    - **Token-Based Batching**: Intelligently groups daily analyses into batches based on a configurable token limit (`MAX_TOKENS_PER_BATCH`) to maximize efficiency and respect API context windows.
    - **Configurable Delays**: Adds a configurable delay between batch processing jobs to manage rate-limiting.
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
1.  **Upload**: A user uploads a JSON file. The API creates job records in the database for the new data and immediately returns an `upload_id`.
2.  **Parse & Group**: The system intelligently detects the JSON format and groups all messages by `conversation_id` and then by `date`.
3.  **Create Daily Analysis Records**: For each day a conversation has messages, a `DailyAnalysis` record is created in the database.
4.  **Token-Based Batching (`services/batch_service.py`):** The new `DailyAnalysis` objects are grouped into efficient, token-limited batches.
5.  **Job Creation & Processing (`worker.py` & `services/job_service.py`):**
    - For each batch, a `Job` is created with a `pending` status.
    - The standalone `worker.py` process polls the database, picks up pending jobs, and passes them to the `job_service` for execution.
    - The `job_service` calls the `gemini_service` to perform the AI analysis.
6.  **Metric Calculation**:
    - The system calculates quantitative time-based metrics (e.g., response times).
    - It then calculates the four pillar scores (Effectiveness, Effort, Efficiency, Empathy).
    - Finally, it computes the weighted daily CSI score.
7.  **Database Persistence**: All scores are saved to the `daily_analyses` table, and the job is marked as `completed`.
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
- `AI_CONCURRENCY` - Max number of concurrent API calls to make. Defaults to `2`.
- `MAX_TOKENS_PER_BATCH` - The target token limit for creating efficient AI processing batches. Defaults to `8000`.
- `BATCH_PROCESSING_DELAY_SECONDS` - The number of seconds to wait between starting each batch job. Defaults to `5`.
- `DATABASE_URL` - Connection string for the database. Defaults to `sqlite:///./powerpulse.db`.

## Testing
```bash
# Run all unit and integration tests
pytest

# Or run a specific test file
pytest tests/unit/test_analytics_service.py -v
```

## Relevant Documentation
Here are the main documentation markdowns spread throughout the project:


   * README.md: The main entry point for the project. Relevant.
   * GEMINI.md: High-level architectural overview. Relevant.
   * LIFELINE.md: Detailed data flow documentation. Relevant.
   * docs/API_DOCUMENTATION.md: The canonical source for API contracts. Relevant.
   * docs/DATABASE_SCHEMA.md: Describes the database structure. Relevant.
   * docs/TESTING_GUIDE.md: Instructions for running tests. Relevant.

CMD: docker run -p 8000:8000 --env-file ./.env --name powerpulse-container powerpulse-backend