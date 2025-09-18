# API Contracts: Interaction Analysis Endpoints

## Overview
This document defines the API contracts for interaction analysis endpoints with JSON upload and batching optimization functionality.

## Base Configuration
- **Base URL**: `/api`
- **Content-Type**: `application/json` (except file uploads: `multipart/form-data`)
- **Authentication**: Not required (internal service)
- **Rate Limiting**: Handled by Gemini API batch processing

## Upload Endpoints

### POST /upload-interaction-json
**Purpose**: Upload JSON file for interaction-based analysis with optimized batching

#### Request
```http
POST /api/upload-interaction-json
Content-Type: multipart/form-data

Parameters:
- file: File (required) - JSON file containing conversation data
- mode: string = "interaction" (default)  
- force_reprocess: boolean = false (optional)
```

#### Response (202 Accepted)
```json
{
  "message": "Successfully processed {X} conversations with {Y} interactions",
  "upload_id": "uuid-string",
  "status": "completed|processing|failed",
  
  "conversations_processed": 150,
  "interactions_detected": 450, 
  "interactions_analyzed": 435,
  
  "avg_csi_score": 6.75,
  "avg_effectiveness": 6.2,
  "avg_efficiency": 7.1,
  "avg_effort": 6.8, 
  "avg_empathy": 6.9,
  
  "processing_time_seconds": 125.5,
  "total_tokens_used": 45000,
  "api_calls_made": 45,
  
  "success_rate": 0.967,
  "error_count": 15,
  
  "progress_url": "/api/upload-interaction-json/{upload_id}/status",
  
  "started_at": "2025-09-17T10:30:00Z",
  "completed_at": "2025-09-17T10:32:05Z"
}
```

#### Error Responses
```json
// 400 Bad Request - Invalid file format
{
  "detail": "Invalid JSON format in uploaded file",
  "error_code": "INVALID_FILE_FORMAT",
  "upload_id": null
}

// 413 Payload Too Large - File size exceeded  
{
  "detail": "File size exceeds maximum limit of 100MB",
  "error_code": "FILE_TOO_LARGE", 
  "max_size_mb": 100
}

// 422 Unprocessable Entity - Invalid JSON structure
{
  "detail": "JSON structure does not match expected conversation format",
  "error_code": "INVALID_JSON_STRUCTURE",
  "expected_fields": ["conversations", "messages"]
}

// 500 Internal Server Error - Processing failure
{
  "detail": "Interaction analysis processing failed",
  "error_code": "PROCESSING_FAILED",
  "upload_id": "uuid-string",
  "retry_available": true
}
```

## Status Monitoring Endpoints

### GET /upload-interaction-json/{upload_id}/status  
**Purpose**: Monitor progress of interaction analysis processing

#### Request
```http
GET /api/upload-interaction-json/{upload_id}/status
```

#### Response (200 OK)
```json
{
  "upload_id": "uuid-string",
  "job_id": 123,
  "status": "running|completed|failed|pending",
  
  "progress_percentage": 75.5,
  "current_stage": "ai_analysis|parsing|detection|completion", 
  "estimated_completion_minutes": 5,
  
  "total_conversations": 200,
  "processed_conversations": 151,
  "total_interactions": 600,
  "processed_interactions": 453,
  
  "current_batch_number": 8,
  "total_batches": 12,
  
  "processing_speed_interactions_per_second": 3.2,
  "elapsed_time_seconds": 145.8,
  
  "avg_csi_score": 6.8, // null if processing
  "success_rate": 0.95,
  
  "error_count": 12,
  "recent_errors": [
    "API rate limit exceeded, retrying...",
    "Invalid interaction boundary detected"
  ],
  
  "started_at": "2025-09-17T10:30:00Z",
  "last_updated_at": "2025-09-17T10:32:25Z", 
  "estimated_completion_at": "2025-09-17T10:35:00Z"
}
```

#### Error Responses
```json  
// 404 Not Found - Upload ID not found
{
  "detail": "Upload session not found", 
  "error_code": "UPLOAD_NOT_FOUND",
  "upload_id": "uuid-string"
}
```

## Configuration Endpoints

### GET /batch-config
**Purpose**: Retrieve current batching configuration and optimization settings

#### Request
```http
GET /api/batch-config
```

