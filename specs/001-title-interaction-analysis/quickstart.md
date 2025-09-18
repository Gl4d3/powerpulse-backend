# Quickstart Guide: Interaction Analysis with JSON Upload

## Overview
This quickstart guide demonstrates how to upload conversation JSON files and process them for interaction-level CSI analysis using the enhanced PowerPulse API with optimized batching.

## Prerequisites

### Environment Setup
```bash
# Ensure PowerPulse is running
cd D:\proj-d\PowerPulse
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Verify API is accessible
curl http://localhost:8000/docs
```

### Test Data
Use one of these sample files:
- `attached_assets/curated_sample.json` (58 conversations - recommended)
- `csi_test_data.json` (test conversations)
- Custom JSON file with conversation data

## Basic Upload Flow

### Step 1: Upload JSON File
```bash
curl -X POST "http://localhost:8000/api/upload-interaction-json" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@attached_assets/curated_sample.json" \
  -F "mode=interaction"
```

**Expected Response (202 Accepted):**
```json
{
  "message": "Successfully processed 58 conversations with 174 interactions",
  "upload_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "completed",
  "conversations_processed": 58,
  "interactions_detected": 174,
  "interactions_analyzed": 168,
  "avg_csi_score": 6.42,
  "avg_effectiveness": 6.1,
  "avg_efficiency": 6.8,
  "avg_effort": 6.3,
  "avg_empathy": 6.5,
  "processing_time_seconds": 45.2,
  "total_tokens_used": 28500,
  "api_calls_made": 18,
  "success_rate": 0.966,
  "error_count": 6,
  "progress_url": "/api/upload-interaction-json/123e4567-e89b-12d3-a456-426614174000/status",
  "started_at": "2025-09-17T10:30:00Z",
  "completed_at": "2025-09-17T10:30:45Z"
}
```

### Step 2: Monitor Processing Status (for large files)
```bash
export UPLOAD_ID="123e4567-e89b-12d3-a456-426614174000"
curl "http://localhost:8000/api/upload-interaction-json/${UPLOAD_ID}/status"
```

**Response During Processing:**
```json
{
  "upload_id": "123e4567-e89b-12d3-a456-426614174000",
  "job_id": 156,
  "status": "running",
  "progress_percentage": 65.5,
  "current_stage": "ai_analysis",
  "estimated_completion_minutes": 2,
  "total_conversations": 200,
  "processed_conversations": 131,
  "total_interactions": 600,
  "processed_interactions": 393,
  "current_batch_number": 8,
  "total_batches": 12,
  "processing_speed_interactions_per_second": 3.2,
  "elapsed_time_seconds": 125.8,
  "success_rate": 0.95,
  "error_count": 12,
  "recent_errors": [
    "API rate limit exceeded, retrying..."
  ],
  "started_at": "2025-09-17T10:30:00Z",
  "last_updated_at": "2025-09-17T10:32:05Z",
  "estimated_completion_at": "2025-09-17T10:34:00Z"
}
```

## Advanced Usage Examples

### Large File Upload with Progress Tracking
```bash
# Upload large conversation file
curl -X POST "http://localhost:8000/api/upload-interaction-json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@large_conversations.json" \
  -F "force_reprocess=true"

# Save upload_id from response
UPLOAD_ID=$(echo $RESPONSE | jq -r '.upload_id')

# Monitor progress every 30 seconds
while true; do
  STATUS=$(curl -s "http://localhost:8000/api/upload-interaction-json/${UPLOAD_ID}/status" | jq -r '.status')
  PROGRESS=$(curl -s "http://localhost:8000/api/upload-interaction-json/${UPLOAD_ID}/status" | jq -r '.progress_percentage')
  echo "Status: $STATUS, Progress: $PROGRESS%"
  
  if [[ "$STATUS" == "completed" || "$STATUS" == "failed" ]]; then
    break
  fi
  
  sleep 30
done
```

### Check Batch Configuration
```bash
curl "http://localhost:8000/api/batch-config"
```

**Response:**
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

## Retrieve Analysis Results

### Get Specific Interaction Analysis
```bash
curl "http://localhost:8000/api/interaction-metrics/123"
```

**Response:**
```json
{
  "interaction_id": 123,
  "conversation_id": 456,
  "start_time": "2025-08-18T10:55:25Z",
  "end_time": "2025-08-18T14:58:35Z",
  "duration_minutes": 243.17,
  "message_count": 24,
  "csi_score": 6.75,
  "inferred_csi": 6.82,
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

### Browse All Interactions
```bash
curl "http://localhost:8000/api/interaction-conversations/?page=1&page_size=10&sort_by=csi_score&sort_order=desc"
```

### Export Results to CSV
```bash
curl "http://localhost:8000/api/interaction-export/download?export_type=interactions&min_csi_score=6.0" \
  -o interaction_results.csv
