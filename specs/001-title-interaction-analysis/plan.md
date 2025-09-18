# Implementation Plan: Interaction Analysis Endpoints with JSON Upload and Batching Optimization

**Branch**: `001-title-interaction-analysis` | **Date**: September 17, 2025 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `D:\proj-d\PowerPulse\specs\001-title-interaction-analysis\spec.md`

## Execution Flow (/plan command scope)
```
1. Load feature spec from Input path
   → ✅ Feature spec loaded successfully
2. Fill Technical Context (scan for NEEDS CLARIFICATION)
   → ✅ Project Type: FastAPI backend with SQLite and Gemini AI
   → ✅ Structure Decision: Single project (existing brownfield)
3. Fill the Constitution Check section based on the content of the constitution document.
   → ✅ Constitution requirements analyzed
4. Evaluate Constitution Check section below
   → ✅ No violations detected - AI micro-metrics architecture preserved
   → ✅ Progress Updated: Initial Constitution Check
5. Execute Phase 0 → research.md
   → ✅ Research phase complete
6. Execute Phase 1 → contracts, data-model.md, quickstart.md, GEMINI.md
   → ✅ Design artifacts generated
7. Re-evaluate Constitution Check section
   → ✅ Post-design constitution check passed
   → ✅ Progress Updated: Post-Design Constitution Check
8. Plan Phase 2 → Task generation approach described
   → ✅ Ready for /tasks command
9. STOP - Ready for /tasks command
```

## Summary
Enhance the existing PowerPulse interaction analysis pipeline to ensure JSON upload endpoints are fully functional with optimized batching for large conversation datasets. Build upon the existing FastAPI backend, SQLite database, and Gemini AI integration while maintaining constitutional compliance with AI micro-metrics supremacy and dual CSI architecture.

## Technical Context
**Language/Version**: Python 3.11+ (existing codebase)  
**Primary Dependencies**: FastAPI, SQLAlchemy, Gemini API, Pydantic (existing stack)  
**Storage**: SQLite database (existing powerpulse.db)  
**Testing**: pytest with existing test infrastructure  
**Target Platform**: Linux server deployment with Docker support  
**Project Type**: Single project (brownfield enhancement)  
**Performance Goals**: 20,000 token context window batching, 3-4 interactions/second processing  
**Constraints**: Maintain backward compatibility, preserve dual CSI architecture  
**Scale/Scope**: Handle 2000+ conversations with 80% API cost reduction via batching

**User-Provided Context**: FastAPI backend framework, SQLite DB, Gemini for AI, existing tech stack referenced from codebase structure and foundation.

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Initial Constitution Check: ✅ PASS
- ✅ **AI Micro-Metrics Supremacy**: Feature preserves existing AI micro-metrics → Four Pillars → Weighted CSI pipeline
- ✅ **Dual CSI Architecture**: Maintains calculated CSI (primary) and inferred CSI (comparison) storage
- ✅ **Test-Driven Development**: All enhancements include comprehensive testing requirements
- ✅ **Brownfield Compatibility**: Enhances existing interaction analysis without breaking daily pipeline
- ✅ **AI Agent Integration**: Leverages Gemini CLI for batch processing optimization

### Post-Design Constitution Check: ✅ PASS
- ✅ **No rule-based calculations introduced**: All CSI calculations continue using AI micro-metrics
- ✅ **Backward compatibility preserved**: Daily analysis pipeline remains unchanged
- ✅ **Dual CSI exposure**: API responses include both calculated and inferred CSI scores
- ✅ **Test coverage mandated**: TDD approach with unit, integration, and constitutional compliance tests

## Project Structure

### Documentation (this feature)
```
specs/001-title-interaction-analysis/
├── plan.md              # This file (/plan command output)
├── research.md          # Phase 0 output (/plan command)
├── data-model.md        # Phase 1 output (/plan command)
├── quickstart.md        # Phase 1 output (/plan command)
├── contracts/           # Phase 1 output (/plan command)
└── tasks.md             # Phase 2 output (/tasks command - NOT created by /plan)
```

### Source Code (existing repository structure)
```
# Existing PowerPulse structure (brownfield)
routes/
├── upload.py                    # ✅ Has upload-interaction-json endpoint
├── interaction_metrics.py       # ✅ Interaction CSI metrics
├── interaction_conversations.py # ✅ Interaction explorer
├── interaction_charts.py        # ✅ Interaction analytics
└── interaction_export.py        # ✅ Interaction data export

services/
├── csi_analysis_pipeline.py     # ✅ Core batch processing pipeline
├── enhanced_analytics_service.py # ✅ AI micro-metrics analysis
├── gemini_service.py            # ✅ Gemini AI integration
└── file_service.py              # ✅ JSON upload processing

models.py                        # ✅ InteractionAnalysis, Job entities
database.py                      # ✅ SQLite session management
schemas.py                       # ✅ API response models
```

