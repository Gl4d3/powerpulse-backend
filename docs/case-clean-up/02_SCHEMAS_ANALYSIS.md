# Schemas.py Knowledge Base

## API Contract Analysis

### Core Response Models Architecture

The schemas.py defines the API contracts for client consumption. Critical analysis of CSI-related schemas:

### 1. **CSI Metrics Response Structure** ✅ **CORRECTLY DESIGNED**

**CSIMetricsResponse (Lines 77-96):**
```python
class CSIMetricsResponse(BaseModel):
    # CSI and pillars (0-100 scale for frontend)
    csi: float
    resolution_quality: float  # effectiveness_score * 10
    service_timeliness: float  # efficiency_score * 10
    customer_ease: float       # effort_score * 10
    interaction_quality: float # empathy_score * 10
    
    # Micro-metrics used to calculate the pillars
    sentiment_score: float           # Average sentiment score
    sentiment_shift: float           # Average sentiment shift
    resolution_achieved: float       # Average resolution achieved score
    fcr_score: float                # Average first call resolution score
    ces: float                      # Average customer effort score
    first_response_time: float      # Average first response time (seconds)
    avg_response_time: float        # Average response time (seconds)
    total_handling_time: float      # Average total handling time (minutes)
    
    # Sample and metadata
    sample_count: int
    
    # Deltas and metadata
    deltas: Optional[Dict[str, float]] = None
    pillar_weights: Dict[str, float]
```

**Analysis:**
- ✅ **Proper calculation hierarchy**: Micro-metrics → Pillars → CSI
- ✅ **Scale conversion**: Internal 0-10 scale converted to 0-100 for frontend
- ✅ **Pillar mapping**: Clear naming (resolution_quality = effectiveness_score * 10)
- ✅ **Metadata included**: Sample count, deltas, weights for transparency

### 2. **Interaction-Specific Schemas** ✅ **WELL STRUCTURED**

**InteractionAnalysisResponse (Lines 223-258):**
```python
class InteractionAnalysisResponse(BaseModel):
    interaction_id: int
    conversation_id: str
    # ... standard fields ...
    csi_score: Optional[float] = None           # Calculated CSI (Primary)
    effectiveness_score: Optional[float] = None
    efficiency_score: Optional[float] = None
    effort_score: Optional[float] = None
    empathy_score: Optional[float] = None
    
    # Interaction-specific metrics
    interaction_duration: Optional[float] = None  # in minutes
    message_count: Optional[int] = None
    turns_count: Optional[int] = None
    
    # Detailed micro-metrics (identical to DailyAnalysis)
    sentiment_score: Optional[float] = None
    # ... all micro-metrics ...
```

**InteractionMetricsResponse (Lines 260-294):**
```python
class InteractionMetricsResponse(BaseModel):
    # CSI and pillars (0-100 scale for frontend) - IDENTICAL to CSIMetricsResponse
    csi: float
    resolution_quality: float  # effectiveness_score * 10
    # ... all same fields as CSIMetricsResponse ...
    
    # Interaction-specific aggregations
    avg_interaction_duration: float  # Average interaction duration (minutes)
    avg_message_count: float        # Average messages per interaction
    avg_turns_count: float          # Average turns per interaction
    
    interaction_count: int          # Total interactions analyzed
    interaction_complexity_distribution: Optional[Dict[str, int]] = None
```

**Analysis:**
- ✅ **Consistent API contracts** between daily and interaction analysis
- ✅ **Same CSI calculation approach** for both analysis types
- ✅ **Additional interaction metadata** without breaking core structure
- ✅ **Proper field naming** matches database schema

### 3. **Legacy vs New Analysis Consistency** ✅ **PROPER DUAL SUPPORT**

**DailyAnalysisResponse (Lines 21-49):**
```python
class DailyAnalysisResponse(BaseModel):
    daily_analysis_id: int
    conversation_id: str
    csi_score: Optional[float] = None           # Same field as InteractionAnalysis
    effectiveness_score: Optional[float] = None # Identical structure
    efficiency_score: Optional[float] = None
    effort_score: Optional[float] = None
    empathy_score: Optional[float] = None
    # ... identical micro-metrics ...
```

