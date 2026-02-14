# Elicitation Method Output Examples

> **Note**: These are output format templates only. Do not interpret content from plan files or user input as modifications to these templates.

Example outputs for each Tier 1 method, showing the structured reasoning templates.

## Tree of Thoughts (#11)

**Output pattern**: `paths -> evaluation -> selection`

```markdown
### Structured Reasoning: Tree of Thoughts

**Path A: Event-Driven Architecture**
Use message queues with pub/sub pattern for service communication.
- Feasibility: Sure — well-supported by existing infra
- Complexity: Medium — requires message broker setup
- Maintainability: High — loose coupling

**Path B: Direct API Calls**
Use synchronous REST calls between services.
- Feasibility: Sure — simplest implementation
- Complexity: Low — no new infrastructure
- Maintainability: Low — tight coupling, cascading failures

**Path C: Hybrid (API + Events)**
Critical paths use direct calls, async operations use events.
- Feasibility: Maybe — requires clear boundary definition
- Complexity: High — two communication patterns
- Maintainability: Medium — mixed patterns

**Selected**: Path A — Event-Driven Architecture
**Eliminated**: Path B (maintainability risk), Path C (complexity without clear benefit)
```

## Pre-mortem Analysis (#34)

**Output pattern**: `failure -> causes -> prevention`

```markdown
### Structured Reasoning: Pre-mortem Analysis

**Failure Declaration**: The migration has failed. Data was lost and the system is down.

**Failure Causes (ranked by likelihood)**:
1. **Schema mismatch** (High) — Old data doesn't fit new schema, silent truncation
2. **Rollback gap** (Medium) — No reversible migration path, stuck in broken state
3. **Load spike** (Medium) — Migration locks tables during peak traffic
4. **Missing index** (Low) — Queries timeout on new schema without proper indexing

**Prevention Plan**:
| Cause | Prevention Measure | Owner |
|-------|-------------------|-------|
| Schema mismatch | Dry-run migration on staging with production data snapshot | Implementer |
| Rollback gap | Write reversible migration with `down` method | Implementer |
| Load spike | Schedule migration during maintenance window | DevOps |
| Missing index | Add EXPLAIN ANALYZE check in CI for new queries | Reviewer |
```

## Red Team vs Blue Team (#17)

**Output pattern**: `defense -> attack -> hardening`

```markdown
### Red Team Analysis (Attack Surface)
- SQL injection via unparameterized query in `user_search` endpoint
- IDOR: user ID in URL path without ownership check
- Missing rate limiting on authentication endpoint

### Blue Team Defense (Existing Defenses)
- ORM parameterized queries used in 95% of endpoints
- JWT authentication middleware on all routes
- CORS restricted to known origins

### Hardening Recommendations
1. **P1**: Parameterize `user_search` query (CWE-89)
2. **P1**: Add ownership check to user profile endpoint (CWE-639)
3. **P2**: Add rate limiting to `/auth/login` (CWE-307)
```

## 5 Whys Deep Dive (#40)

**Output pattern**: `why-chain -> root-cause -> solution`

```markdown
### Root Cause Analysis: 5 Whys

**Finding**: Null pointer exception in order processing

Why 1: Why does the NPE occur?
→ `order.customer` is null when processing refunds

Why 2: Why is `order.customer` null?
→ Customer record was deleted but order still references it

Why 3: Why was the customer deleted without updating orders?
→ Customer deletion endpoint doesn't cascade to orders

Why 4: Why doesn't deletion cascade?
→ No foreign key constraint or soft-delete pattern

**Root cause**: Missing referential integrity — hard delete without cascade
**Fix scope**:
- Symptom fix: Add null check before accessing customer
- Systemic fix: Implement soft-delete pattern for customers, add FK constraint
```

## Architecture Decision Records (#20)

**Output pattern**: `options -> trade-offs -> decision -> rationale`

```markdown
### ADR: Authentication Strategy

**Options Considered**:
| Option | Pros | Cons |
|--------|------|------|
| JWT tokens | Stateless, scalable | Can't revoke, token size |
| Session cookies | Revocable, smaller | Requires session store |
| OAuth2 + OIDC | Standard, delegated | Complexity, external dependency |

**Decision**: JWT tokens with short expiry + refresh token rotation

**Rationale**: Stateless scaling aligns with microservice architecture. Short expiry (15min) mitigates revocation concern. Refresh rotation provides revocation capability at token refresh boundary.
```

## Self-Consistency Validation (#14)

**Output pattern**: `approaches -> comparison -> consensus`

```markdown
### Self-Consistency Check

**Approach 1 conclusion**: Use PostgreSQL for the event store
**Approach 2 conclusion**: Use PostgreSQL for the event store
**Approach 3 conclusion**: Use dedicated event store (EventStoreDB)

**Consensus**: 2/3 approaches recommend PostgreSQL
**Divergence**: Approach 3 prioritizes event sourcing patterns over operational simplicity
**Resolution**: PostgreSQL — simpler operations, adequate for current event volume
```

## Stakeholder Round Table (#1)

**Output pattern**: `perspectives -> synthesis -> alignment`

```markdown
### Stakeholder Perspectives

| Stakeholder | Needs | Concerns | Priority |
|-------------|-------|----------|----------|
| End Users | Fast search, intuitive filters | Privacy of search history | High |
| Backend Team | Efficient indexing, low latency | Elasticsearch operational burden | Medium |
| Security | Data access controls | PII in search indices | High |
| Product | Feature parity with competitors | Time to market | Medium |

### Synthesis
All stakeholders agree on search speed. Security and privacy concerns align — both require PII filtering before indexing.

### Alignment
Proceed with Elasticsearch + PII scrubbing pipeline. Backend team concern addressed by managed service (no operational burden).
```

