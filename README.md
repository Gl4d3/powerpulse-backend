# PowerPulse Analytics - Constitutional Compliance Edition

A production-ready customer satisfaction analytics backend built with FastAPI. It processes customer service chat logs using **constitutionally compliant AI-Enhanced Interaction Detection** and **Google Gemini AI** to perform sophisticated, interaction-level analysis and calculate detailed Customer Satisfaction Index (CSI) scores.

## 🎯 Constitutional Compliance Status: ✅ FULLY COMPLIANT

**BREAKING CHANGE**: This version enforces constitutional compliance with **Amendment I** by removing all rule-based micro-metrics calculations and implementing pure AI micro-metrics extraction for interaction analysis, ensuring identical methodology with daily analysis.

### Constitutional Amendments Enforced:
- ✅ **Amendment I**: AI micro-metrics extraction SHALL remain the authoritative method
- ✅ **Amendment II**: ALL pipeline logic SHALL remain identical between daily and interaction analysis  
- ✅ **Amendment III**: Test-driven development SHALL prevent scope creep

## Core Features

### 🚀 AI-Enhanced Interaction Detection
- **Hybrid Detection Pipeline**: Combines rule-based boundary detection with AI refinement for optimal accuracy
- **Smart Boundary Enhancement**: AI identifies missed interactions and removes false boundaries with 95%+ confidence
- **Intelligent Reasoning**: Each AI suggestion includes detailed explanations for transparency
- **Graceful Fallback**: System maintains reliability even when AI enhancement is unavailable
- **Real-Time Processing**: Concurrent interaction detection with configurable performance limits

### ✅ Advanced CSI Analytics (Interaction-Level Granularity) - CONSTITUTIONALLY COMPLIANT
- **🔬 Constitutional AI Micro-Metrics**: Uses `GeminiService.analyze_interaction_analyses_batch()` to extract 8 distinct metrics from each customer service interaction using **Google Gemini 1.5 Flash** - **IDENTICAL** to daily analysis methodology
- **🏛️ Constitutional Four Pillars**: Calculates interaction scores for **Effectiveness, Effort, Efficiency, and Empathy** using **IDENTICAL** enhanced analytics service as daily analysis
- **⚖️ Dual CSI Architecture**: Provides both calculated CSI (from AI micro-metrics → four pillars) and inferred CSI (direct AI blackbox assessment) for validation and transparency
- **📊 Multi-Dimensional Analytics**: Supports both daily-granularity (legacy) and interaction-level (new) analysis with **>0.8 correlation** between methodologies
- **📈 Executive Reporting**: Automated insights, trends, and actionable recommendations

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

#### Core Data Processing
- `POST /api/upload-json` - Upload chat log JSON files for processing
- `GET /api/progress/{upload_id}` - Track real-time progress of file uploads

#### Analytics & Reporting  
- `GET /api/metrics` - Retrieve aggregated dashboard metrics (CSI, pillars, etc.)
- `GET /api/charts/csi-trend` - Historical CSI and pillar score data for charts
- `GET /api/charts/sentiment-trend` - Historical sentiment trend data

#### Interaction Analysis (New)
- `POST /api/interactions/detect` - AI-enhanced interaction detection for conversations
- `GET /api/interactions/analytics/{interaction_id}` - Detailed CSI metrics for specific interactions
- `GET /api/interactions/report` - Generate comprehensive analytics reports for time periods

#### Legacy Daily Analysis
- `GET /api/explorer/analyses` - Paginated list of daily analyses
- `GET /api/explorer/transcript/{daily_analysis_id}` - Message transcript for daily analysis

#### Data Export
- `GET /api/download` - Export data tables to timestamped CSV files

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

## How It Works: The Complete CSI Analysis Pipeline

### 🔄 End-to-End Processing Flow

1. **Upload & Parsing**: JSON files are uploaded and intelligently parsed to detect conversation structure
2. **AI-Enhanced Interaction Detection**:
   - Rule-based boundary detection identifies potential interaction breaks (time gaps, resolution keywords)
   - AI enhancement refines boundaries using contextual understanding
   - Smart merging/splitting of interactions based on conversation flow
3. **Comprehensive CSI Analytics**:
   - Each detected interaction is analyzed for 4 pillar scores (Effectiveness, Effort, Efficiency, Empathy)
   - AI assessment combined with quantitative metrics (response times, message counts)
   - Weighted CSI score calculation (0-10 scale)
