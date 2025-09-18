# PowerPulse Analytics Gemini Context (v7.0 - Enhanced Upload & Batching)

This document provides a comprehensive and technically accurate overview of the PowerPulse Analytics backend. It details the architecture after implementing AI-enhanced interaction analysis with hybrid boundary detection and comprehensive CSI scoring across customer service interactions.

**CURRENT FEATURE**: Interaction Analysis Endpoints with JSON Upload and Batching Optimization (Branch: `001-title-interaction-analysis`)

---
**IMPORTANT NOTE:** For detailed, human-readable API documentation, including sample requests and responses, refer to the official **[`docs/API_DOCUMENTATION.md`](./docs/API_DOCUMENTATION.md)**. This file is the canonical source for API contracts.
---

## CONSTITUTIONAL REQUIREMENTS (NON-NEGOTIABLE)

### 1. AI Micro-Metrics Supremacy
- ALL CSI calculations MUST use AI micro-metrics extraction
- NEVER implement rule-based calculations  
- Preserve existing pipeline: `AI micro-metrics → Four Pillars → Weighted CSI`

### 2. Dual CSI Architecture  
- Maintain `csi_score` (PRIMARY: calculated from AI micro-metrics)
- Maintain `inferred_csi` (SECONDARY: AI blackbox inference)
- BOTH scores must appear in ALL API responses

### 3. Brownfield Compatibility
- Enhance existing interaction analysis without breaking daily pipeline
- Use identical methodology, only change granularity (daily → interaction)
- Preserve all existing database tables and relationships

## CURRENT ENHANCEMENT FOCUS

### Upload Endpoint Status
- ✅ EXISTS: `POST /api/upload-interaction-json` in `routes/upload.py`
- 🔧 ENHANCE: Add async processing for large files (prevent timeouts)
- 🔧 ADD: Progress tracking endpoints for long-running uploads
- 🔧 INTEGRATE: Job queue system for consistency with daily analysis

### Batch Processing Status  
- ✅ WORKING: `CSIAnalysisPipeline.process_batch()` achieves 80% API cost reduction
- ✅ OPTIMIZED: 20K token context windows for efficient processing
- ✅ PROVEN: 3-4 interactions/second processing speed in E2E tests
- 🔧 ENHANCE: Better error handling and retry logic for large batches

---

## 1. High-Level Architecture & Data Flow

The backend is a FastAPI application that processes customer service chat logs with AI-enhanced interaction analysis. It features both legacy daily analysis and new interaction-based analysis pipelines.

### 1.1. AI-Enhanced Interaction Analysis Pipeline (Primary)

1.  **Conversation Processing:** Input conversations are processed through the CSI Analysis Pipeline (`services/csi_analysis_pipeline.py`) for comprehensive interaction-based analysis.

2.  **Hybrid Interaction Detection:** The `InteractionDetectionService` uses rule-based boundary detection enhanced with AI refinement via Google Gemini 1.5 Flash, achieving 88.5% high-confidence interactions with only 7.7% AI usage.

3.  **AI Boundary Enhancement:** When confidence thresholds aren't met, Gemini AI analyzes conversation context to refine interaction boundaries through merge/split operations.

4.  **Comprehensive CSI Analytics:** The `InteractionAnalyticsService` performs 4-pillar scoring (Effectiveness, Effort, Efficiency, Empathy) across detected interactions with pattern analysis and trend detection.

5.  **Executive Reporting:** Automated generation of insights, recommendations, and comprehensive reports for business stakeholders.

### 1.2. Legacy Daily Analysis Pipeline (Maintained)

1.  **Upload:** A user uploads a JSON file via `POST /api/upload-json`. The API creates necessary `Job` records in the database with a `pending` status and immediately returns an `upload_id`.

2.  **Daily Grouping & Persistence:** The backend parses conversations and groups messages by date. For each day a conversation has activity, a `DailyAnalysis` record is created in the database if one does not already exist.

3.  **Worker-Based Processing:** A standalone `worker.py` process polls the database for `pending` jobs and processes batches of `DailyAnalysis` records through Google Gemini for micro-metric extraction.

4.  **Pillar & CSI Calculation:** Four macro-metric pillars are calculated from micro-metrics with a final weighted CSI score stored in the `DailyAnalysis` table.

### 1.3. API Access (Multi-Mode)
- **AI-Enhanced Analysis:** New `/api/interactions/*` endpoints for interaction-based analysis and CSI metrics
- **Aggregated Dashboards:** `GET /api/metrics` and `GET /api/charts/*` endpoints provide system-wide data
- **Conversation Explorer:** `GET /api/explorer/*` endpoints provide granular access to daily analyses and transcripts

---

## 2. Technical Deep Dive

### 2.1. Enhanced Database Models (`models.py`)

- **`Conversation` Model:** Stores high-level metadata about a conversation (`fb_chat_id`, `customer_name`)
- **`InteractionAnalysis` Model:** **NEW** - Core interaction-based analysis with AI-enhanced CSI metrics and confidence scoring
- **`DailyAnalysis` Model:** Legacy daily analysis storing micro-metrics, four pillar scores, and CSI score with `common_topics` JSON field
- **`DetectedInteraction` Model:** **NEW** - AI-enhanced interaction boundaries with confidence levels and metadata

### 2.2. AI-Enhanced Core Services (`services/`)

- **`csi_analysis_pipeline.py`:** **NEW** - Orchestrates end-to-end interaction analysis with health monitoring and executive reporting
- **`interaction_detection_service.py`:** **NEW** - Hybrid rule-based + AI boundary detection achieving 88.5% high-confidence interactions
- **`interaction_analytics_service.py`:** **NEW** - Comprehensive CSI scoring across 4 pillars with pattern analysis and insights
- **`gemini_service.py`:** **ENHANCED** - Added AI boundary enhancement, JSON response cleaning, and interaction analysis capabilities
- **Legacy Services:** `file_service_optimized.py`, `batch_service.py`, and `analytics_service.py` maintain daily analysis functionality

### 2.3. Enhanced API Routes (`routes/`)

The API has been significantly expanded with AI-enhanced interaction analysis endpoints:

- **`routes/conversations.py`:** **NEW** - AI-enhanced interaction analysis endpoints (`/api/interactions/*`)
- **`routes/metrics.py` & `routes/charts.py`:** Enhanced with interaction-based metrics and CSI dashboards
- **`routes/explorer.py`:** Conversation Explorer with both daily and interaction-based data access

---

## 3. Production Environment & Configuration

### 3.1. AI Enhancement Configuration

```env
# AI Enhancement Settings (NEW)
AI_ENHANCEMENT_ENABLED=true
AI_CONFIDENCE_THRESHOLD=0.7
AI_ENHANCEMENT_MODEL=gemini-1.5-flash

# Gemini API Configuration
GEMINI_API_KEY=your_api_key_here
MAX_TOKENS_PER_BATCH=100000
```

### 3.2. Database & Infrastructure

- **Database:** SQLite (`powerpulse.db`) for development, PostgreSQL recommended for production
- **Migrations:** Alembic handles both legacy and new interaction analysis schema
- **Configuration:** Enhanced `config.py` with AI enhancement parameters and performance tuning
- **Health Monitoring:** Built-in pipeline health checks and performance metrics

### 3.3. Development Tools

- **Database Reset:** `reset_database.py` script for development environment cleanup
- **Test Suite:** Comprehensive tests for AI enhancement pipeline and interaction analysis
- **Performance Monitoring:** Real-time tracking of AI usage rates and confidence levels