**Structure Decision**: Existing single project structure maintained (brownfield enhancement)

## Phase 0: Outline & Research

### Research Completed ✅

**Key Findings from Codebase Analysis:**

1. **Existing Upload Endpoint**: `/api/upload-interaction-json` already exists in `routes/upload.py`
   - ✅ Processes JSON files via OptimizedFileService
   - ✅ Uses CSIAnalysisPipeline with dual CSI processing
   - ⚠️ Synchronous execution could timeout on large files

2. **Batch Processing Architecture**: `services/csi_analysis_pipeline.py`
   - ✅ Implements batch AI processing reducing API calls from 2000→200 (80% cost reduction)
   - ✅ Uses 20,000 token context windows for batch efficiency
   - ✅ Supports concurrent processing with semaphore limits

3. **Constitutional Compliance**: Existing implementation
   - ✅ Preserves AI micro-metrics → Four Pillars → Weighted CSI pipeline
   - ✅ Maintains dual CSI architecture (calculated + inferred)
   - ✅ Uses enhanced_analytics_service for AI-driven analysis

**Output**: Research findings documented - existing infrastructure largely supports requirements

## Phase 1: Design & Contracts

### Data Model Enhancements

**Existing Entities (preserved):**
- `InteractionAnalysis` - Individual interaction records with CSI scores
- `Job` - Batch processing tasks with progress tracking  
- `BatchResult` - Aggregated processing results
- `Upload Session` - File upload metadata and status

**New/Enhanced Entities:**
- `BatchContext` - Context window management for optimal AI processing
- `ProcessingMetrics` - Detailed batch performance tracking

### API Contract Enhancements

**Primary Endpoint** (existing): `POST /api/upload-interaction-json`
- ✅ Accepts multipart/form-data JSON uploads
- ✅ Returns interaction count and average CSI
- 🔧 **Enhancement needed**: Add progress tracking for large files

**Status Monitoring** (new): `GET /api/upload-interaction-json/{upload_id}/status`
- Track processing progress for long-running uploads
- Return batch completion metrics and intermediate results

**Batch Configuration** (new): `GET /api/batch-config`
- Expose current batching parameters (context window, concurrent limits)
- Allow runtime optimization adjustments

### Testing Strategy

**Constitutional Compliance Tests:**
- Verify AI micro-metrics pipeline preservation
- Validate dual CSI architecture maintenance
- Confirm backward compatibility with daily analysis

**Integration Tests:**
- Large JSON file processing with batching
- Context window limit validation
- API timeout prevention verification

**Performance Tests:**
- 2000+ conversation processing benchmarks
- API cost reduction validation (80% target)
- Processing speed targets (3-4 interactions/second)

### Agent Context Update

Generated `GEMINI.md` with current implementation context for Gemini CLI integration during development.

**Output**: Design artifacts created - contracts/, data-model.md, quickstart.md, GEMINI.md

## Phase 2: Task Planning Approach
*This section describes what the /tasks command will do - DO NOT execute during /plan*

**Task Generation Strategy**:
- Enhance existing upload endpoint for async processing and progress tracking
- Add new status monitoring endpoints with proper error handling
- Implement comprehensive test coverage following TDD principles
- Validate constitutional compliance through automated tests

**Ordering Strategy**:
- TDD order: Tests first, then implementation enhancements
- Dependencies: API contract tests → endpoint enhancements → integration validation
- Parallel tasks: Independent route enhancements can run concurrently [P]

**Estimated Output**: 15-20 focused tasks addressing upload reliability, progress tracking, and comprehensive testing

**IMPORTANT**: This phase is executed by the /tasks command, NOT by /plan

## Phase 3+: Future Implementation
*These phases are beyond the scope of the /plan command*

**Phase 3**: Task execution (/tasks command creates tasks.md)  
**Phase 4**: Implementation (execute tasks.md following constitutional principles)  
**Phase 5**: Validation (run tests, execute quickstart.md, performance validation)

## Complexity Tracking
*No constitutional violations identified - existing architecture already compliant*

| Area | Consideration | Resolution |
|------|---------------|------------|
| Synchronous Processing | Large files could timeout | Add async job queue integration |
| Batching Optimization | Balance context window vs API calls | Use existing 20K token batching |
| Progress Tracking | No current upload progress API | Add status monitoring endpoints |

## Progress Tracking
*This checklist is updated during execution flow*

**Phase Status**:
- [x] Phase 0: Research complete (/plan command)
- [x] Phase 1: Design complete (/plan command)  
- [x] Phase 2: Task planning complete (/plan command - describe approach only)
- [ ] Phase 3: Tasks generated (/tasks command)
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:
- [x] Initial Constitution Check: PASS
- [x] Post-Design Constitution Check: PASS  
- [x] All NEEDS CLARIFICATION resolved
- [x] Complexity deviations documented

---
*Based on Constitution v2.1.1 - See `.specify/memory/constitution.md`*