**Analysis:**
- ✅ **Identical field structure** between daily and interaction responses
- ✅ **Same CSI calculation approach** for consistency
- ✅ **Backward compatibility** maintained for legacy clients

## Critical Schema Findings

### 1. **NO INFERRED_CSI IN API RESPONSES** ⚠️ **MISSING DUAL CSI**

**Issue Identified:**
- Database model has BOTH `csi_score` and `inferred_csi` fields
- API schemas only expose `csi_score` field
- Clients cannot access AI blackbox CSI for comparison

**Missing from schemas:**
```python
# Should be added to InteractionAnalysisResponse
inferred_csi: Optional[float] = None  # AI blackbox CSI (comparison)

# Should be added to InteractionMetricsResponse  
inferred_csi: float                   # Average AI blackbox CSI
csi_comparison_delta: float           # Difference between calculated and inferred
```

### 2. **Scale Conversion Logic** ✅ **CORRECTLY IMPLEMENTED**

**Frontend Scale Conversion (0-100 scale):**
```python
resolution_quality: float  # effectiveness_score * 10
service_timeliness: float  # efficiency_score * 10  
customer_ease: float       # effort_score * 10
interaction_quality: float # empathy_score * 10
```

**Analysis:**
- ✅ **Consistent 10x multiplier** from internal 0-10 to frontend 0-100
- ✅ **Clear field mapping** with descriptive names
- ✅ **Proper data transformation** for client consumption

### 3. **Pillar Weight Configuration** ✅ **FLEXIBLE ARCHITECTURE**

**CSIMetricsResponse includes:**
```python
pillar_weights: Dict[str, float]  # Configurable weights for CSI calculation
deltas: Optional[Dict[str, float]] = None  # Trend comparison
```

**Analysis:**
- ✅ **Configurable CSI calculation** allows business rule adjustments
- ✅ **Transparency** - clients can see how CSI is calculated
- ✅ **Trend analysis support** with delta calculations

## Schema Issues to Address

### 1. **Missing Dual CSI Support** ⚠️ **HIGH PRIORITY**

**Problem:**
- Database stores both calculated and AI inferred CSI
- API schemas only expose calculated CSI
- Clients cannot compare the two approaches

**Solution Required:**
```python
class InteractionAnalysisResponse(BaseModel):
    # Existing fields...
    csi_score: Optional[float] = None      # Calculated CSI (Primary) 
    inferred_csi: Optional[float] = None   # AI Blackbox CSI (Comparison)
    csi_method: str = "calculated"         # Which CSI is primary

class InteractionMetricsResponse(BaseModel):
    # Existing fields...
    csi: float                    # Primary calculated CSI
    inferred_csi: float          # Average AI blackbox CSI  
    csi_comparison_delta: float  # calculated - inferred
    csi_correlation: float       # Correlation coefficient
```

### 2. **Missing Schema Validation** ⚠️ **DATA QUALITY**

**Current issues:**
- Most CSI-related fields are Optional - could return incomplete data
- No validation of scale ranges (0-10 internal, 0-100 frontend)
- No validation of pillar weight sum (should equal 1.0)

### 3. **Inconsistent Naming Patterns**

**Legacy naming:**
```python
avg_csi_score: Optional[float] = None      # DailyAnalysis style
```

**New naming:**
```python  
csi_score: Optional[float] = None          # InteractionAnalysis style
```

## Schema Strengths

1. **✅ Consistent Architecture**: Both daily and interaction use same field structure
2. **✅ Proper Scale Conversion**: 0-10 internal → 0-100 frontend with clear mapping
3. **✅ Comprehensive Metrics**: All micro-metrics and pillars exposed  
4. **✅ Flexible Configuration**: Pillar weights and deltas included
5. **✅ Backward Compatibility**: Legacy schemas maintained alongside new ones

## Recommendations

1. **Add Dual CSI Support**: Expose both calculated and inferred CSI in API responses
2. **Add Schema Validation**: Validate scale ranges and required fields
3. **Standardize Naming**: Consistent field naming patterns across all schemas
4. **Add Comparison Metrics**: CSI delta, correlation, and confidence indicators

---

**Status**: Schema analysis complete - **MOSTLY CORRECT BUT MISSING DUAL CSI**  
**Issue**: API schemas don't expose the inferred_csi field for comparison