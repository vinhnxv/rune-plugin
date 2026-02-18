# Phase 7.5: Verify Mend (Review-Mend Convergence Controller) — Full Algorithm

Full convergence controller that evaluates mend results, determines whether to loop back for another review-mend cycle, or proceed to audit. Replaces the previous single-pass spot-check with an adaptive multi-cycle review-mend loop.

**Team**: None for convergence decision. Delegates full re-review to `/rune:review` (Phase 6) via dispatcher loop-back.
**Tools**: Read, Glob, Grep, Write, Bash (git diff)
**Duration**: Max 4 minutes per convergence evaluation (re-review cycles run as separate Phase 6+7 invocations)

See [review-mend-convergence.md](../../roundtable-circle/references/review-mend-convergence.md) for shared tier selection and convergence evaluation logic.

## Entry Guard

Skip if mend was skipped, had 0 findings, or produced no fixes.

```javascript
// Decree-arbiter P2: Round-aware resolution report read path
const mendRound = checkpoint.convergence?.round ?? 0
const resolutionReportPath = mendRound === 0
  ? `tmp/arc/${id}/resolution-report.md`
  : `tmp/arc/${id}/resolution-report-round-${mendRound}.md`
const resolutionReport = Read(resolutionReportPath)
const mendSummary = parseMendSummary(resolutionReport)
// parseMendSummary extracts: { total, fixed, false_positive, failed, skipped }

// BACK-004 FIX: Removed mendSummary.fixed === 0 from entry guard — that case is handled by EC-1 below.
if (checkpoint.phases.mend.status === "skipped" || mendSummary.total === 0) {
  updateCheckpoint({ phase: "verify_mend", status: "skipped", phase_sequence: 8, team_name: null })
  return
}

// EC-1: Mend made no progress — prevent infinite retry on unfixable findings
if (mendSummary.fixed === 0 && mendSummary.failed > 0) {
  warn(`Mend fixed 0 findings (${mendSummary.failed} failed) — manual intervention required.`)
  checkpoint.convergence.history.push({
    round: mendRound, findings_before: mendSummary.total, findings_after: mendSummary.failed,
    p1_remaining: 0, verdict: 'halted', reason: 'zero_progress', timestamp: new Date().toISOString()
  })
  updateCheckpoint({ phase: 'verify_mend', status: 'completed', phase_sequence: 8, team_name: null,
    artifact: resolutionReportPath, artifact_hash: sha256(resolutionReport) })
  return
}

updateCheckpoint({ phase: "verify_mend", status: "in_progress", phase_sequence: 8, team_name: null })
```

## STEP 1: Read Current TOME and Count Findings

```javascript
// EC-2: Guard against missing or malformed TOME
const tomeFile = mendRound === 0 ? `tmp/arc/${id}/tome.md` : `tmp/arc/${id}/tome-round-${mendRound}.md`
let currentTome
try {
  currentTome = Read(tomeFile)
} catch (e) {
  warn(`TOME not found at ${tomeFile} — review may have timed out.`)
  checkpoint.convergence.history.push({
    round: mendRound, findings_before: 0, findings_after: 0,
    verdict: 'halted', reason: 'tome_missing', timestamp: new Date().toISOString()
  })
  updateCheckpoint({ phase: 'verify_mend', status: 'completed', phase_sequence: 8, team_name: null })
  return
}
if (!currentTome || (!currentTome.includes('RUNE:FINDING') && !currentTome.includes('<!-- CLEAN -->'))) {
  warn(`TOME at ${tomeFile} appears empty or malformed — halting convergence.`)
  checkpoint.convergence.history.push({
    round: mendRound, findings_before: 0, findings_after: 0,
    verdict: 'halted', reason: 'tome_malformed', timestamp: new Date().toISOString()
  })
  updateCheckpoint({ phase: 'verify_mend', status: 'completed', phase_sequence: 8, team_name: null })
  return
}

const currentFindingCount = countTomeFindings(currentTome)
const p1Count = countP1Findings(currentTome)

// v1.38.0: Extract scope stats for smart convergence scoring
// Scope stats are available when diff-scope tagging was applied (review.md Phase 5.3).
// For untagged TOMEs (pre-v1.38.0), scopeStats is null → evaluateConvergence skips smart scoring.
let scopeStats = null
// SEC-007 FIX: Filter markers by session nonce before extracting scope stats.
// Without nonce validation, stale/injected markers from prior sessions could inflate counts.
const sessionNonce = checkpoint.session_nonce
const allMarkers = currentTome.match(/<!-- RUNE:FINDING[^>]*-->/g) || []
const findingMarkers = sessionNonce
  ? allMarkers.filter(m => m.includes(`nonce="${sessionNonce}"`))
  : allMarkers  // Fallback: no nonce in checkpoint (pre-v1.11.0) → use all markers
if (findingMarkers.some(m => /scope="(in-diff|pre-existing)"/.test(m))) {
  // SEC-006 FIX: Case-insensitive severity matching to prevent p1 bypass via lowercase
  const p3Markers = findingMarkers.filter(m => /severity="P3"/i.test(m))
  const preExistingMarkers = findingMarkers.filter(m => /scope="pre-existing"/.test(m))
  const inDiffMarkers = findingMarkers.filter(m => /scope="in-diff"/.test(m))
  scopeStats = {
    p1Count,
    p3Count: p3Markers.length,
    preExistingCount: preExistingMarkers.length,
    inDiffCount: inDiffMarkers.length,
    totalFindings: currentFindingCount,
  }
}
```