#### Response (200 OK)
```json
{
  "context_window_size": 20000,
  "batch_size_interactions": 10,
  "max_concurrent_batches": 5,
  "timeout_seconds": 300,
  
  "performance_targets": {
    "interactions_per_second": 3.5,
    "api_cost_reduction_percentage": 80,
    "success_rate_minimum": 0.95
  },
  
  "current_performance": {
    "avg_processing_speed": 3.2,
    "actual_cost_reduction": 83,
    "recent_success_rate": 0.967
  },
  
  "optimization_enabled": true,
  "last_updated": "2025-09-17T08:00:00Z"
}
```

## Enhanced Interaction Endpoints (Existing)

### GET /interaction-metrics/{interaction_id}
**Purpose**: Retrieve detailed analysis for specific interaction with dual CSI

#### Response Enhancement
```json
{
  "interaction_id": 123,
  "conversation_id": 456, 
  
  "start_time": "2025-08-18T10:55:25Z",
  "end_time": "2025-08-18T14:58:35Z",
  "duration_minutes": 243.17,
  "message_count": 24,
  
  // Constitutional Dual CSI Architecture
  "csi_score": 6.75,        // PRIMARY: from AI micro-metrics
  "inferred_csi": 6.82,     // SECONDARY: AI blackbox
  
  // Four Pillars (from AI micro-metrics)
  "effectiveness_score": 6.2,
  "efficiency_score": 7.1,
  "effort_score": 6.8,
  "empathy_score": 6.9,
  
  "confidence_level": 0.92,
  "detection_method": "ai_boundary_detection",
  "token_usage": 1250,
  "processing_time_seconds": 2.3,
  
  "analysis_quality": "high",
  "anomaly_flags": []
}
```

## Batch Processing Internal Endpoints

### POST /internal/batch-process
**Purpose**: Internal endpoint for batch processing optimization (not public)

#### Request
```json
{
  "conversation_ids": [123, 124, 125],
  "batch_config": {
    "context_window_size": 20000,
    "max_interactions_per_batch": 10
  },
  "job_id": 456
}
```

#### Response  
```json
{
  "batch_id": "batch-uuid",
  "conversations_processed": 3,
  "interactions_analyzed": 28, 
  "avg_csi_score": 6.85,
  "processing_time_seconds": 15.2,
  "token_usage": 18500,
  "success_rate": 1.0,
  "errors": []
}
```

## WebSocket Status Updates (Optional Enhancement)

### WS /upload-interaction-json/{upload_id}/updates
**Purpose**: Real-time progress updates for long-running uploads

#### Message Format
```json
{
  "type": "progress_update",
  "upload_id": "uuid-string",
  "progress_percentage": 45.2,
  "current_stage": "ai_analysis",
  "interactions_processed": 271,
  "current_batch": 6,
  "timestamp": "2025-09-17T10:31:15Z"
}

{
  "type": "batch_completed", 
  "batch_number": 6,
  "interactions_in_batch": 10,
  "avg_batch_csi": 6.9,
  "processing_time_seconds": 3.2
}

{
  "type": "processing_complete",
  "final_results": {
    // Same as upload response
  }
}

{
  "type": "error",
  "error_message": "Batch processing failed, retrying...",
  "retry_attempt": 2,
  "recoverable": true
}
```

## Error Codes Reference

| Code | Description | HTTP Status | Recoverable |
|------|-------------|-------------|-------------|
| `INVALID_FILE_FORMAT` | File is not valid JSON | 400 | No |
| `FILE_TOO_LARGE` | File exceeds size limit | 413 | No |
| `INVALID_JSON_STRUCTURE` | JSON missing required fields | 422 | No |
| `PROCESSING_FAILED` | Analysis pipeline failed | 500 | Yes |
| `UPLOAD_NOT_FOUND` | Upload session not found | 404 | No |
| `BATCH_TIMEOUT` | Batch processing timeout | 504 | Yes |
| `API_RATE_LIMITED` | Gemini API rate limit hit | 429 | Yes |
| `CONTEXT_WINDOW_EXCEEDED` | Batch too large for context | 400 | Yes |

## Performance Guarantees

### Response Time Targets
- Upload initiation: < 2 seconds
- Status check: < 500ms  
- Configuration retrieval: < 200ms

### Processing Targets  
- Small files (< 100 conversations): < 30 seconds
- Medium files (100-1000 conversations): < 5 minutes
- Large files (1000+ conversations): Background processing with progress tracking

### Reliability Targets
- Upload success rate: > 99%
- Processing success rate: > 95%
- API availability: > 99.9%