4. **Executive Reporting & Insights**:
   - Automated pattern detection and trend analysis
   - Performance alerts and actionable recommendations
   - Multi-dimensional analytics (time-based, agent-based, topic-based)

### 📊 Legacy Daily Analysis Pipeline (Maintained)

1. **Upload**: JSON files processed and `upload_id` returned immediately
2. **Parse & Group**: Messages grouped by `conversation_id` and `date`
3. **Token-Based Batching**: Daily analyses grouped into efficient, token-limited batches
4. **Job Processing**: Background worker processes jobs via `worker.py`
5. **AI Analysis**: Gemini API analyzes daily conversation metrics
6. **CSI Calculation**: Four pillar scores computed and aggregated
7. **Database Persistence**: All scores saved with job completion tracking

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

### Core Configuration
- `GEMINI_API_KEY` - **Required**. Your Google Gemini API key
- `DATABASE_URL` - Connection string for the database. Defaults to `sqlite:///./powerpulse.db`

### AI Processing Configuration
- `AI_CONCURRENCY` - Max concurrent API calls. Defaults to `2`
- `MAX_TOKENS_PER_BATCH` - Token limit for processing batches. Defaults to `8000`
- `BATCH_PROCESSING_DELAY_SECONDS` - Delay between batch jobs. Defaults to `5`

### AI Enhancement Settings (New)
- `AI_ENHANCEMENT_ENABLED` - Enable AI boundary enhancement. Defaults to `true`
- `AI_ENHANCEMENT_CONFIDENCE_THRESHOLD` - Minimum confidence for AI suggestions. Defaults to `0.7`
- `AI_ENHANCEMENT_MAX_CONCURRENT` - Max concurrent AI enhancement calls. Defaults to `3`

## Constitutional Compliance Testing 🧪

### Validate Constitutional Compliance
```bash
# Run comprehensive constitutional compliance validator
python utils/constitutional_validator.py

# Expected output:
# 📋 CONSTITUTIONAL COMPLIANCE FINAL CHECK
# ==================================================
# Amendment I (No Rule-Based Methods): ✅ COMPLIANT
# Dual CSI Schema Exposure: ✅ COMPLIANT  
# AI Micro-Metrics Method: ✅ COMPLIANT
# ==================================================
# CONSTITUTIONAL STATUS: 🎉 FULLY COMPLIANT
```

### Run Full Test Suite
```bash
# Run constitutional compliance tests (primary)
pytest test_constitutional_compliance.py -v

# Run all unit and integration tests
pytest

# Run specific service tests
pytest tests/unit/test_analytics_service.py -v
```

### Testing Approach - How to Proceed

#### 1. Constitutional Validation (Priority 1)
```bash
# Always run this first to ensure constitutional compliance
python utils/constitutional_validator.py
```

#### 2. Interaction Analysis Testing (Priority 2)
```bash
# Test interaction analysis with real data
python -c "
from services.csi_analysis_pipeline import CSIAnalysisPipeline
from database import SessionLocal

# Test interaction detection and analysis pipeline
db = SessionLocal()
pipeline = CSIAnalysisPipeline(db)
# Run with actual conversation data
"
```

#### 3. API Integration Testing (Priority 3)
```bash
# Start the server
uvicorn main:app --reload

# Test interaction endpoints
curl -X POST http://localhost:8000/api/interactions/detect \
  -H "Content-Type: application/json" \
  -d '{"conversation_id": 1}'

# Test dual CSI exposure
curl http://localhost:8000/api/interactions/analytics/1
```

#### 4. Data Validation Testing (Priority 4)
- Upload curated sample data (`attached_assets/curated_sample.json`)
- Validate >0.8 correlation between daily and interaction CSI
- Confirm dual CSI values (calculated vs inferred) are populated
- Verify constitutional micro-metrics extraction works end-to-end

## Relevant Documentation
Here are the main documentation markdowns spread throughout the project:


   * README.md: The main entry point for the project. Relevant.
   * GEMINI.md: High-level architectural overview. Relevant.
   * LIFELINE.md: Detailed data flow documentation. Relevant.
   * docs/API_DOCUMENTATION.md: The canonical source for API contracts. Relevant.
   * docs/DATABASE_SCHEMA.md: Describes the database structure. Relevant.
   * docs/TESTING_GUIDE.md: Instructions for running tests. Relevant.

CMD: docker run -p 8000:8000 --env-file ./.env --name powerpulse-container powerpulse-backend