# Agent Registry

**Total: 55 agents** (21 review + 5 research + 2 work + 11 utility + 12 investigation + 4 testing)

Shared resources: [Review Checklist](../agents/review/references/review-checklist.md) (self-review and pre-flight for all review agents)

## Review Agents (`agents/review/`)

| Agent | Expertise |
|-------|-----------|
| ward-sentinel | Security vulnerabilities, OWASP, auth, secrets |
| ember-oracle | Performance bottlenecks, N+1 queries, complexity |
| rune-architect | Architecture compliance, layer boundaries, SOLID |
| simplicity-warden | YAGNI, over-engineering, premature abstraction |
| flaw-hunter | Logic bugs, edge cases, race conditions |
| mimic-detector | DRY violations, code duplication |
| pattern-seer | Cross-cutting consistency: naming, error handling, API design, data modeling, auth, state, logging |
| void-analyzer | Incomplete implementations, TODOs, stubs |
| wraith-finder | Dead code, unwired code, DI wiring gaps, orphaned routes/handlers, AI orphan detection |
| phantom-checker | Dynamic references, reflection analysis |
| type-warden | Type safety, mypy strict, Python idioms, async correctness |
| trial-oracle | TDD compliance, test quality, coverage gaps, assertions |
| depth-seer | Missing logic, incomplete state machines, complexity hotspots |
| blight-seer | Design anti-patterns, God Service, leaky abstractions, temporal coupling |
| forge-keeper | Data integrity, migration safety, reversibility, lock analysis, transaction boundaries |
| tide-watcher | Async/concurrency patterns, waterfall awaits, unbounded concurrency, cancellation, race conditions |
| reality-arbiter | Production viability truth-telling, deployment gaps, integration honesty |
| assumption-slayer | Premise validation, cargo cult detection, problem-fit analysis |
| entropy-prophet | Long-term consequence analysis, complexity trajectory, lock-in risks |
| refactor-guardian | Refactoring completeness, orphaned callers, broken import paths |
| reference-validator | Cross-file reference integrity, config path validation, frontmatter schema |

## Research Agents (`agents/research/`)

| Agent | Purpose |
|-------|---------|
| practice-seeker | External best practices and industry patterns |
| repo-surveyor | Codebase exploration and pattern discovery |
| lore-scholar | Framework documentation and API research |
| git-miner | Git history analysis and code archaeology |
| echo-reader | Reads Rune Echoes to surface relevant past learnings |

## Work Agents (`agents/work/`)

| Agent | Purpose |
|-------|---------|
| rune-smith | Code implementation (TDD-aware swarm worker) |
| trial-forger | Test generation (swarm worker) |

## Utility Agents (`agents/utility/`)

| Agent | Purpose |
|-------|---------|
| runebinder | Aggregates Ash findings into TOME.md |
| decree-arbiter | Technical soundness review for plans (9-dimension evaluation) |
| truthseer-validator | Audit coverage validation (Roundtable Phase 5.5) |
| flow-seer | Spec flow analysis and gap detection |
| scroll-reviewer | Document quality review |
| mend-fixer | Parallel code fixer for /rune:mend findings (restricted tools) |
| gap-fixer | Gap remediation fixer for Phase 5.8 — prompt-template-based (no dedicated .md file, uses `skills/roundtable-circle/references/ash-prompts/gap-fixer.md`) |
| knowledge-keeper | Documentation coverage reviewer for plans |
| elicitation-sage | Structured reasoning using BMAD-derived methods (summoned per eligible section, max 6 per forge session) |
| veil-piercer-plan | Plan truth-telling (6-dimension analysis, PASS/CONCERN/BLOCK verdicts) |
| horizon-sage | Strategic depth assessment — Temporal Horizon, Root Cause Depth, Innovation Quotient, Stability, Maintainability |

## Investigation Agents (`agents/investigation/`)

| Agent | Purpose |
|-------|---------|
| data-layer-tracer | Impact tracing across data models, schemas, migrations, and storage layers |
| api-contract-tracer | Impact tracing across API endpoints, contracts, request/response schemas |
| business-logic-tracer | Impact tracing across business rules, domain logic, and workflow orchestration |
| event-message-tracer | Impact tracing across event buses, message queues, pub/sub, and async pipelines |
| config-dependency-tracer | Impact tracing across configuration, environment variables, feature flags, and deployment settings |
| wisdom-sage | Git archaeology — commit intent classification, caution scoring via git blame analysis |
| lore-analyst | Quantitative git history analysis — churn metrics, co-change clustering, ownership concentration |
| goldmask-coordinator | Three-layer synthesis — merges Impact + Wisdom + Lore findings into unified GOLDMASK.md report |
| grace-warden | Correctness & completeness inspector — plan requirement traceability and implementation status |
| ruin-prophet | Failure modes, security posture, and operational readiness inspector |
| sight-oracle | Design alignment, coupling analysis, and performance profiling inspector |
| vigil-keeper | Test coverage, observability, maintainability, and documentation inspector |

## Testing Agents (`agents/testing/`)

| Agent | Purpose |
|-------|---------|
| unit-test-runner | Diff-scoped unit test execution — pytest, jest, vitest (model: sonnet) |
| integration-test-runner | Integration test execution with service dependency management (model: sonnet) |
| e2e-browser-tester | E2E browser testing via agent-browser with file-to-route mapping (model: sonnet) |
| test-failure-analyst | Read-only failure analysis — root cause classification and fix suggestions (maxTurns: 15) |
