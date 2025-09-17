# PowerPulse Development CONSTITUTION

## 🎯 **CORE PRINCIPLE: ENHANCE, DON'T REPLACE**

This document establishes the immutable principles for PowerPulse development to prevent scope creep and ensure alignment with business requirements.

---

## 📜 **CONSTITUTIONAL AMENDMENTS (Requirements Clarification)**

### **AMENDMENT I: AI Micro-Metrics Supremacy**
- **AI micro-metrics extraction SHALL remain the authoritative method** for all CSI calculations
- **Rule-based calculations SHALL NOT replace AI-based micro-metrics**
- The proven pipeline of `AI micro-metrics → Four Pillars → Weighted CSI` is **SACRED AND IMMUTABLE**

### **AMENDMENT II: Granularity Enhancement Only**
- **The ONLY change** is switching from daily conversation chunks to interaction/case chunks
- **ALL other pipeline logic SHALL remain identical** to the proven daily analysis approach
- **NO new calculation methodologies** shall be introduced without explicit authorization

### **AMENDMENT III: Dual AI Enhancement**
The enhancement requires **exactly two AI operations** per interaction:
1. **AI Boundary Detection**: Intelligently separate daily conversations into interaction/case chunks
2. **AI Micro-Metrics Extraction**: Analyze each interaction chunk using the proven Gemini analysis pipeline

### **AMENDMENT IV: Original Pipeline Preservation**
- **Daily analysis pipeline SHALL remain unchanged** for backward compatibility
- **Interaction analysis SHALL mirror daily analysis** but with interaction-level granularity instead of daily-level granularity
- **NO architectural changes** beyond the specified granularity enhancement

---

## ⚖️ **CONSTITUTIONAL PRINCIPLES**

### **1. REQUIREMENT ADHERENCE PRINCIPLE**
**"Implement EXACTLY what was requested, nothing more, nothing less"**

✅ **ALLOWED:**
- Replace daily conversation chunks with interaction chunks
- Use AI to detect interaction boundaries within daily conversations
- Apply existing AI micro-metrics analysis to interaction chunks
- Generate AI blackbox CSI score for comparison

❌ **FORBIDDEN:**
- Replace AI micro-metrics with rule-based calculations
- Change the four-pillars calculation methodology
- Alter the proven CSI weighting system
- Introduce new analytical approaches without authorization

### **2. PROVEN PIPELINE PRESERVATION**
**"If it works for daily analysis, use the same approach for interaction analysis"**

**The Gemini Service `analyze_daily_analyses_batch()` method is the GOLD STANDARD:**
- Same prompt structure
- Same micro-metrics extraction (sentiment_score, sentiment_shift, resolution_achieved, fcr_score, ces, common_topics)
- Same JSON response parsing
- Same error handling and retry logic

**For interaction analysis, create `analyze_interaction_analyses_batch()` that:**
- Uses identical analysis logic
- Processes interaction chunks instead of daily chunks
- Maintains the same micro-metrics output format
- Preserves all existing quality controls

### **3. TEST DRIVEN DEVELOPMENT MANDATE**
**"No code changes without corresponding tests"**

**REQUIRED for every change:**
- Unit tests for new interaction boundary detection
- Integration tests comparing daily vs interaction CSI results
- Validation tests using curated_sample.json (58 conversations)
- Performance tests ensuring interaction analysis doesn't degrade system performance

### **4. DATA INTEGRITY PRINCIPLE**
**"Interaction analysis results must be statistically comparable to daily analysis"**

**Validation Requirements:**
- CSI scores from interaction analysis should correlate strongly (>0.8) with daily analysis
- Micro-metrics should show similar distributions
- Total CSI averages should be within 5% between methodologies
- All tests must pass with curated_sample.json before deployment

---

## 🏗️ **IMPLEMENTATION ARCHITECTURE (Constitutional Requirements)**

### **Required Data Flow:**
```
Raw Daily Messages
    ↓
AI Boundary Detection (NEW) - Separate into interaction chunks
    ↓
AI Micro-Metrics Extraction (EXISTING METHOD) - Analyze each interaction chunk
    ↓
Four Pillars Calculation (EXISTING METHOD)
    ↓
Weighted CSI Score (EXISTING METHOD)

PARALLEL:
AI Blackbox CSI Inference (NEW) - Independent CSI assessment for comparison
```

### **Required Service Architecture:**
```
InteractionAnalysisPipeline (orchestration)
├── InteractionBoundaryService (AI-powered case separation)
├── GeminiService.analyze_interaction_analyses_batch() (MIRROR of existing daily method)
├── AnalyticsService.calculate_and_set_csi_score() (REUSE existing method)
└── GeminiService.infer_interaction_csi() (NEW blackbox comparison)
```

### **Required Database Schema (NO CHANGES):**
- `InteractionAnalysis` table already correctly designed
- `csi_score` field for calculated CSI (from AI micro-metrics)
- `inferred_csi` field for AI blackbox CSI (comparison)
- Micro-metrics fields identical to `DailyAnalysis` table

