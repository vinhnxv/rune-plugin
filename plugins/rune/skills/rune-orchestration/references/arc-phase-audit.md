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

## Codex Oracle (Conditional)

```javascript
// Run Codex detection per roundtable-circle/references/codex-detection.md
// If detected and `audit` is in `talisman.codex.workflows`, include Codex Oracle
// Findings use `CDX` prefix and participate in dedup and TOME aggregation
```

The Codex Oracle is conditionally included when:
1. The `codex` CLI is available on the system PATH
2. The `talisman.codex.workflows` array includes `"audit"`

## Invocation

```javascript
// Delegation pattern: /rune:audit creates its own team (e.g., rune-audit-{identifier}).
// Arc reads the team name from the audit state file or teammate idle notification.
const auditTeamName = Read(`tmp/.rune-audit-*.json`)?.team_name || `rune-audit-${Date.now()}`
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
