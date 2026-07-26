# BABOK / PMBOK Methodology

Project management lifecycle aligned to **BABOK®** (Business Analysis) and **PMBOK®** (Project Management) for the KSF Stock Market Analysis System.

## 1. BABOK Knowledge Areas

| Knowledge Area | Current Artifact | Status |
|---|---|---|
| Business Analysis Planning & Monitoring | `docs/requirements/requirements-specification.md` | Complete |
| Elicitation & Collaboration | BRD stakeholder analysis, advisor hiring UI | Complete |
| Requirements Life Cycle Management | `docs/requirements/traceability-matrix.md` | Complete |
| Strategy Analysis | `docs/requirements/business-requirements.md` | Complete |
| Solution Evaluation | ATR backtest results, rule engine metrics | In Progress |

## 2. PMBOK Process Groups

### 2.1 Initiating
- Project charter approved (Kevin Fraser, ksfraser.ca)
- Business case: legacy modernization, 2013 backup trauma, TA bottleneck, scoring preservation

### 2.2 Planning
- Requirements management plan: BABOK-format docs in `/docs`
- Scope statement: BR-1 through BR-7, FR-1 through FR-105
- Schedule: phased approach (Phase 1–6 in architecture-document.md)
- Risk management: optional_rules formalize known investment risks
- Quality management: BABOK-format documentation mandatory (NFR-4.4)

### 2.3 Executing
- Incremental delivery by phase
- Advisor hiring framework, multi-gateway recommendations, optional rules executed in Phase 3
- ATR 2.5x methodology validated via backtest

### 2.4 Monitoring & Controlling
- Traceability matrix maps BR → FR → US → DB/PHP/Python/Status
- Backtest metrics (return, drawdown, win rate) validate solution fitness
- Cron-based alerting for pipeline failures
- Migration-based schema management prevents drift

### 2.5 Closing
- Phase completion criteria in BRD acceptance criteria
- Documentation updates tied to phase deliverables

## 3. Deliverable Mapping

| Deliverable | BABOK / PMBOK Reference | Location |
|---|---|---|
| Business Requirements Document | BABOK BRD, PMBOK Scope Statement | `docs/requirements/business-requirements.md` |
| Requirements Specification | BABOK Requirements Management | `docs/requirements/requirements-specification.md` |
| Traceability Matrix | BABOK Requirements Life Cycle | `docs/requirements/traceability-matrix.md` |
| Solution Design | BABOK Strategy Analysis | `docs/requirements/solution-design.md` |
| Architecture Document | PMBOK Scope Management | `docs/architecture/architecture-document.md` |
| ADRs | BABOK Knowledge Management | `docs/architecture/` |
| Test Plans | BABOK Solution Evaluation, PMBOK Quality | `docs/` planned |
| User Stories | BABOK Elicitation | `docs/user-stories/user-stories.md` |
