# Stagnation Sentinel (ARC-8.5)

Cross-phase diagnostic monitor for the arc pipeline. Detects error repetition, file-change stagnation, regression patterns, and budget overrun risk. Non-blocking — emits warnings only, never halts autonomously.

**Inputs**: `checkpoint.json` (schema v15), phase completion events, convergence history
**Outputs**: Updated `checkpoint.stagnation` field; warning strings for arc orchestrator
**Preconditions**: Arc pipeline active with valid checkpoint (schema v15)
**Error handling**: All stagnation checks are non-blocking (WARN only). Missing stagnation data → return null. Malformed TOME → skip pattern extraction, log warning. git diff failure → skip velocity update, log warning.

**Consumers**: arc SKILL.md (after each `updateCheckpoint()` call), [verify-mend.md](verify-mend.md)

> **Note**: `sha256()`, `PHASE_ORDER`, `calculateDynamicTimeout()`, and `updateCheckpoint()` are defined in arc SKILL.md. `extractFilePaths()`, `deriveSeverity()`, `severityRank()`, and `countFindingsPerFile()` are defined inline in SKILL.md (utility block).

## extractErrorPatterns

**Inputs**: `tomeContent: string` (raw TOME markdown), `phaseName: string` (e.g. `"code_review"`), `checkpoint: object` (schema v15)
**Outputs**: Mutates `checkpoint.stagnation.error_patterns[]` in place
**Preconditions**: At least one TOME exists (Phase 6+ completed). `checkpoint.stagnation` initialized.
**Error handling**: Malformed TOME (no matching findings) → loop body never executes, no-op. Missing `checkpoint.stagnation` field → throw `Error("checkpoint.stagnation not initialized — schema v15 required")`.

