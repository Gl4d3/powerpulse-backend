# Data Model: Interaction Analysis Endpoints with JSON Upload and Batching Optimization

## Entity Overview

This document defines the data model enhancements required for reliable interaction analysis with JSON upload and optimized batching functionality.

## Core Entities (Existing - Preserved)

### InteractionAnalysis
**Purpose**: Represents individual customer-agent interactions within conversations  
**Location**: `models.py` (existing)  

```python
class InteractionAnalysis(Base):
    __tablename__ = "interaction_analyses"
    
    # Primary identification
    id: int (PK)
    conversation_id: int (FK to conversations.id)
    
    # Interaction boundaries  
    start_message_id: int (FK to messages.id)
    end_message_id: int (FK to messages.id)
    interaction_start: datetime
    interaction_end: datetime
    
    # Metadata
    message_count: int
    turns_count: int
    interaction_duration: float (minutes)
    boundary_method: str (detection method used)
    boundary_confidence: float (0-1)
    
    # CSI Scores (Constitutional Dual Architecture)
    csi_score: float (calculated from AI micro-metrics - PRIMARY)
    inferred_csi: float (AI blackbox inference - COMPARISON)
    
    # Four Pillars Breakdown (from AI micro-metrics)
    effectiveness_score: float
    efficiency_score: float  
    effort_score: float
    empathy_score: float
    
    # Processing metadata
    processed_at: datetime
    ai_model_version: str
    token_usage: int
    created_at: datetime
    updated_at: datetime
```

**Relationships**:
- `conversation: Conversation` (many-to-one)
- `start_message: Message` (many-to-one)  
- `end_message: Message` (many-to-one)

**Validation Rules**:
- `interaction_start <= interaction_end`
- `start_message_id <= end_message_id`
- `csi_score` and `inferred_csi` must be 1-10 range
- `effectiveness_score`, `efficiency_score`, `effort_score`, `empathy_score` must be 1-10 range

### Job (Existing - Enhanced)
**Purpose**: Represents batch processing tasks with progress tracking  
**Location**: `models.py` (existing, enhanced for interaction analysis)

```python
class Job(Base):
    __tablename__ = "jobs"
    
    # Core job identification
    id: int (PK)
    upload_id: str (index, links to upload sessions)
    
    # Job configuration
    task_name: str (default: "interaction_csi_analysis")
    status: str (pending|running|completed|failed|retryable_failure)
    
    # Execution control
    run_at: datetime
    retry_count: int (default: 0)
    max_retries: int (default: 3)
    
    # Progress tracking (enhanced for interaction analysis)
    total_conversations: int
    processed_conversations: int
    total_interactions: int  
    processed_interactions: int
    current_stage: str (parsing|detection|analysis|completion)
    
    # Results aggregation
    avg_csi_score: float
    success_rate: float (successful_interactions / total_interactions)
    
    # Performance metrics
    processing_time_seconds: float
    total_tokens_used: int
    api_calls_made: int
    
    # Error tracking
    error_count: int
    error_details: JSON (list of error messages)
    
    # Timestamps  
    created_at: datetime
    started_at: datetime
    completed_at: datetime
    updated_at: datetime
```

**Relationships**:
- `daily_analyses: List[DailyAnalysis]` (many-to-many via job_daily_analyses)
- `interaction_analyses: List[InteractionAnalysis]` (many-to-many via job_interaction_analyses)

**State Transitions**:
```
pending → running → completed
pending → running → failed
failed → pending (if retry_count < max_retries)
```

## Enhanced Entities (New/Modified)

### BatchContext (New)
**Purpose**: Manages context window optimization and batch processing parameters  
**Location**: New addition to `models.py`

```python
class BatchContext(Base):
    __tablename__ = "batch_contexts"
    
    # Identification
    id: int (PK)
    job_id: int (FK to jobs.id)
    batch_number: int
    
    # Context window management
    context_window_size: int (default: 20000 tokens)
    actual_tokens_used: int
    interaction_count: int
    
    # Batch composition
    conversation_ids: JSON (list of conversation IDs in batch)
    interaction_ids: JSON (list of interaction IDs processed)
    
    # Processing metrics
    batch_start_time: datetime
    batch_end_time: datetime
    processing_duration_seconds: float
    api_calls_count: int
    
    # Results
    successful_interactions: int
    failed_interactions: int
    avg_batch_csi: float
    
    # Error handling
    errors: JSON (list of error details)
    retry_count: int
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
```

**Relationships**:
- `job: Job` (many-to-one)

**Validation Rules**:
- `actual_tokens_used <= context_window_size`
- `batch_start_time <= batch_end_time`
- `successful_interactions + failed_interactions = interaction_count`

### UploadSession (Enhanced)
**Purpose**: Tracks JSON file upload metadata and processing status  
**Location**: Enhanced in existing upload flow

```python
class UploadSession(Base):
    __tablename__ = "upload_sessions"
    
    # Session identification
    id: int (PK) 
    upload_id: str (UUID, indexed)
    
    # File metadata
    filename: str
    file_size_bytes: int
    content_type: str
    upload_timestamp: datetime
    
    # Processing configuration
    mode: str (interaction|daily)
    force_reprocess: bool (default: False)
    
    # Content analysis  
    total_conversations: int
    total_messages: int
    estimated_interactions: int
    
    # Processing status
    status: str (uploaded|parsing|processing|completed|failed)
    progress_percentage: float (0-100)
    current_stage: str
    
    # Results summary
    conversations_processed: int
    interactions_detected: int
    interactions_analyzed: int
    avg_csi_score: float
    
    # Performance tracking
    processing_start_time: datetime
    processing_end_time: datetime
    total_processing_time_seconds: float
    
    # Error handling
    error_message: str
    error_details: JSON
    
    # Relationships
    job_id: int (FK to jobs.id, nullable)
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
```

