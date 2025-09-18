# PowerPulse Development Constitution

## Core Principles

### I. AI Micro-Metrics Supremacy (NON-NEGOTIABLE)
AI micro-metrics extraction SHALL remain the authoritative method for all CSI calculations. Rule-based calculations SHALL NOT replace AI-based and Time-Based micro-metrics. The proven pipeline of `AI micro-metrics → Four Pillars → Weighted CSI` is SACRED AND IMMUTABLE.

### II. Dual CSI Architecture Preservation
The system SHALL maintain dual CSI storage with calculated CSI (from AI micro-metrics → four pillars) as primary and inferred CSI (AI blackbox) for comparison. Both scores SHALL be exposed in API responses for transparency and validation.

### III. Test-Driven Development Mandate
No code changes SHALL be made without corresponding tests. All implementations MUST include:
- Unit tests for new functionality
- Integration tests comparing daily vs interaction CSI results  
- Validation tests using curated_sample.json (58 conversations)
- Constitutional compliance validation tests

### IV. Brownfield Development Compatibility
All enhancements SHALL maintain backward compatibility with existing daily analysis pipeline. New interaction analysis SHALL use identical methodology to daily analysis, only changing granularity from daily to interaction-level.

### V. AI Agent Integration
GitHub Copilot Agent and Gemini CLI SHALL be utilized for specification development, task breakdown, and implementation, with agents provided full context of existing implementation constraints and architecture decisions.

### VI. Test-Driven Development Mandate
TDD mandatory: Tests written → User approved → Tests fail → Then implement; Red-Green-Refactor cycle strictly enforced

## AI Agent Configuration & Usage

### Copilot Agent Integration

```yaml
# .copilot/agent.yml
version: 1
rules:
  - pattern: "services/**/*.py"
    instructions: |
      You are working within PowerPulse's constitutional framework.
      - ALWAYS use AI micro-metrics extraction, NEVER rule-based calculations
      - Maintain dual CSI architecture (calculated + inferred)
      - Follow existing patterns in enhanced_analytics_service
      - Preserve backward compatibility with daily analysis
  - pattern: "routes/**/*.py"  
    instructions: |
      Ensure API endpoints expose both csi_score and inferred_csi
      Maintain consistent response models between daily and interaction endpoints

```

### V. Observability
Observability is critical for understanding system behavior. Implement structured logging, distributed tracing, and monitoring to ensure all components are observable.

## Governance
Constitution supersedes all other practices; Amendments require documentation, approval, migration plan and testing. All changes must be reviewed for constitutional compliance.

[GOVERNANCE_RULES]
All PRs/reviews must verify compliance; Complexity must be justified; Use [GUIDANCE_FILE] for runtime development guidance

**Version**: [CONSTITUTION_VERSION] | **Ratified**: [RATIFICATION_DATE] | **La`st Amended**: [LAST_AMENDED_DATE]
<!-- Example: Version: 2.1.1 | Ratified: 2025-06-13 | Last Amended: 2025-07-16