## STEP 2: Evaluate Convergence

Uses shared `evaluateConvergence()` from review-mend-convergence.md. Passes `scopeStats` (v1.38.0+) for smart convergence scoring when diff-scope data is available.

```javascript
const talisman = readTalisman()
const verdict = evaluateConvergence(currentFindingCount, p1Count, checkpoint, talisman, scopeStats)

// v1.38.0: Compute convergence score for history record (observability — R6 mitigation)
let convergenceScore = null
if (scopeStats && talisman?.review?.diff_scope?.enabled !== false) {
  convergenceScore = computeConvergenceScore(scopeStats, checkpoint, talisman)
}

// Record convergence history
// BACK-007 NOTE: prevFindings is also computed inside evaluateConvergence() (review-mend-convergence.md).
// Intentional duplication — this copy is for the history record; evaluateConvergence uses its own for verdict.
const prevFindings = mendRound === 0 ? Infinity
  : checkpoint.convergence.history[mendRound - 1]?.findings_after ?? Infinity
checkpoint.convergence.history.push({
  round: mendRound,
  findings_before: prevFindings === Infinity ? currentFindingCount : prevFindings,
  findings_after: currentFindingCount,
  p1_remaining: p1Count,
  mend_fixed: mendSummary.fixed,
  mend_failed: mendSummary.failed,
  // v1.38.0: Scope-aware fields for smart convergence observability
  scope_stats: scopeStats ?? null,              // { p1Count, p3Count, preExistingCount, inDiffCount, totalFindings }
  convergence_score: convergenceScore ?? null,   // { total, components, reason } from computeConvergenceScore()
  verdict,
  timestamp: new Date().toISOString()
})
```

## STEP 3: Act on Verdict

```javascript
if (verdict === 'converged') {
  updateCheckpoint({
    phase: 'verify_mend', status: 'completed',
    artifact: resolutionReportPath, artifact_hash: sha256(resolutionReport),
    phase_sequence: 8, team_name: null
  })
  // → Dispatcher proceeds to Phase 8 (AUDIT)

} else if (verdict === 'retry') {
  // Build progressive focus scope for re-review
  const focusResult = buildProgressiveFocus(resolutionReport, checkpoint.convergence.original_changed_files || [])

  // EC-9: Empty focus scope → halt convergence
  if (!focusResult) {
    warn(`No files modified by mend — cannot scope re-review. Convergence halted.`)
    checkpoint.convergence.history[checkpoint.convergence.history.length - 1].verdict = 'halted'
    checkpoint.convergence.history[checkpoint.convergence.history.length - 1].reason = 'empty_focus_scope'
    updateCheckpoint({ phase: 'verify_mend', status: 'completed',
      artifact: resolutionReportPath, artifact_hash: sha256(resolutionReport),
      phase_sequence: 8, team_name: null })
    return
  }

  // Store focus scope for Phase 6 re-review
  // BACK-008 FIX: Write focus file BEFORE incrementing round — crash between won't leave inconsistent state.
  const nextRound = checkpoint.convergence.round + 1
  Write(`tmp/arc/${id}/review-focus-round-${nextRound}.json`, JSON.stringify(focusResult))
  checkpoint.convergence.round = nextRound

  // CRITICAL: Reset code_review, mend, and verify_mend phases to "pending"
  // The dispatcher scans PHASE_ORDER for the first "pending" phase.
  // Resetting code_review (index 6) ensures the dispatcher loops back to Phase 6
  // before reaching verify_mend (index 8).
  // ASSERTION (decree-arbiter P2): Verify code_review precedes verify_mend in PHASE_ORDER
  const crIdx = PHASE_ORDER.indexOf('code_review')
  const vmIdx = PHASE_ORDER.indexOf('verify_mend')
  if (crIdx < 0 || vmIdx < 0 || crIdx >= vmIdx) {
    throw new Error(`PHASE_ORDER invariant violated: code_review (${crIdx}) must precede verify_mend (${vmIdx})`)
  }

  checkpoint.phases.code_review.status = 'pending'
  checkpoint.phases.code_review.artifact = null
  checkpoint.phases.code_review.artifact_hash = null
  checkpoint.phases.code_review.team_name = null      // BUG FIX: Clear stale team from prior round
  checkpoint.phases.mend.status = 'pending'
  checkpoint.phases.mend.artifact = null
  checkpoint.phases.mend.artifact_hash = null
  checkpoint.phases.mend.team_name = null              // BUG FIX: Clear stale team from prior round
  checkpoint.phases.verify_mend.status = 'pending'
  checkpoint.phases.verify_mend.artifact = null      // Must null — stale artifact causes phantom hash match on resume
  checkpoint.phases.verify_mend.artifact_hash = null
  checkpoint.phases.verify_mend.team_name = null      // BUG FIX: Clear stale team from prior round

  updateCheckpoint(checkpoint)
  // → Dispatcher loops back to Phase 6 (code_review is next "pending" in PHASE_ORDER)

} else if (verdict === 'halted') {
  const round = checkpoint.convergence.round
  warn(`Convergence halted after ${round + 1} cycle(s): ${currentFindingCount} findings remain (${p1Count} P1). Proceeding to audit.`)

  updateCheckpoint({
    phase: 'verify_mend', status: 'completed',
    artifact: resolutionReportPath, artifact_hash: sha256(resolutionReport),
    phase_sequence: 8, team_name: null
  })
  // → Dispatcher proceeds to Phase 8 (AUDIT) with warning
}
```

