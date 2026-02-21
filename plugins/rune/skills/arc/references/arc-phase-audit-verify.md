# Phase 8.7: AUDIT_VERIFY — Full Algorithm

Convergence controller for the audit-mend loop. Evaluates whether audit findings are resolved.

**Team**: None (orchestrator-only)
**Tools**: Read, Write
**Timeout**: `PHASE_TIMEOUTS.audit_verify` (4 min default)

**Inputs**: `tmp/arc/${id}/audit-resolution-report.md`
**Outputs**: Convergence verdict (checkpoint update)
**Consumers**: Phase 9 (ship) or Phase 8 (audit, on retry)

> **Note**: Uses `checkpoint.audit_convergence` (separate from `checkpoint.convergence` which tracks review-mend).

> **Note**: `sha256()`, `updateCheckpoint()`, `exists()`, and `warn()` are dispatcher-provided utilities available in the arc orchestrator context. Phase reference files call these without import.

## Algorithm

```javascript
// Phase 8.7: Audit-Verify (Convergence Check)
// Entry guard
if (checkpoint.phases.audit_mend.status === "skipped") {
  updateCheckpoint({ phase: "audit_verify", status: "skipped", phase_sequence: 15.7, team_name: null })
  return
}

const auditRound = checkpoint.audit_convergence?.round ?? 0
const auditMaxCycles = talisman?.audit?.audit_mend?.max_cycles ?? 2
const p1HardGate = talisman?.audit?.audit_mend?.p1_hard_gate !== false  // default: true

// Read resolution report
const resReport = Read(`tmp/arc/${id}/audit-resolution-report.md`)
const remainingP1 = countResolution(resReport, 'FAILED', 'P1')
const remainingP2 = countResolution(resReport, 'FAILED', 'P2')
const totalFixed = countResolution(resReport, 'FIXED')
const totalFailed = countResolution(resReport, 'FAILED')

// EC-1: Zero progress guard
if (totalFixed === 0 && totalFailed > 0) {
  warn(`Audit-mend fixed 0 findings — manual intervention may be required.`)
}

// Determine verdict
let verdict
if (remainingP1 === 0 && remainingP2 === 0) {
  verdict = 'converged'
} else if (remainingP1 === 0 && remainingP2 > 0 && auditRound + 1 >= auditMaxCycles) {
  verdict = 'halted'  // P2 remaining but out of cycles — ship as tech debt
} else if (remainingP1 > 0 && auditRound + 1 >= auditMaxCycles) {
  if (p1HardGate) {
    verdict = 'failed'  // P1 remaining and hard gate — halt pipeline
  } else {
    verdict = 'halted'  // P1 remaining but soft gate — ship with warning
  }
} else {
  verdict = 'retry'
}

// Record history
const historyEntry = {
  round: auditRound,
  p1_remaining: remainingP1,
  p2_remaining: remainingP2,
  fixed: totalFixed,
  failed: totalFailed,
  verdict,
  timestamp: new Date().toISOString()
}

const history = [...(checkpoint.audit_convergence?.history ?? []), historyEntry]

if (verdict === 'converged') {
  updateCheckpoint({
    phase: "audit_verify", status: "completed", phase_sequence: 15.7,
    audit_convergence: { ...checkpoint.audit_convergence, history }
  })
} else if (verdict === 'retry') {
  // Reset audit_mend and audit_verify to pending for next cycle
  checkpoint.phases.audit_mend.status = 'pending'
  checkpoint.phases.audit_mend.artifact = null
  checkpoint.phases.audit_mend.artifact_hash = null
  checkpoint.phases.audit_mend.team_name = null

  checkpoint.phases.audit_verify.status = 'pending'
  checkpoint.phases.audit_verify.artifact = null
  checkpoint.phases.audit_verify.artifact_hash = null
  checkpoint.phases.audit_verify.team_name = null

  checkpoint.audit_convergence = {
    ...checkpoint.audit_convergence,
    round: auditRound + 1,
    history
  }

  updateCheckpoint(checkpoint)
  // Dispatcher loops back to audit_mend (first pending in PHASE_ORDER)
} else if (verdict === 'halted') {
  // Ship remaining as tech debt
  const unfixed = extractUnfixed(resReport, ['P1', 'P2'])
  const knownIssuesCap = talisman?.audit?.audit_mend?.known_issues_cap ?? 10
  Write(`tmp/arc/${id}/audit-known-issues.md`, formatKnownIssues(unfixed, knownIssuesCap))

  updateCheckpoint({
    phase: "audit_verify", status: "completed", phase_sequence: 15.7,
    audit_convergence: { ...checkpoint.audit_convergence, history }
  })
} else if (verdict === 'failed') {
  updateCheckpoint({
    phase: "audit_verify", status: "failed", phase_sequence: 15.7,
    audit_convergence: { ...checkpoint.audit_convergence, history }
  })
  warn(`Audit-mend halted with ${remainingP1} unresolved P1 findings. Manual fix required.`)
  // Pipeline halts — user must fix and --resume
}
```

## Error Handling

| Condition | Action |
|-----------|--------|
| audit_mend was skipped | Skip audit_verify |
| Resolution report missing | Halt — audit_mend did not complete |
| P1 > 0 after maxCycles (hard gate) | Pipeline FAILS — manual fix required |
| P1 > 0 after maxCycles (soft gate) | Ship with Known Issues warning |
| Zero progress (0 fixed, N failed) | Warn but continue verdict evaluation |

## Crash Recovery

Orchestrator-only phase with no team — minimal crash surface.

| Resource | Location |
|----------|----------|
| Checkpoint state | `.claude/arc/{id}/checkpoint.json` (phase: "audit_verify") |

Recovery: On `--resume`, if audit_verify phase is `in_progress`, re-run from the beginning. No team cleanup needed.

**Output**: Convergence verdict in checkpoint
**Failure policy**: P1 hard gate blocks ship. P2 overflow → Known Issues.
