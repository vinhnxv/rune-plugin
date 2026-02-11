---
name: rune-echoes
description: |
  Smart Memory Lifecycle for Rune agents. Project-level memory stored in `.claude/echoes/`
  with 3-layer lifecycle (Etched/Inscribed/Traced), multi-factor pruning, and concurrent
  write safety. Agents learn across sessions without manual compound workflows.

  <example>
  Context: After a review, Runebearers persist patterns to echoes
  user: "Review found repeated N+1 query pattern"
  assistant: "Pattern persisted to echoes/reviewer/MEMORY.md as Inscribed entry"
  </example>
user-invocable: false
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Grep
---

# Rune Echoes — Smart Memory Lifecycle

Project-level agent memory that compounds knowledge across sessions. Each workflow writes learnings to `.claude/echoes/`, and future workflows read them to avoid repeating mistakes.

> "The Tarnished collects runes to grow stronger. Each engineering session should do the same."

## Architecture

### Memory Directory Structure

```
.claude/echoes/
├── planner/
│   ├── MEMORY.md              # Active memory (150 line limit)
│   ├── knowledge.md           # Compressed learnings (on-demand load)
│   └── archive/               # Pruned memories (never auto-loaded)
├── workers/
│   └── MEMORY.md
├── reviewer/
│   ├── MEMORY.md
│   ├── knowledge.md
│   └── archive/
├── auditor/
│   └── MEMORY.md
└── team/
    └── MEMORY.md              # Cross-role learnings (lead writes post-workflow)
```

### 3-Layer Lifecycle

| Layer | Rune Name | Max Age | Trigger | Pruning |
|-------|-----------|---------|---------|---------|
| Structural | **Etched** | Never expires | Manual only | User confirmation required |
| Tactical | **Inscribed** | 90 days unreferenced | MEMORY.md > 150 lines | Multi-factor scoring, archive bottom 20% |
| Session | **Traced** | 30 days | MEMORY.md > 150 lines | Utility-based, compress middle 30% |

**Etched** entries are permanent project knowledge (architecture decisions, tech stack, key conventions). Only the user can add or remove them.

**Inscribed** entries are tactical patterns discovered during reviews, audits, and work (e.g., "this codebase has N+1 query tendency in service layers"). They persist across sessions and get pruned when stale.

**Traced** entries are session-specific observations (e.g., "PR #42 had 3 unused imports"). They compress or archive quickly.

## Memory Entry Format

Every echo entry must include evidence-based metadata:

```markdown
### [YYYY-MM-DD] Pattern: {short description}
- **layer**: etched | inscribed | traced
- **source**: rune:{workflow} {context}
- **confidence**: 0.0-1.0
- **evidence**: `{file}:{lines}` — {what was found}
- **verified**: YYYY-MM-DD
- **supersedes**: {previous entry title} | none
- {The actual learning in 1-3 sentences}
```

### Example Entries

**Etched (permanent):**
```markdown
### [2026-02-11] Architecture: Express + Prisma async
- **layer**: etched
- **source**: manual
- **confidence**: 1.0
- **evidence**: `package.json:5-15` — framework dependencies
- **verified**: 2026-02-11
- **supersedes**: none
- Backend uses Express with Prisma ORM. All repository methods are async.
  Domain layer has no framework imports. DI container manages dependencies.
```

**Inscribed (tactical):**
```markdown
### [2026-02-11] Pattern: Unused imports in new files
- **layer**: inscribed
- **source**: rune:review PR #42
- **confidence**: 0.85
- **evidence**: `src/auth.py:1-5` — 3 unused imports found
- **verified**: 2026-02-11
- **supersedes**: none
- Codebase tends to leave unused imports in newly created files.
  Reviewers should flag import hygiene in new files specifically.
```

**Traced (session):**
```markdown
### [2026-02-11] Observation: Slow test suite in CI
- **layer**: traced
- **source**: rune:work session-abc
- **confidence**: 0.6
- **evidence**: CI logs — test suite took 8min (vs 3min baseline)
- **verified**: 2026-02-11
- **supersedes**: none
- Test suite is unusually slow today, possibly due to new integration tests.
```

## Multi-Factor Pruning Algorithm