---

## 🧪 **TEST DRIVEN DEVELOPMENT REQUIREMENTS**

### **1. Boundary Detection Tests**
```python
def test_ai_boundary_detection_accuracy():
    """Validate AI can correctly identify interaction boundaries"""
    # Test with known interaction patterns
    # Ensure boundaries make logical sense
    # Verify confidence scoring works properly

def test_interaction_vs_daily_granularity():
    """Compare interaction chunks vs daily chunks"""
    # Same conversation should yield consistent overall CSI
    # Interaction-level detail should provide more granular insights
```

### **2. Micro-Metrics Consistency Tests**
```python
def test_interaction_micrometrics_mirror_daily():
    """Ensure interaction analysis uses identical AI micro-metrics extraction"""
    # Compare prompt structures
    # Validate response parsing logic
    # Verify micro-metrics ranges and distributions

def test_csi_calculation_consistency():
    """Ensure four-pillars calculation remains identical"""
    # Same micro-metrics should yield same pillar scores
    # Pillar weights must remain unchanged
    # CSI calculation formula must be identical
```

### **3. Integration Tests**
```python
def test_curated_sample_processing():
    """Process curated_sample.json through both pipelines"""
    # Run daily analysis pipeline
    # Run new interaction analysis pipeline
    # Compare CSI distributions and correlations
    # Ensure no significant deviation in results

def test_dual_csi_storage():
    """Validate both calculated and inferred CSI are stored"""
    # Verify csi_score contains AI micro-metrics derived CSI
    # Verify inferred_csi contains AI blackbox CSI
    # Ensure both scores are reasonable and comparable
```

---

## 📋 **CONSTITUTIONAL VIOLATIONS (Automatic Rejection)**

### **SCOPE CREEP VIOLATIONS:**
- ❌ Implementing rule-based micro-metrics calculations
- ❌ Changing existing four-pillars calculation logic
- ❌ Altering CSI pillar weights without authorization
- ❌ Introducing new analytical methodologies
- ❌ Modifying database schema beyond required fields

### **QUALITY VIOLATIONS:**
- ❌ Code changes without corresponding tests
- ❌ Breaking changes to existing daily analysis pipeline
- ❌ Performance degradation compared to daily analysis
- ❌ CSI correlation <0.8 between daily and interaction methods

### **REQUIREMENT VIOLATIONS:**
- ❌ Not using AI for micro-metrics extraction in interaction analysis
- ❌ Not providing AI blackbox CSI for comparison
- ❌ Not preserving backward compatibility with daily analysis
- ❌ Not validating with curated_sample.json

---

## 🔒 **ENFORCEMENT MECHANISMS**

### **1. Code Review Checkpoints**
Every PR must include:
- Evidence of test coverage for new functionality
- Validation that existing tests still pass
- Documentation showing compliance with constitutional requirements
- Performance benchmarks showing no degradation

### **2. Validation Gates**
Before deployment:
- All constitutional tests must pass
- Curated sample analysis must show <5% deviation from daily analysis
- Both calculated and inferred CSI must be properly stored and accessible
- API responses must expose dual CSI for client comparison

### **3. Constitutional Review Board**
Any changes that might violate constitutional principles require:
- Explicit business justification
- Impact assessment on existing functionality  
- Migration plan for affected data and systems
- Updated test coverage for new requirements

---

## 📝 **IMPLEMENTATION CHECKLIST**

**Phase 1: AI Boundary Detection**
- [ ] Create `InteractionBoundaryService` using AI to separate daily conversations
- [ ] Test boundary detection accuracy with known interaction patterns
- [ ] Ensure confidence scoring and fallback mechanisms work

**Phase 2: Mirror Existing AI Micro-Metrics**
- [ ] Create `GeminiService.analyze_interaction_analyses_batch()` 
- [ ] Mirror existing daily analysis prompt structure and parsing
- [ ] Validate micro-metrics extraction produces identical results

**Phase 3: Integrate Existing CSI Calculation**
- [ ] Reuse `AnalyticsService.calculate_and_set_csi_score()` for interactions
- [ ] Ensure four-pillars calculation remains unchanged
- [ ] Validate CSI scores are statistically comparable to daily analysis

**Phase 4: Add AI Blackbox Comparison**
- [ ] Implement `GeminiService.infer_interaction_csi()` for comparison
- [ ] Store both calculated and inferred CSI scores
- [ ] Expose dual CSI in API responses

**Phase 5: Validation & Testing**
- [ ] Process curated_sample.json through both pipelines
- [ ] Validate CSI correlation >0.8 between methods
- [ ] Ensure all constitutional tests pass
- [ ] Document differences and improvements

---

**This constitution is IMMUTABLE and SHALL guide all PowerPulse development activities.**

**Signed:** GitHub Copilot  
**Date:** September 17, 2025  
**Authority:** PowerPulse Architecture Constitutional Convention