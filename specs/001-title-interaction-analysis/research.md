# Research: Interaction Analysis Endpoints with JSON Upload and Batching Optimization

## Research Summary

This document captures research findings for enhancing the PowerPulse interaction analysis pipeline with focus on JSON upload reliability and batching optimization.

## Technology Research

### FastAPI Backend Framework
**Decision**: Continue using FastAPI for all endpoint enhancements  
**Rationale**: Existing codebase built on FastAPI with mature routing, dependency injection, and async support  
**Alternatives Considered**: Flask (lacks async), Django (too heavy for API-only service)

### SQLite Database  
**Decision**: Maintain SQLite for development/testing, support PostgreSQL for production scaling  
**Rationale**: Current powerpulse.db works well for current scale, SQLAlchemy provides database-agnostic ORM  
**Alternatives Considered**: PostgreSQL (overkill for current scale), MongoDB (schema mismatch)

### Gemini AI Integration
**Decision**: Enhance existing Gemini batch processing with optimized context window management  
**Rationale**: Existing batch API reduces costs by 80% (2000→200 API calls), proven in E2E tests  
**Alternatives Considered**: OpenAI GPT (cost prohibitive), Claude (no batch API)

## Architecture Research

### Existing Upload Pipeline Analysis
**Current State**: `POST /api/upload-interaction-json` exists with synchronous processing  
**Issues Identified**:
- Large files (2000+ conversations) could cause API timeouts
- No progress tracking for long-running operations
- Missing job queue integration unlike legacy daily analysis

**Research Finding**: Existing `services/csi_analysis_pipeline.py` already supports batch processing with:
- Concurrent processing with semaphore limits
- 20,000 token context window optimization  
- Comprehensive error handling and retry logic

### Batching Optimization Research
**Current Implementation**: CSIAnalysisPipeline.process_batch()
- Processes conversations in batches with async concurrency control
- Uses batch AI enhancement reducing API calls by 10x
- Implements intelligent context window management (20K tokens)
- Achieves 3-4 interactions/second processing speed

**Best Practices Identified**:
- Batch size: 10 interactions per API call for optimal token usage
- Concurrency: Semaphore-controlled parallel processing
- Error handling: Graceful degradation with individual fallback processing
- Progress tracking: Real-time metrics collection during batch processing

### Constitutional Compliance Research
**AI Micro-Metrics Supremacy**: ✅ Verified existing pipeline uses AI extraction for all CSI calculations  
**Dual CSI Architecture**: ✅ Confirmed `enhanced_analytics_service` maintains calculated + inferred CSI scores  
**Brownfield Compatibility**: ✅ Interaction analysis uses identical methodology to daily analysis at different granularity  

## Performance Research

### Current Benchmarks (from E2E testing)
- **Processing Speed**: 3-4 interactions/second with batch enhancement
- **API Efficiency**: 80% cost reduction via batch processing (2000→200 calls)
- **Context Window**: 20,000 token limit per batch for optimal AI processing
- **Success Rate**: 95%+ interaction detection and CSI calculation accuracy

### Scaling Considerations  
- **Memory Usage**: Batch processing requires careful memory management for large JSON files
- **API Rate Limits**: Gemini batch API provides sufficient throughput for expected workloads
- **Database Performance**: SQLite handles current interaction analysis volume adequately

## Integration Research

### Job Queue System
**Current State**: Legacy daily analysis uses background job queue via `models.Job`  
**Research Finding**: Interaction analysis bypasses job system for synchronous processing  
**Recommendation**: Integrate interaction analysis with existing job queue for consistency

### Progress Tracking Patterns
**Current State**: Daily analysis provides progress updates via upload_id tracking  
**Gap Identified**: Interaction analysis lacks progress monitoring for large uploads  
**Solution**: Implement status endpoint pattern matching existing progress APIs

### Error Handling Patterns
**Best Practice**: Existing `csi_analysis_pipeline.py` implements comprehensive error handling:
- Individual interaction failures don't stop batch processing
- Graceful degradation with detailed error reporting
- Retry logic with exponential backoff for API failures

## Security Research

### File Upload Security
**Current Implementation**: Uses FastAPI UploadFile with content-type validation  
**Best Practices**: JSON structure validation, file size limits, malware scanning consideration  
**Recommendation**: Enhance existing file validation in `services/file_service.py`

### API Rate Limiting  
**Current State**: Relies on Gemini API built-in rate limiting  
**Research Finding**: Batch processing naturally reduces rate limit pressure  
**Enhancement**: Consider client-side rate limiting for additional protection

## Testing Research  

### Existing Test Infrastructure
**Available**: pytest framework with comprehensive test utilities  
**Test Data**: `curated_sample.json` (58 conversations) for validation  
**E2E Pipeline**: `utils/test_e2e_interaction_pipeline.py` demonstrates full workflow

### Constitutional Compliance Testing
**Required Tests**:
- Verify AI micro-metrics pipeline preservation
- Validate dual CSI architecture (calculated vs inferred)
- Confirm backward compatibility with daily analysis
- Ensure no rule-based calculation introduction

### Performance Testing Requirements
- Large JSON processing (2000+ conversations)
- API timeout prevention validation
- Batch optimization verification (80% cost reduction target)
- Context window limit compliance testing

## Decision Log

| Decision | Rationale | Impact |
|----------|-----------|--------|
| Enhance existing upload endpoint | Proven architecture with batch optimization | Low risk, high value enhancement |
| Add async job queue integration | Consistency with daily analysis pattern | Improved reliability for large files |  
| Implement progress tracking API | User experience improvement for long operations | New endpoint development required |
| Maintain existing batch parameters | 20K token context window already optimized | No changes to core AI processing |
| Use existing test infrastructure | Comprehensive pytest framework available | Faster test development cycle |

## Unknown Resolution

All technical uncertainties from the feature specification have been resolved:
- ✅ Context window size: 20,000 tokens per batch (existing implementation)
- ✅ Batching strategy: 10 interactions per API call with concurrent processing
- ✅ Tech stack integration: FastAPI + SQLite + Gemini already proven
- ✅ Performance targets: 3-4 interactions/second achievable with current architecture