```

## Error Handling Examples

### Invalid File Format
```bash
curl -X POST "http://localhost:8000/api/upload-interaction-json" \
  -F "file=@invalid_file.txt"

# Response: 400 Bad Request
{
  "detail": "Invalid JSON format in uploaded file",
  "error_code": "INVALID_FILE_FORMAT",
  "upload_id": null
}
```

### File Too Large  
```bash
curl -X POST "http://localhost:8000/api/upload-interaction-json" \
  -F "file=@massive_file.json"

# Response: 413 Payload Too Large
{
  "detail": "File size exceeds maximum limit of 100MB",
  "error_code": "FILE_TOO_LARGE",
  "max_size_mb": 100
}
```

### Processing Failure with Retry
```bash
# Initial upload fails
curl -X POST "http://localhost:8000/api/upload-interaction-json" \
  -F "file=@problematic_conversations.json"

# Response: 500 Internal Server Error
{
  "detail": "Interaction analysis processing failed",
  "error_code": "PROCESSING_FAILED",
  "upload_id": "failed-uuid",
  "retry_available": true
}

# Retry the same file
curl -X POST "http://localhost:8000/api/upload-interaction-json" \
  -F "file=@problematic_conversations.json" \
  -F "force_reprocess=true"
```

## Performance Validation

### Verify Batch Optimization
```python
import requests
import time
import json

def test_batch_performance():
    # Upload test file
    with open('attached_assets/curated_sample.json', 'rb') as f:
        response = requests.post(
            'http://localhost:8000/api/upload-interaction-json',
            files={'file': f}
        )
    
    result = response.json()
    
    # Validate performance metrics
    assert result['success_rate'] >= 0.95, f"Success rate too low: {result['success_rate']}"
    assert result['processing_time_seconds'] < 60, f"Processing too slow: {result['processing_time_seconds']}s"
    
    # Check cost reduction (should use batch processing)
    interactions_per_api_call = result['interactions_analyzed'] / result['api_calls_made']
    assert interactions_per_api_call >= 8, f"Batch optimization not working: {interactions_per_api_call} interactions/call"
    
    print(f"✅ Performance test passed:")
    print(f"   Success rate: {result['success_rate']:.1%}")
    print(f"   Processing time: {result['processing_time_seconds']:.1f}s")
    print(f"   Batch efficiency: {interactions_per_api_call:.1f} interactions/API call")

# Run performance test
test_batch_performance()
```

## Constitutional Compliance Validation

### Verify Dual CSI Architecture
```bash
# Get interaction details to confirm dual CSI
INTERACTION_ID=$(curl -s "http://localhost:8000/api/interaction-conversations/?page_size=1" | jq -r '.interactions[0].id')
curl "http://localhost:8000/api/interaction-metrics/${INTERACTION_ID}"

# Verify response contains both CSI scores
# csi_score: PRIMARY (from AI micro-metrics)  
# inferred_csi: SECONDARY (AI blackbox)
```

### Test Backward Compatibility
```bash
# Verify daily analysis still works
curl -X POST "http://localhost:8000/api/upload-json" \
  -F "file=@attached_assets/curated_sample.json"

# Verify daily metrics unchanged
curl "http://localhost:8000/api/metrics/"
```

## Troubleshooting

### Common Issues

1. **Upload Timeout**: For large files, processing continues in background. Use status endpoint.

2. **Low Success Rate**: Check `recent_errors` in status response for specific issues.

3. **API Rate Limits**: Batch processing should handle this automatically with retries.

4. **Memory Issues**: Large files are processed in batches to prevent memory overflow.

### Debug Commands
```bash
# Check service health
curl "http://localhost:8000/health"

# View recent logs
tail -f logs/powerpulse.log

# Check database state
sqlite3 powerpulse.db "SELECT COUNT(*) FROM interaction_analyses;"

# Verify Gemini API access
curl "http://localhost:8000/api/dev/test-gemini"
```

## Expected Results

### Success Criteria
- ✅ File uploads process without timeouts
- ✅ Batch optimization reduces API calls by 80%+
- ✅ Processing speed: 3+ interactions per second
- ✅ Success rate: 95%+ interaction analysis
- ✅ Dual CSI scores present in all responses
- ✅ Progress tracking works for large files
- ✅ Constitutional compliance maintained

### Performance Benchmarks
- Small files (< 100 conversations): < 30 seconds
- Medium files (100-1000 conversations): < 5 minutes  
- Large files (1000+ conversations): Background with progress
- API efficiency: 8-12 interactions per API call
- Memory usage: Stable during large file processing

This quickstart demonstrates the enhanced interaction analysis pipeline with JSON upload and optimized batching while maintaining constitutional compliance with PowerPulse's AI micro-metrics architecture.