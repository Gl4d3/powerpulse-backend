# Phase 1: Planning and Specification - Interaction-Based CSI Analysis

**Date**: September 16, 2025  
**Status**: In Progress  
**Objective**: Define comprehensive specification for interaction-based grouping system with backward compatibility

## Context Summary

PowerPulse Analytics currently processes customer service chats using daily-granularity analysis via `DailyAnalysis` model. The system groups messages by `(conversation_id, analysis_date)` with a unique database index, calculating CSI scores using four pillars (Effectiveness: 0.29, Effort: 0.27, Efficiency: 0.21, Empathy: 0.23).

**Current Limitations Identified**:
- No session boundary detection within or across days
- Time metrics artificially bounded by calendar days  
- Multiple logical interactions on same day merged into single analysis
- Missing escalation and resolution pattern recognition

**Sample Interaction Patterns** (from Claude's analysis):
- **Daniel W***: 4-day gap between resolved outage and new complaint
- **Judy K***: Multiple same-day interactions requiring separate CSI analysis
- **Cliff A***: Escalation patterns with "Attention" signals

## Specifications

### 1. InteractionAnalysis Data Model

**New Model**: `InteractionAnalysis` (parallel to existing `DailyAnalysis`)

```python
class InteractionAnalysis(Base):
    """
    Stores CSI analysis for a single customer service interaction.
    An interaction represents a complete issue cycle from initiation to resolution/closure.
    """
    __tablename__ = "interaction_analyses"

    # Primary Key and Relations
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    
    # Interaction Boundaries
    interaction_start = Column(DateTime, nullable=False)  # First message timestamp
    interaction_end = Column(DateTime, nullable=False)    # Last message timestamp  
    interaction_type = Column(String, nullable=True)     # "outage", "billing", "inquiry", etc.
    
    # Detection Metadata
    boundary_method = Column(String, nullable=False)     # "time_gap", "resolution_keywords", "ai_detected"
    boundary_confidence = Column(Float, nullable=True)   # 0.0-1.0 confidence score
    
    # Relationships
    conversation = relationship("Conversation", back_populates="interaction_analyses")
    jobs = relationship("Job", secondary=job_interaction_analyses, back_populates="interaction_analyses")

    # --- Micro-Metrics (Identical to DailyAnalysis) ---
    sentiment_score = Column(Float, nullable=True)        # 0-10 scale
    sentiment_shift = Column(Float, nullable=True)        # -5 to +5
    resolution_achieved = Column(Float, nullable=True)    # 0-10 scale
    fcr_score = Column(Float, nullable=True)             # 0-10 scale
    ces = Column(Float, nullable=True)                   # 1-7 scale (Customer Effort Score)
    common_topics = Column(JSON, nullable=True)          # Array of topic strings
    first_response_time = Column(Float, nullable=True)   # seconds
    avg_response_time = Column(Float, nullable=True)     # seconds
    total_handling_time = Column(Float, nullable=True)   # minutes

    # --- Pillar Scores (Calculated from Micro-metrics) ---
    effectiveness_score = Column(Float, nullable=True)   # 0-10 scale
    effort_score = Column(Float, nullable=True)         # 0-10 scale
    efficiency_score = Column(Float, nullable=True)     # 0-10 scale
    empathy_score = Column(Float, nullable=True)        # 0-10 scale

    # --- Final CSI Score for the Interaction ---
    csi_score = Column(Float, nullable=True, index=True) # 0-10 scale

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

**Key Design Decisions**:
- **No unique constraint** on conversation/date (allows multiple interactions per day)
- **Boundary metadata** for detection method tracking and confidence
- **Identical metrics** to DailyAnalysis for consistent CSI calculation
- **Interaction type** for utility-specific categorization (outage, billing, etc.)

### 2. New API Endpoints

**Upload Endpoint**: 
```
POST /api/upload-interaction-json
Content-Type: multipart/form-data
Parameters: file (JSON), force_reprocess (optional boolean)
Response: {
  "message": "Successfully processed X conversations with Y interactions",
  "conversations_processed": X,
  "interactions_processed": Y, 
  "interaction_upload_id": "uuid-string"
}
```

**Explorer Endpoints**:
```
GET /api/explorer/interactions?page=1&page_size=50&sort_by=csi_score&sort_order=desc
Response: {
  "interactions": [
    {
      "id": 123,
      "conversation_id": 456,
      "fb_chat_id": "chat_id_string",
      "customer_name": "Customer Name",
      "interaction_start": "2025-08-18T10:55:25Z",
      "interaction_end": "2025-08-18T14:58:35Z",
      "interaction_type": "outage",
      "csi_score": 7.8,
      "boundary_method": "resolution_keywords",
      "message_count": 7
    }
  ],
  "total": 500,
  "page": 1,
  "pages": 10
}

GET /api/explorer/transcript/{interaction_analysis_id}
Response: {
  "interaction": { /* InteractionAnalysis details */ },
  "messages": [
    {
      "id": 789,
      "message_content": "Hello",
      "direction": "to_company", 
      "social_create_time": "2025-08-18T10:55:25Z",
      "agent_info": null
    }
  ]
}
```

**Progress Tracking**:
```
GET /api/progress/{interaction_upload_id}
Response: {
  "upload_id": "uuid-string",
  "status": "processing", // "completed", "failed"
  "interactions_processed": 45,
  "total_interactions": 67,
  "current_stage": "ai_analysis"
}
```

**Metrics Endpoints**:
```  
GET /api/interaction-metrics?start_date=2025-08-01&end_date=2025-08-31
Response: {
  "total_interactions": 500,
  "avg_csi_score": 6.7,
  "avg_effectiveness": 6.2,
  "avg_efficiency": 7.1,  
  "avg_effort": 6.8,
  "avg_empathy": 6.9,
  "interaction_type_breakdown": {
    "outage": {"count": 300, "avg_csi": 6.5},
    "billing": {"count": 150, "avg_csi": 7.2},
    "inquiry": {"count": 50, "avg_csi": 8.1}
  }
}
```

### 3. Interaction Detection Rules

**Primary Rule-Based Detection** (Cost-Effective):

1. **Time Gap Rule**: 
   - Split on gaps > 4 hours (configurable: `INTERACTION_GAP_HOURS=4`)
   - Account for business hours (Kenya Power: 8 AM - 6 PM)

2. **Resolution Keywords**:
   - **Closure Signals**: "power restored", "thanks", "resolved", "working now", "problem solved"
   - **New Issue Signals**: "hello", "attention", "another", "again", reference number patterns

3. **Agent Handoff Detection**:
   - Different agent email/username in sequence
   - Explicit handoff language: "transferring", "escalating"

4. **Topic Shift Detection**:  
   - Keyword transitions: "outage" → "billing", "prepaid" → "postpaid"
   - Reference number changes (e.g., "13459714" → "13495277")

**AI Fallback Detection** (For Complex Cases):
- Trigger when: >20 messages AND no clear rule-based splits
- Gemini prompt: "Segment this conversation into logical customer service interactions. Consider issue types, resolution events, and natural conversation boundaries."
- Response format: JSON list with start/end message indices and interaction type

### 4. Backward Compatibility Strategy

**Parallel Processing Architecture**:
- Existing `/api/upload-json` → Daily analysis (unchanged)
- New `/api/upload-interaction-json` → Interaction analysis
- Both endpoints coexist; no modification to existing logic
- Shared services via mode parameter (e.g., `interaction_mode: bool`)

**Database Coexistence**:
- `DailyAnalysis` table unchanged (keeps unique constraint)
- New `InteractionAnalysis` table (no conflicting constraints)
- Optional linking table for daily roll-up aggregation

**Service Layer Compatibility**:
- `file_service_optimized.py`: Add `process_grouped_chats_json_interaction_mode()`
- `batch_service.py`: Add `create_interaction_analysis_batches()`
- `gemini_service.py`: Add `analyze_interaction_analyses_batch()`

## Test-Driven Development (TDD) Plan

### Skeleton Tests (To be implemented)

**Unit Tests** (`tests/unit/test_interaction_service.py`):
```python
def test_detect_time_gap_interactions():
    """Test detection of interactions split by 4+ hour gaps"""
    # Use Daniel W* sample: 4-day gap between resolution and new complaint
    pass

def test_detect_resolution_keyword_interactions():
    """Test detection based on resolution closure language"""
    # Use "power restored" + "thanks" pattern
    pass

def test_detect_same_day_multiple_interactions():
    """Test multiple interactions on same calendar day"""
    # Use Judy K* sample: 6-hour gap same day
    pass
```

**Integration Tests** (`tests/integration/test_interaction_flow.py`):
```python
def test_upload_interaction_json_endpoint():
    """Test new upload endpoint processes interactions correctly"""
    pass

def test_interaction_csi_calculation():
    """Test CSI calculation for interaction-based analysis"""
    pass
```

**Model Tests** (`tests/unit/test_models.py`):
```python
def test_interaction_analysis_model_creation():
    """Test InteractionAnalysis model fields and relationships"""
    pass
```

## Implementation Steps (Next Phases)

1. **Phase 2**: Implement `services/interaction_service.py` with rule-based detection
2. **Phase 3**: Add `InteractionAnalysis` model and Alembic migration  
3. **Phase 4**: Integrate interaction mode into existing services
4. **Phase 5**: Create new API endpoints
5. **Phase 6**: Comprehensive testing and validation
6. **Phase 7**: Documentation and deployment

## Risk Mitigation

**Performance Concerns**:
- Rule-based detection handles 90%+ cases without AI calls
- Batch size limits maintained (`MAX_TOKENS_PER_BATCH=8000`)
- Gradual rollout with feature flags

**Accuracy Validation**:
- Test against Claude's identified samples
- Manual validation of boundary detection
- Confidence scoring for AI-detected boundaries

**Operational Safety**:
- No changes to existing daily analysis flow
- Separate upload endpoint prevents accidental interaction processing
- Database migrations are additive only

## Completion Checkpoint

**Phase 1 Success Criteria**:
- ✅ Comprehensive specification documented
- ✅ API contracts defined  
- ✅ Data model specified
- ✅ TDD plan established
- ✅ Backward compatibility strategy confirmed
- ⏳ Skeleton tests to be implemented in Phase 2

**No Code Changes Yet**: This phase is specification only.
**Next Phase**: Implement interaction detection service with rule-based logic.

---

**Note**: This specification maintains 100% backward compatibility while introducing intelligent interaction detection. The system will handle Kenya Power's utility-specific patterns (outages, escalations) and scale cost-effectively with rule-based detection as the primary method.