**Relationships**:
- `job: Job` (one-to-one, optional)

**State Transitions**:
```
uploaded → parsing → processing → completed
uploaded → parsing → processing → failed  
uploaded → parsing → failed
```

## Response Models (API Schemas)

### UploadResponse (Enhanced)
**Purpose**: Response for `/api/upload-interaction-json` endpoint  
**Location**: `schemas.py` (existing, enhanced)

```python
class UploadResponse(BaseModel):
    # Basic upload confirmation
    message: str
    upload_id: str
    status: str
    
    # Processing summary
    conversations_processed: int
    interactions_detected: int  
    interactions_analyzed: int
    
    # Results overview
    avg_csi_score: float
    avg_effectiveness: float
    avg_efficiency: float
    avg_effort: float  
    avg_empathy: float
    
    # Performance metrics
    processing_time_seconds: float
    total_tokens_used: int
    api_calls_made: int
    
    # Quality metrics
    success_rate: float
    error_count: int
    
    # Progress tracking
    progress_url: str  # URL to check processing status
    
    # Timestamps
    started_at: datetime
    completed_at: datetime
```

### BatchProcessingStatus (New)
**Purpose**: Response for batch processing status endpoint  
**Location**: New addition to `schemas.py`

```python
class BatchProcessingStatus(BaseModel):
    # Job identification
    upload_id: str
    job_id: int
    status: str
    
    # Overall progress
    progress_percentage: float
    current_stage: str
    estimated_completion_minutes: int
    
    # Processing metrics
    total_conversations: int
    processed_conversations: int
    total_interactions: int
    processed_interactions: int
    
    # Batch details
    current_batch_number: int
    total_batches: int
    batch_contexts: List[BatchContextResponse]
    
    # Performance tracking
    processing_speed_interactions_per_second: float
    elapsed_time_seconds: float
    
    # Results (partial/final)
    avg_csi_score: float (nullable if in progress)
    success_rate: float
    
    # Error summary
    error_count: int
    recent_errors: List[str] (last 5 errors)
    
    # Timestamps
    started_at: datetime
    last_updated_at: datetime
    estimated_completion_at: datetime (nullable)
```

### InteractionAnalysisResult (Enhanced)  
**Purpose**: Detailed interaction analysis results with dual CSI  
**Location**: Enhanced in `schemas.py`

```python
class InteractionAnalysisResult(BaseModel):
    # Interaction identification
    interaction_id: int
    conversation_id: int
    
    # Interaction boundaries
    start_time: datetime
    end_time: datetime
    duration_minutes: float
    message_count: int
    
    # Constitutional Dual CSI Architecture
    csi_score: float  # Primary: calculated from AI micro-metrics
    inferred_csi: float  # Secondary: AI blackbox inference
    
    # Four Pillars Breakdown (from AI micro-metrics)
    effectiveness_score: float
    efficiency_score: float
    effort_score: float
    empathy_score: float
    
    # Processing metadata
    confidence_level: float
    detection_method: str
    token_usage: int
    processing_time_seconds: float
    
    # Quality indicators
    analysis_quality: str (high|medium|low)
    anomaly_flags: List[str]
```

## Database Relationships

### Interaction Analysis Flow
```
UploadSession (1) → Job (1) → BatchContext (*)
Job (1) → InteractionAnalysis (*) 
InteractionAnalysis (*) → Conversation (1)
InteractionAnalysis (*) → Message (start/end)
```

### Progress Tracking Flow
```
UploadSession.upload_id → Job.upload_id
Job.id → BatchContext.job_id
BatchContext.interaction_ids → InteractionAnalysis.id
```

## Indexes for Performance

### Critical Indexes (Existing + New)
```sql
-- Existing (preserved)
CREATE INDEX idx_interaction_analysis_conversation_id ON interaction_analyses(conversation_id);
CREATE INDEX idx_interaction_analysis_processed_at ON interaction_analyses(processed_at);
CREATE INDEX idx_jobs_upload_id ON jobs(upload_id);
CREATE INDEX idx_jobs_status ON jobs(status);

-- New for enhanced functionality  
CREATE INDEX idx_upload_sessions_upload_id ON upload_sessions(upload_id);
CREATE INDEX idx_upload_sessions_status ON upload_sessions(status);  
CREATE INDEX idx_batch_contexts_job_id ON batch_contexts(job_id);
CREATE INDEX idx_interaction_analyses_csi_scores ON interaction_analyses(csi_score, inferred_csi);
```

## Migration Strategy

### Phase 1: Add New Tables
- Create `upload_sessions` table
- Create `batch_contexts` table  
- Add indexes for new tables

### Phase 2: Enhance Existing Tables  
- Add progress tracking fields to `jobs` table
- Add performance metrics to `interaction_analyses` table
- Preserve existing data and relationships

### Phase 3: Update Application Layer
- Enhance response models in `schemas.py`
- Update service layer for new entities
- Maintain backward compatibility

## Constitutional Compliance

### AI Micro-Metrics Supremacy ✅
- `csi_score` field represents calculated CSI from AI micro-metrics (PRIMARY)
- Four Pillars fields (`effectiveness_score`, etc.) derived from AI extraction
- No rule-based calculation fields introduced

### Dual CSI Architecture ✅  
- `csi_score`: Calculated from AI micro-metrics → Four Pillars → Weighted CSI
- `inferred_csi`: AI blackbox inference for comparison
- Both scores exposed in all API responses

### Brownfield Compatibility ✅
- All existing tables and relationships preserved
- New entities extend functionality without breaking changes
- Migration strategy maintains data integrity