When MEMORY.md exceeds 150 lines, calculate Echo Score for each entry:

```
Echo Score = (Importance × 0.4) + (Relevance × 0.3) + (Recency × 0.3)

Where:
  Importance = layer weight (etched=1.0, inscribed=0.7, traced=0.3)
  Relevance  = times referenced in recent workflows / total workflows (0.0-1.0)
  Recency    = 1.0 - (days_since_verified / max_age_for_layer)
```

### Pruning Rules

- **Etched**: Score locked at 1.0 — never pruned automatically
- **Inscribed**: Archive if score < 0.3 AND age > 90 days unreferenced
- **Traced**: Archive if score < 0.2 AND age > 30 days
- Prune ONLY between workflows, never during active phases
- Always backup before pruning: copy MEMORY.md to `archive/MEMORY-{date}.md`

### Active Context Compression

When a role's `knowledge.md` exceeds 300 lines:
1. Group related entries by topic
2. Compress each group into a "knowledge block" (3-5 line summary)
3. Preserve evidence references but remove verbose descriptions
4. Expected savings: ~22% token reduction

## Concurrent Write Protocol

Multiple Runebearers may discover learnings simultaneously. To prevent write conflicts:

1. **During workflow**: Each Runebearer writes to `echoes/{role}/{agent-name}-findings.md` (unique file per agent)
2. **Post-workflow**: Lead agent consolidates all `{agent-name}-findings.md` into `echoes/{role}/MEMORY.md`
3. **Cross-role learnings**: Only lead writes to `echoes/team/MEMORY.md`
4. **Consolidation protocol**: Read existing MEMORY.md → append new entries → check 150-line limit → prune if needed → write

### Write Protocol Steps

```
1. Read echoes/{role}/MEMORY.md (or create if missing)
2. Read all echoes/{role}/*-findings.md files
3. For each finding:
   a. Check if it duplicates an existing entry (same evidence + pattern)
   b. If duplicate: update verified date and confidence (higher wins)
   c. If new: append with entry format
4. If MEMORY.md > 150 lines: run pruning algorithm
5. Write updated MEMORY.md
6. Delete processed *-findings.md files
```

## Security

### Sensitive Data Filter

Before persisting any echo entry, reject if content matches:

```
Patterns to reject:
- API keys: /[A-Za-z0-9_-]{20,}/ in context suggesting key/token
- Passwords: /password\s*[:=]\s*\S+/i
- Tokens: /bearer\s+[A-Za-z0-9._-]+/i
- Connection strings: /[a-z]+:\/\/[^:]+:[^@]+@/
- Email addresses in evidence (unless the learning IS about email handling)
```

If a finding triggers the filter, persist the learning but strip the sensitive evidence.

### Default Exclusion

`.gitignore` excludes `.claude/echoes/` by default. Users opt-in to version control:

```yaml
# .claude/rune-config.yml
echoes:
  version_controlled: true  # Remove .claude/echoes/ from .gitignore
```

## Integration Points

### After Review (`/rune:review`)

In Phase 7 (Cleanup), before presenting TOME.md:

```
1. Read TOME.md for high-confidence patterns (P1/P2 findings)
2. Convert recurring patterns to Inscribed entries
3. Write to echoes/reviewer/MEMORY.md via consolidation protocol
```

### After Audit (`/rune:audit`)

Same as review, writing to `echoes/auditor/MEMORY.md`.

### During Plan (`/rune:plan`, v1.0)

```
1. echo-reader agent reads echoes/planner/MEMORY.md + echoes/team/MEMORY.md
2. Surfaces relevant past learnings for current feature
3. After plan: persist architectural discoveries to echoes/planner/
```

### During Work (`/rune:work`, v1.0)

```
1. Read echoes/workers/MEMORY.md for implementation patterns
2. After work: persist TDD patterns, gotchas to echoes/workers/
```

## Echo Schema Versioning

MEMORY.md files include a version header:

```markdown
<!-- echo-schema: v1 -->
# {Role} Memory

{entries...}
```

This enables future schema migrations without breaking existing echoes.

## Commands

See `/rune:echoes` command for user-facing echo management (show, prune, reset).