```javascript
// Called after each TOME aggregation (Phase 6 code-review, Phase 7.5 verify-mend)
// SHA-256 fingerprinting deduplicates recurring errors across phases
function extractErrorPatterns(tomeContent: string, phaseName: string, checkpoint: object): void {
  if (!checkpoint.stagnation) {
    throw new Error("checkpoint.stagnation not initialized — schema v15 required")
  }

  // Parse TOME findings: [PREFIX-NNN] Title\n**Verdict**: ...\n**Evidence**: ...
  const findingRegex = /\[([\w]+-\d+)\]\s+(.+)\n\*\*Verdict\*\*:\s*(.+)/g

  for (const match of tomeContent.matchAll(findingRegex)) {
    const [, id, title, verdict] = match
    const prefix = id.split('-')[0]
    const severity = deriveSeverity(verdict)  // P1/P2/P3 from verdict text

    // Fingerprint: normalize title (lowercase, strip file paths and numbers)
    const normalized = title.toLowerCase()
      .replace(/`[^`]+`/g, 'PATH')    // Replace backtick file paths with placeholder
      .replace(/\d+/g, 'N')           // Replace numbers for deduplication
      .replace(/\s+/g, ' ').trim()
    const fingerprint = sha256(normalized).substring(0, 16)

    // Check if pattern already exists
    const existing = checkpoint.stagnation.error_patterns
      .find(p => p.fingerprint === fingerprint)

    if (existing) {
      // Update recurrence metadata
      existing.last_seen_phase = phaseName
      existing.occurrences += 1
      // Escalate severity if new occurrence is higher priority
      if (severityRank(severity) > severityRank(existing.severity)) {
        existing.severity = severity
      }
    } else {
      // Register new error pattern
      checkpoint.stagnation.error_patterns.push({
        fingerprint,
        first_seen_phase: phaseName,
        last_seen_phase: phaseName,
        occurrences: 1,
        affected_files: extractFilePaths(match[0]),
        finding_prefix: prefix,
        severity
      })
    }
  }
}
```

## updateFileVelocity

**Inputs**: `mendRound: number` (0-indexed convergence round), `checkpoint: object` (schema v15)
**Outputs**: Mutates `checkpoint.stagnation.file_velocity[]` in place
**Preconditions**: At least 1 mend round completed. `checkpoint.convergence.history[mendRound]` populated with `pre_mend_sha` and finding counts.
**Error handling**: Missing `pre_mend_sha` → warn and return. git diff failure → warn and return. `checkpoint.convergence.history[mendRound]` missing → warn and return.

```javascript
// Called after each mend round (Phase 7 → Phase 7.5)
// CONCERN-3 FIX: Use checkpoint.convergence.history[round] for finding counts
// instead of reading TOME-round-${mendRound}.md (those per-round files do not exist)
function updateFileVelocity(mendRound: number, checkpoint: object): void {
  if (!checkpoint.stagnation) {
    throw new Error("checkpoint.stagnation not initialized — schema v15 required")
  }

  const roundHistory = checkpoint.convergence.history[mendRound]
  if (!roundHistory) {
    warn(`Stagnation: No convergence history for mend round ${mendRound} — skipping velocity update`)
    return
  }

  // Get the SHA recorded before this mend round started
  const preMendSha = roundHistory?.pre_mend_sha
  if (!preMendSha || preMendSha === "null") {
    warn("Stagnation: Cannot compute file velocity — pre_mend_sha unavailable in convergence history")
    return
  }

  const postMendResult = Bash(`git rev-parse HEAD 2>/dev/null || echo "null"`)
  const postMendSha = postMendResult.stdout?.trim() ?? postMendResult.trim()

  if (!postMendSha || postMendSha === "null") {
    warn("Stagnation: Cannot compute file velocity — HEAD SHA unavailable")
    return
  }

  // Security pattern: SAFE_SHA_PATTERN — see security-patterns.md
  const SAFE_SHA_PATTERN = /^[0-9a-f]{7,40}$/
  if (!SAFE_SHA_PATTERN.test(preMendSha) || !SAFE_SHA_PATTERN.test(postMendSha)) {
    warn(`Stagnation: Unsafe SHA value — skipping velocity update`)
    return
  }

  const diffResult = Bash(`git diff --name-only ${preMendSha} ${postMendSha} 2>/dev/null`)
  const diffOutput = typeof diffResult === 'string' ? diffResult : diffResult.stdout ?? ''
  const modifiedFiles = diffOutput.trim().split('\n').filter(Boolean)

  if (modifiedFiles.length === 0) return

  // CONCERN-3 FIX: Get findings per file from convergence history round data
  // roundHistory.findings_per_file is a map of { [filename]: count } built during verify-mend
  // Falls back to roundHistory.finding_count (total) distributed across files if per-file unavailable
  const findingsPerFile = roundHistory.findings_per_file ?? {}

  for (const file of modifiedFiles) {
    const existing = checkpoint.stagnation.file_velocity
      .find(v => v.file === file)
    const findings = findingsPerFile[file] ?? 0

    if (existing) {
      existing.rounds_touched.push(mendRound)
      existing.findings_per_round.push(findings)

      // Classify velocity based on improvement over previous round
      const prevFindings = existing.findings_per_round[existing.findings_per_round.length - 2]
      const improvement = prevFindings > 0 ? (prevFindings - findings) / prevFindings : 0

      if (findings > prevFindings) {
        existing.velocity = "regressing"
      } else if (improvement < 0.10 && existing.rounds_touched.length >= 2) {
        existing.velocity = "stagnant"
      } else {
        existing.velocity = "improving"
      }
    } else {
      // First touch — register as improving by default
      checkpoint.stagnation.file_velocity.push({
        file,
        rounds_touched: [mendRound],
        findings_per_round: [findings],
        velocity: "improving"
      })
    }
  }
}
```

## checkBudgetForecast

**Inputs**: `checkpoint: object` (schema v15), `currentPhaseIndex: number` (0-indexed position in `PHASE_ORDER`)
**Outputs**: Mutates `checkpoint.stagnation.budget` in place; returns `forecast_status: string` (`"on_track"` | `"at_risk"` | `"overrun"`)
**Preconditions**: At least 2 phases completed (need avg to forecast). `checkpoint.totals.phase_times` populated.
**Error handling**: Missing `phase_times` → use hardcoded 10min fallback for `avgPhaseMs`. Missing `checkpoint.created_at` → use `checkpoint.started_at`. Missing `checkpoint.convergence.tier` → use default tier timeout.

```javascript
// Called between every phase in arc orchestrator (checkArcTimeout enhancement)
// CONCERN-4 FIX: Check overrun (elapsed > 90%) FIRST, then at_risk (projected > 85%)
// The plan pseudocode had the ternary order inverted — overrun must take priority
// because it's based on already-consumed budget, not a projection
function checkBudgetForecast(checkpoint: object, currentPhaseIndex: number): string {
  const startedAt = checkpoint.started_at ?? checkpoint.created_at
  if (!startedAt) {
    warn('checkBudgetForecast: Missing checkpoint timestamps (started_at and created_at both absent)')
    return "on_track"  // Fail-open: no timestamp data → cannot forecast, assume on_track
  }
  const elapsed = Date.now() - new Date(startedAt).getTime()
  if (isNaN(elapsed)) {
    warn('checkBudgetForecast: Invalid timestamp produced NaN elapsed time')
    return "on_track"  // Fail-open: corrupted timestamp → cannot forecast
  }
  const budget = calculateDynamicTimeout(checkpoint.convergence.tier)

  const completedPhases = Object.values(checkpoint.phases)
    .filter(p => p.status === "completed").length
  const phaseTimes = Object.values(checkpoint.totals?.phase_times ?? {})
  const avgPhaseMs = phaseTimes.length > 0
    ? phaseTimes.reduce((a, b) => a + b, 0) / phaseTimes.length
    : 600_000  // 10 min fallback if no phase timing data yet

  const remainingPhases = PHASE_ORDER.length - currentPhaseIndex
  const projectedTotal = elapsed + (avgPhaseMs * remainingPhases)
  const utilization = elapsed / budget

  // CONCERN-4 FIX: overrun check (elapsed-based) MUST precede at_risk check (projection-based)
  // Original plan ternary was wrong: projected > 85% ? at_risk : elapsed > 90% ? overrun : on_track
  // Correct order: elapsed > 90% ? overrun : projected > 85% ? at_risk : on_track
  const forecastStatus = elapsed > budget * 0.90 ? "overrun"
    : projectedTotal > budget * 0.85 ? "at_risk"
    : "on_track"

  checkpoint.stagnation.budget = {
    elapsed_ms: elapsed,
    budget_ms: budget,
    phases_completed: completedPhases,
    phases_remaining: remainingPhases,
    avg_phase_ms: Math.round(avgPhaseMs),
    projected_total_ms: Math.round(projectedTotal),
    budget_utilization: Math.round(utilization * 100) / 100,
    forecast_status: forecastStatus
  }

  // Emit non-blocking warnings
  if (forecastStatus === "overrun") {
    warn(`Stagnation Sentinel: Budget overrun imminent — ${Math.round(utilization * 100)}% consumed. Consider cancelling with /rune:cancel-arc.`)
  } else if (forecastStatus === "at_risk") {
    warn(`Stagnation Sentinel: Budget at risk — ${Math.round(utilization * 100)}% consumed, ${remainingPhases} phases remaining. Projected ${Math.round(projectedTotal / 60000)}min vs budget ${Math.round(budget / 60000)}min.`)
  }

  return forecastStatus
}
```

## checkStagnation

**Inputs**: `checkpoint: object` (schema v15)
**Outputs**: Stagnation diagnostic string (or `null` if healthy)
**Preconditions**: At least Phase 6 completed (need TOME data for meaningful error pattern analysis)
**Error handling**: Missing `checkpoint.stagnation` field → return `null` (no diagnostic). Missing sub-fields → skip that check, continue with others.

```javascript
// Called between every phase (enhancement to existing checkArcTimeout in arc SKILL.md)
// Aggregates all stagnation sub-checks into a single diagnostic report
// NON-BLOCKING: returns a warning string (or null). Never throws or halts pipeline.
function checkStagnation(checkpoint: object): string | null {
  const s = checkpoint.stagnation
  if (!s) return null

  const diagnostics = []

  // Check 1: Error repetition — same fingerprint seen in 3+ phases
  const repeating = (s.error_patterns ?? []).filter(p => p.occurrences >= 3)
  if (repeating.length > 0) {
    diagnostics.push(
      `REPEATING ERRORS (${repeating.length}): ` +
      repeating.map(p =>
        `${p.finding_prefix}-* in ${p.affected_files.join(',')} ` +
        `(${p.occurrences}x, first: ${p.first_seen_phase}, last: ${p.last_seen_phase})`
      ).join('; ')
    )
  }

  // Check 2: File stagnation — file touched in 3+ mend rounds without improving
  const stagnantFiles = (s.file_velocity ?? []).filter(
    v => v.velocity === "stagnant" && v.rounds_touched.length >= 3
  )
  if (stagnantFiles.length > 0) {
    diagnostics.push(
      `STAGNANT FILES (${stagnantFiles.length}): ` +
      stagnantFiles.map(v =>
        `${v.file} (${v.rounds_touched.length} rounds, findings: ${v.findings_per_round.join('→')})`
      ).join('; ')
    )
  }

  // Check 3: Regressing files — findings increasing between rounds
  const regressingFiles = (s.file_velocity ?? []).filter(v => v.velocity === "regressing")
  if (regressingFiles.length > 0) {
    diagnostics.push(
      `REGRESSING FILES (${regressingFiles.length}): ` +
      regressingFiles.map(v =>
        `${v.file} (findings: ${v.findings_per_round.join('→')})`
      ).join('; ')
    )
  }

  // Check 4: Budget forecast status
  if (s.budget?.forecast_status === "at_risk" || s.budget?.forecast_status === "overrun") {
    diagnostics.push(
      `BUDGET ${s.budget.forecast_status.toUpperCase()}: ` +
      `${Math.round(s.budget.budget_utilization * 100)}% consumed, ` +
      `${s.budget.phases_remaining} phases left`
    )
  }

  if (diagnostics.length === 0) return null

  return `Stagnation Sentinel Report:\n${diagnostics.map(d => `  - ${d}`).join('\n')}`
}
```

## Integration Points

### arc SKILL.md (after each `updateCheckpoint()` call)

```javascript
// Stagnation Sentinel — non-blocking diagnostic check after every phase
// See references/stagnation-sentinel.md for full algorithm
const stagnationReport = checkStagnation(checkpoint)
if (stagnationReport) {
  warn(stagnationReport)
  // NON-BLOCKING: warn only. User can /rune:cancel-arc if needed.
  // Future: configurable halt threshold in talisman.yml
}
```

### verify-mend.md (Phase 7.5 — after TOME aggregation)

```javascript
// After TOME aggregation, update error pattern fingerprints
extractErrorPatterns(tomeContent, "verify_mend", checkpoint)

