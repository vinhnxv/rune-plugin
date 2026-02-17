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
// PRE-DELEGATION: Record phase as in_progress with null team name.
// Actual team name will be discovered post-delegation from state file.
updateCheckpoint({ phase: "audit", status: "in_progress", phase_sequence: 9, team_name: null })
```

## Post-Delegation Team Name Discovery

```javascript
// POST-DELEGATION: Read actual team name from state file
const postAuditStateFiles = Glob("tmp/.rune-audit-*.json").filter(f => {
  try {
    const state = JSON.parse(Read(f))
    if (!state.status) return false
    const age = Date.now() - new Date(state.started).getTime()
    const isValidAge = !Number.isNaN(age) && age >= 0 && age < PHASE_TIMEOUTS.audit
    const isRelevant = state.status === "active" ||
      (state.status === "completed" && age >= 0 && age < 5000)
    return isRelevant && isValidAge
  } catch (e) { return false }
})
if (postAuditStateFiles.length > 1) {
  warn(`Multiple audit state files found (${postAuditStateFiles.length}) — using most recent`)
}
if (postAuditStateFiles.length > 0) {
  try {
    const actualTeamName = JSON.parse(Read(postAuditStateFiles[0])).team_name
    if (actualTeamName && /^[a-zA-Z0-9_-]+$/.test(actualTeamName)) {
      updateCheckpoint({ phase: "audit", team_name: actualTeamName })
    }
  } catch (e) {
    warn(`Failed to read team_name from state file: ${e.message}`)
  }
}
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

Arc runs `prePhaseCleanup(checkpoint)` before delegation (ARC-6). See SKILL.md Inter-Phase Cleanup Guard section.

**Output**: `tmp/arc/{id}/audit-report.md`

**Failure policy**: Report results. Does not halt — informational final gate.

## Crash Recovery

If this phase crashes before reaching cleanup, the following resources are orphaned:

| Resource | Location |
|----------|----------|
| Team config | `~/.claude/teams/rune-audit-{identifier}/` |
| Task list | `~/.claude/tasks/rune-audit-{identifier}/` |
| State file | `tmp/.rune-audit-*.json` (stuck in `"active"` status) |
| Signal dir | `tmp/.rune-signals/rune-audit-{identifier}/` |

### Recovery Layers

If this phase crashes, the orphaned resources above are recovered by the 3-layer defense:
Layer 1 (ORCH-1 resume), Layer 2 (`/rune:rest --heal`), Layer 3 (arc pre-flight stale scan).
Audit phase teams use `rune-audit-*` prefix — handled by the sub-command's own pre-create guard (not Layer 3).

See [team-lifecycle-guard.md](team-lifecycle-guard.md) §Orphan Recovery Pattern for full layer descriptions and coverage matrix.
