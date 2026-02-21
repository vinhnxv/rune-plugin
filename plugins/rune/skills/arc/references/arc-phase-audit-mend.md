# Phase 8.5: AUDIT_MEND — Full Algorithm

Fixes P1+P2 findings from the unified deep audit TOME.

**Team**: Delegated to `/rune:mend` (creates `rune-mend-deep-{id}`)
**Tools**: Delegated
**Timeout**: `PHASE_TIMEOUTS.audit_mend` (23 min default)

**Inputs**: `tmp/arc/{id}/TOME.md` (unified audit TOME)
**Outputs**: `tmp/arc/{id}/audit-resolution-report.md`
**Consumers**: Phase 8.7 (audit_verify)

> **Note**: `sha256()`, `updateCheckpoint()`, `exists()`, and `warn()` are dispatcher-provided utilities available in the arc orchestrator context. Phase reference files call these without import.

## Algorithm

```javascript
// Phase 8.5: Audit-Mend
// Entry guard: skip if audit was skipped or informational-only
if (checkpoint.phases.audit.status === "skipped") {
  updateCheckpoint({ phase: "audit_mend", status: "skipped", phase_sequence: 15.5, team_name: null })
  return
}

// Read unified TOME
const auditTome = Read(`tmp/arc/${id}/TOME.md`)
const p1p2Count = countFindings(auditTome, ['P1', 'P2'])

if (p1p2Count === 0) {
  updateCheckpoint({ phase: "audit_mend", status: "skipped", phase_sequence: 15.5, team_name: null })
  return  // Nothing to mend
}

// Filter TOME to mendable severities only
const mendScope = talisman?.audit?.audit_mend?.scope ?? 'p1p2'
const severities = mendScope === 'p1' ? ['P1'] : mendScope === 'all' ? ['P1', 'P2', 'P3'] : ['P1', 'P2']
const mendableTome = filterTome(auditTome, { severities })
Write(`tmp/arc/${id}/audit-tome-mendable.md`, mendableTome)

// Extract P3 findings for Known Issues (separate from mend)
const p3Findings = filterTome(auditTome, { severities: ['P3'] })
if (p3Findings) {
  Write(`tmp/arc/${id}/audit-known-issues-p3.md`, p3Findings)
}

// ARC-6: Clean stale teams before delegating
prePhaseCleanup(checkpoint)

updateCheckpoint({ phase: "audit_mend", status: "in_progress", phase_sequence: 15.5, team_name: null })

// Delegate to /rune:mend with audit-specific TOME
// The mend skill creates its own team (rune-mend-deep-{session_id})
// SEC-MEND-001 hook applies — same path enforcement
// State file: tmp/.rune-mend-deep-{session_id}.json

// Post-delegation: discover team name from state file
const postStateFiles = Glob("tmp/.rune-mend-deep-*.json").filter(f => {
  const state = JSON.parse(Read(f))
  const age = Date.now() - new Date(state.started).getTime()
  return !Number.isNaN(age) && age >= 0 && age < auditMendTimeout
})

const teamName = postStateFiles.length > 0 ? JSON.parse(Read(postStateFiles[0])).team_name : null

// Read resolution report
const resReport = Read(`tmp/arc/${id}/audit-resolution-report.md`)
const hash = sha256(resReport)

updateCheckpoint({
  phase: "audit_mend", status: "completed",
  artifact: `tmp/arc/${id}/audit-resolution-report.md`,
  artifact_hash: hash,
  phase_sequence: 15.5,
  team_name: teamName
})
```

## Error Handling

| Condition | Action |
|-----------|--------|
| Audit was skipped/informational | Skip audit_mend |
| 0 P1+P2 findings | Skip audit_mend |
| Mend delegation fails | Halt — warn and stop pipeline |
| >3 findings FAILED in resolution | Halt — manual intervention |
| Resolution report missing | Halt — mend did not complete |

## Crash Recovery

If this phase crashes before reaching cleanup, the following resources are orphaned:

| Resource | Location |
|----------|----------|
| Team config | `~/.claude/teams/rune-mend-deep-{session_id}/` |
| Task list | `~/.claude/tasks/rune-mend-deep-{session_id}/` |
| State file | `tmp/.rune-mend-deep-*.json` |
| Mendable TOME | `tmp/arc/{id}/audit-tome-mendable.md` |

### Recovery Layers

If this phase crashes, the orphaned resources above are recovered by the 3-layer defense:
Layer 1 (ORCH-1 resume), Layer 2 (`/rune:rest --heal`), Layer 3 (arc pre-flight stale scan).
Audit-mend teams use `rune-mend-deep-*` prefix — handled by the sub-command's own pre-create guard (not Layer 3).

See [team-lifecycle-guard.md](team-lifecycle-guard.md) §Orphan Recovery Pattern for full layer descriptions and coverage matrix.

**Output**: `tmp/arc/{id}/audit-resolution-report.md`
**Failure policy**: Halt if >3 FAILED findings. Pipeline requires manual fix.