## Mini-TOME Generation (reference — not called by convergence controller)

<!-- QUAL-014: This function is a reference implementation preserved for future use.
     The current convergence controller (STEP 3 retry branch) triggers a full /rune:review
     re-review instead of generating a mini-TOME. If the convergence design changes to use
     spot-check-based retry (without full re-review), this function would be needed. -->
When `verify_mend` decides to retry but uses spot-check findings instead of a full re-review, it generates a mini-TOME. However, in the new convergence controller, retry triggers a full `/rune:review` re-review — the mini-TOME is only needed as a fallback when the convergence controller itself detects regressions before dispatching.

```javascript
function generateMiniTome(spotFindings, sessionNonce, round) {
  // SEC-008 FIX: Validate round is a non-negative integer before interpolation into finding IDs
  if (!Number.isInteger(round) || round < 0 || round > 10) {
    throw new Error(`Invalid round number: ${round} (must be integer 0-10)`)
  }
  const header = `# TOME -- Convergence Round ${round}\n\n` +
    `Generated by verify_mend convergence controller.\n` +
    `Session nonce: ${sessionNonce}\n` +
    `Findings: ${spotFindings.length}\n\n`

  const findings = spotFindings.map((f, i) => {
    const findingId = `SPOT-R${round}-${String(i + 1).padStart(3, '0')}`
    const safeDesc = f.description
      .replace(/<!--[\s\S]*?-->/g, '')
      .replace(/[\r\n]+/g, ' ')
      .slice(0, 500)
    return `<!-- RUNE:FINDING nonce="${sessionNonce}" id="${findingId}" file="${f.file}" line="${f.line}" severity="${f.severity}" -->\n` +
      `### ${findingId}: ${safeDesc}\n` +
      `**Ash:** verify_mend convergence (round ${round})\n` +
      `**Evidence:** Regression detected in mend fix\n` +
      `**Fix guidance:** Review and correct the mend fix\n` +
      `<!-- /RUNE:FINDING -->\n`
  }).join('\n')

  return header + findings
}
```

**Output**: Convergence verdict stored in checkpoint. On retry, phases reset to "pending" and dispatcher loops back.

**Failure policy**: Non-blocking. Halting proceeds to audit with warning. The convergence gate never blocks the pipeline permanently; it either retries or gives up gracefully.

## Dispatcher Contract

**CRITICAL**: The dispatcher MUST use "first pending in PHASE_ORDER" scan to select the next phase. The convergence controller resets `code_review` to "pending" to trigger a loop-back. If the dispatcher were optimized to use "last completed + 1", the loop-back would silently fail and the pipeline would skip to Phase 8 (audit).

The defensive assertion in STEP 3 (retry branch) verifies the PHASE_ORDER invariant at runtime: `code_review` index must be less than `verify_mend` index.
