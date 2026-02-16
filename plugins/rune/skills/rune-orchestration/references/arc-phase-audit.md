# Phase 8: AUDIT — Full Algorithm

Invoke `/rune:audit` logic as a final quality gate. Informational only — does not halt the pipeline.

**Team**: `arc-audit-{id}` (delegated to `/rune:audit` — manages its own TeamCreate/TeamDelete with guards)
**Tools (read-only)**: Read, Glob, Grep, Write (own output file only)
**Timeout**: 20 min (PHASE_TIMEOUTS.audit = 1_200_000 — inner 15m + 5m setup)

**Inputs**:
- All prior phase artifacts (enriched plan, work summary, TOME, resolution report, gap analysis)
- Committed code changes on the feature branch
- Arc identifier (`id`)

**Outputs**: `tmp/arc/{id}/audit-report.md`

**Consumers**: Completion report (final arc output to user)

> **Note**: `sha256()`, `updateCheckpoint()`, `exists()`, and `warn()` are dispatcher-provided utilities available in the arc orchestrator context. Phase reference files call these without import.

## Delegation Steps (Phase 8 → audit.md Phase 0)

<!-- See arc-delegation-checklist.md Phase 8 for the canonical contract -->

When arc invokes `/rune:audit` logic, the delegated command MUST execute these Phase 0 steps
from audit.md:

| # | audit.md Phase 0 Step | Action | Notes |
|---|----------------------|--------|-------|
| 1 | File scanning | **RUN** | Audit needs full project file inventory (`find` with standard exclusions) |
| 2 | Abort conditions check | **RUN** | Graceful no-op if no auditable code |
| 3 | Custom Ash loading | **RUN** | `ashes.custom[]` filtered by `workflows: [audit]` (no-op if none configured) |
| 4 | Codex Oracle detection | **RUN** | Per `codex-detection.md`, if `audit` in `talisman.codex.workflows` |

**Steps SKIPPED** (arc handles or not applicable):
- Generate audit identifier: use arc id for consistent artifact naming
- Branch detection (metadata): arc already has this from pre-flight (COMMIT-1)
- `--focus` / `--max-agents` / `--dry-run` flags: arc uses defaults (full audit)

## Codex Oracle (Conditional)

```javascript
// Run Codex detection per roundtable-circle/references/codex-detection.md
// If detected and `audit` is in `talisman.codex.workflows`, include Codex Oracle
// Findings use `CDX` prefix and participate in dedup and TOME aggregation
```

The Codex Oracle is conditionally included when:
1. The `codex` CLI is available on the system PATH
2. The `talisman.codex.workflows` array includes `"audit"`

## Ash Selection

Delegated to `/rune:audit` — typically summons rune-architect + ward-sentinel + pattern-weaver (see audit.md for full selection logic based on file types and talisman.yml configuration).

## Invocation

```javascript
// Delegation pattern: /rune:audit creates its own team (e.g., rune-audit-{identifier}).
// Arc reads the team name from the audit state file or teammate idle notification.
// SEC-12 FIX: Use Glob() to resolve wildcard — Read() does not support glob expansion.
// CDX-2 NOTE: Glob matches ALL audit state files — [0] is most recent by mtime.
const auditStateFiles = Glob("tmp/.rune-audit-*.json")
if (auditStateFiles.length > 1) warn(`Multiple audit state files found (${auditStateFiles.length}) — using most recent`)
const auditTeamName = auditStateFiles.length > 0
  ? JSON.parse(Read(auditStateFiles[0])).team_name
  : `rune-audit-${Date.now()}`
// SEC-2 FIX: Validate team_name from state file before storing in checkpoint (TOCTOU defense)
if (!/^[a-zA-Z0-9_-]+$/.test(auditTeamName)) throw new Error(`Invalid team_name from state file: ${auditTeamName}`)
updateCheckpoint({ phase: "audit", status: "in_progress", phase_sequence: 9, team_name: auditTeamName })
```

## Completion

```javascript
updateCheckpoint({
  phase: "audit", status: "completed",
  artifact: `tmp/arc/${id}/audit-report.md`, artifact_hash: sha256(auditReport), phase_sequence: 9
})
```

## Error Handling

| Condition | Action |
|-----------|--------|
| Audit timeout (inner polling exceeded) | Phase marked completed with partial report. Does NOT halt pipeline |
| Team creation fails | Cleanup fallback via `rm -rf` (see team-lifecycle-guard.md) |
| No findings | Audit completes with clean report |

## Team Lifecycle

Delegated to `/rune:audit` — manages its own TeamCreate/TeamDelete with guards (see [team-lifecycle-guard.md](team-lifecycle-guard.md)). Arc records the actual `team_name` in checkpoint for cancel-arc discovery.

**Output**: `tmp/arc/{id}/audit-report.md`

**Failure policy**: Report results. Does not halt — informational final gate.