// After each mend round, update file-change velocity
updateFileVelocity(checkpoint.convergence.round, checkpoint)

// Budget forecast check (also called from arc SKILL.md between all phases)
checkBudgetForecast(checkpoint, currentPhaseIndex)
```

### Checkpoint initialization

The `stagnation` field is initialized in `arc-checkpoint-init.md` as part of the Write() call (schema v15):

```javascript
stagnation: {
  error_patterns: [],
  file_velocity: [],
  budget: null
}
```

## Schema — checkpoint.stagnation

```javascript
{
  error_patterns: [
    {
      fingerprint: string,        // sha256(normalized_title).substring(0, 16)
      first_seen_phase: string,   // Phase where error first appeared
      last_seen_phase: string,    // Most recent phase
      occurrences: number,        // Total count across phases
      affected_files: string[],   // Files associated with this error
      finding_prefix: string,     // TOME prefix (e.g. "SEC", "BACK")
      severity: string            // Highest severity seen: "P1" | "P2" | "P3"
    }
  ],
  file_velocity: [
    {
      file: string,               // Relative file path
      rounds_touched: number[],   // Which mend rounds (0-indexed) modified this file
      findings_per_round: number[], // Finding count per round for this file
      velocity: string            // "improving" | "stagnant" | "regressing"
    }
  ],
  budget: null | {
    elapsed_ms: number,           // Total elapsed time since arc started
    budget_ms: number,            // Dynamic timeout for current tier
    phases_completed: number,     // Count of completed phases
    phases_remaining: number,     // Count of remaining phases
    avg_phase_ms: number,         // Average phase duration so far
    projected_total_ms: number,   // Projected total if avg phase time continues
    budget_utilization: number,   // elapsed / budget (0.0–1.0)
    forecast_status: string       // "on_track" | "at_risk" | "overrun"
  }
}
```

## Velocity Classification

| Condition | Status |
|-----------|--------|
| First touch | `"improving"` (default) |
| findings increased between rounds | `"regressing"` |
| `rounds_touched.length >= 2` AND improvement < 10% | `"stagnant"` |
| improvement >= 10% | `"improving"` |

## Budget Forecast Thresholds

| Condition | Status | Action |
|-----------|--------|--------|
| `elapsed > budget * 0.90` | `"overrun"` | WARN: suggest `/rune:cancel-arc` |
| `projected_total > budget * 0.85` | `"at_risk"` | WARN: phases remaining + projection |
| neither | `"on_track"` | No warning |

> **Note**: `overrun` check (elapsed-based) takes priority over `at_risk` check (projection-based). See CONCERN-4 fix in [concern-context.md](../../../tmp/arc/arc-1771829206/concern-context.md).