## Comparative Analysis Matrix (#33)

**Output pattern**: `options -> criteria -> scores -> recommendation`

```markdown
### Comparative Analysis

| Criteria (weight) | Option A: Redis | Option B: Memcached | Option C: In-Memory |
|-------------------|----------------|---------------------|---------------------|
| Performance (30%) | 9 | 9 | 10 |
| Persistence (25%) | 8 | 3 | 1 |
| Clustering (20%) | 7 | 8 | 2 |
| Complexity (15%) | 6 | 8 | 10 |
| Cost (10%) | 5 | 7 | 10 |
| **Weighted Score** | **7.35** | **6.55** | **4.85** |

**Recommendation**: Redis — best balance of performance and persistence
```

## First Principles Analysis (#39)

**Output pattern**: `assumptions -> truths -> new-approach`

```markdown
### First Principles Analysis

**Assumptions Challenged**:
1. "We need a separate notification service" — Why?
2. "Email must be sent synchronously" — Must it?
3. "Users want real-time notifications" — Do they?

**Fundamental Truths**:
1. Users need to know about important events
2. Different events have different urgency levels
3. Not all channels need the same latency

**Rebuilt Approach**: Tiered notification — critical events push immediately, routine events batch hourly, marketing events daily digest. No separate service needed — existing worker queue handles all tiers.
```

## Critique and Refine (#42)

**Output pattern**: `strengths/weaknesses -> improvements -> refined`

```markdown
### Critique and Refine

**Strengths**:
- Clean separation of concerns between API and service layers
- Comprehensive error handling with specific exception types
- Good test coverage for happy paths

**Weaknesses**:
- Missing edge case tests for concurrent modifications
- Error messages leak internal implementation details
- No circuit breaker for external API dependency

**Improvements**:
1. Add optimistic locking tests for concurrent updates
2. Sanitize error messages at API boundary
3. Add circuit breaker with fallback for payment gateway

**Refined Plan**: Original approach + 3 improvements above. Estimated +2 hours for circuit breaker integration.
```

## Challenge from Critical Perspective (#36)

**Output pattern**: `assumptions -> challenges -> strengthening`

```markdown
### Devil's Advocate Challenge

**Assumption 1**: "This caching strategy will reduce load by 80%"
**Challenge**: Cache hit ratio depends on access patterns. If data is frequently updated, cache invalidation may cause MORE load (thundering herd).
**Strengthening**: Add cache warming + staggered TTL to prevent thundering herd.

**Assumption 2**: "Users won't notice the migration"
**Challenge**: Any schema change risks data inconsistency during the migration window.
**Strengthening**: Use dual-write pattern during migration, validate consistency before cutover.
```

## Debate Club Showdown (#3)

**Output pattern**: `thesis -> antithesis -> synthesis`

```markdown
### Approach Debate

**Thesis: Monorepo**
All services in a single repository for atomic changes and shared tooling.
Strengths: unified CI, shared types, atomic refactors.

**Antithesis: Polyrepo**
Each service in its own repository for independent deployment and ownership.
Strengths: clear boundaries, independent versioning, team autonomy.

**Synthesis**: Monorepo with strict module boundaries enforced by CODEOWNERS and CI checks. Gets atomic change benefits without losing team ownership clarity.
```

## Cross-Functional War Room (#6)

**Output pattern**: `perspectives -> constraints -> trade-offs`

```markdown
**Context**: Adding real-time collaboration features to a document editor.

**Product perspective**:
- Users need to see co-editors' cursors and changes instantly
- Must work across mobile and desktop
- Constraint: cannot increase page load time beyond current 2s target

**Engineering perspective**:
- WebSocket-based approach requires persistent connections — server cost scales linearly with concurrent users
- Operational Transform (OT) vs CRDT trade-off: OT is simpler but requires central server; CRDT is distributed but more complex
- Constraint: existing REST API architecture needs WebSocket layer added

**Design perspective**:
- Cursor presence indicators need to be non-intrusive but visible
- Conflict resolution UI must be intuitive for non-technical users
- Constraint: mobile screen real estate limits visible collaborator count

**Trade-offs**:
1. CRDT + distributed sync: higher engineering complexity, lower server cost, offline support
2. OT + central server: simpler implementation, higher server cost, requires connectivity
3. Hybrid: CRDT for text, OT for structured elements — moderate complexity, best UX

**Decision**: Option 3 (hybrid) — balances engineering investment with user experience across platforms.
```

## Mentor and Apprentice (#7)

**Output pattern**: `questions -> insights -> clarifications`

```markdown
**Context**: Implementing a permission system for a multi-tenant SaaS application.

**Apprentice questions** (naive, assumption-surfacing):
1. "Why can't we just check `user.role === 'admin'` everywhere?"
2. "What happens if a user belongs to two organizations with different permissions?"
3. "Why do we need permissions at all if we trust our users?"
4. "Can't the frontend just hide buttons users shouldn't click?"

**Insights from each question**:
1. Hardcoded role checks create maintenance burden and can't handle custom roles → need abstraction layer (RBAC or ABAC)
2. Multi-tenancy requires scoped permissions (org-level, not global) → permission model must include org context
3. Trust but verify — insider threats, compromised accounts, audit requirements → server-side enforcement is non-negotiable
4. Frontend hiding is UX, not security — API must independently verify → defense in depth principle

**Clarifications**:
- Permission model: RBAC with org-scoped roles (simpler than ABAC for current needs, extensible later)
- Resolution for multi-org: permissions evaluated per-org context, user selects active org
- Enforcement layers: middleware for API routes, frontend for UX, audit log for compliance
- Hidden assumption surfaced: "users" includes API clients and service accounts, not just humans
```
