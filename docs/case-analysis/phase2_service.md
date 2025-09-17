# Phase 2: New Interaction Service Implementation

**Date**: September 16, 2025  
**Status**: In Progress  
**Objective**: Implement `services/interaction_service.py` with rule-based detection and AI fallback

## Context Summary

Building on Phase 1 specifications, implementing the core interaction detection service that will:

1. **Rule-Based Detection** (Primary): Time gaps, resolution keywords, escalation signals
2. **AI Fallback Detection** (Secondary): For complex cases >20 messages with no clear boundaries  
3. **Utility-Specific Patterns**: Handle Kenya Power patterns (outages, reference numbers, escalations)

## Implementation

### Rule-Based Detection Logic

**Priority Order**:
1. Time gaps >4 hours (configurable)
2. Resolution keywords + closure patterns  
3. Escalation signals ("Attention", "again", "urgent")
4. Reference number changes (new complaint IDs)
5. Topic shifts (outage → billing)

**Performance Target**: Handle 90%+ cases without AI calls to maintain cost efficiency.

## Integration Strategy

- **Minimal Integration**: Service operates standalone, can be called from existing file processing
- **Optional Mode**: Add interaction detection as opt-in flag in `file_service_optimized.py`
- **Backward Compatibility**: No changes to existing daily analysis flow

## Success Criteria

- ✅ Service detects Claude's sample patterns (Daniel W*, Judy K*, Cliff A*)
- ✅ Unit tests pass for all detection scenarios
- ✅ Performance target: <10% cases require AI fallback
- ✅ No dependencies on existing services (standalone operation)

---

## Implementation Status

**Next**: Implement the actual service code with rule-based detection logic.