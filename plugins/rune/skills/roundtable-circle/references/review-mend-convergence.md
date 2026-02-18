# Review-Mend Convergence — Shared Reference

Shared tier selection, convergence evaluation, and progressive focus logic for both arc (Phase 6-7.5 loop) and standalone `/rune:review --cycles N`.

## 3-Tier Adaptive Convergence

The number of review-mend cycles scales with changeset complexity.

| Tier | Review-Mend Cycles | Trigger |
|------|-------------------|---------|
| **LIGHT** | 2 | ≤100 lines changed AND no high-risk files AND type=fix |
| **STANDARD** | 3 | 100-2000 lines OR mixed code/docs (default) |
| **THOROUGH** | 5 | >2000 lines OR high-risk files OR architectural changes |

## Tier Selection Engine

**Inputs**: `git diff --stat`, plan frontmatter (optional), talisman config
**Outputs**: `{ tier, maxCycles, reason }` — selected convergence tier
**Error handling**: Missing git stats → default STANDARD; invalid talisman config → ignore with warning

```javascript
// Security-critical path patterns (reuse from chunk-scoring.md)
// Security pattern: HIGH_RISK_PATTERNS — see security-patterns.md
const HIGH_RISK_PATTERNS = [
  '**/auth/**', '**/middleware/auth*', '**/security/**',
  '**/validators/**', '**/*permission*', '**/crypto/**',
  '**/payment/**', '**/migrate/**', '**/migration*',
]

const TIERS = {
  light:    { name: 'LIGHT',    maxCycles: 2 },
  standard: { name: 'STANDARD', maxCycles: 3 },
  thorough: { name: 'THOROUGH', maxCycles: 5 },
}

// SEC-007 helper: compute auto-tier without config override (for warning comparison)
function computeAutoTier(diffStats, planMeta) {
  const totalLines = diffStats.insertions + diffStats.deletions
  const hasHighRisk = diffStats.files.some(f => matchesAnyPattern(f, HIGH_RISK_PATTERNS))
  const planType = planMeta?.type
  const fileCount = diffStats.files.length
  if (totalLines > 2000 || hasHighRisk || (planType === 'feat' && fileCount > 20)) return 'thorough'
  if (totalLines <= 100 && !hasHighRisk && planType === 'fix') return 'light'
  return 'standard'
}

function selectReviewMendTier(diffStats, planMeta, config) {
  // User override via talisman.yml (arc-specific namespace per decree-arbiter P1)
  // NOTE: Uses arc_convergence_tier_override (not convergence_tier_override)
  // to avoid collision with chunked review's convergence_tier_override key.
  const override = config?.review?.arc_convergence_tier_override
  // SEC-004 FIX: Type-check override before TIERS lookup — reject non-string values (arrays, objects)
  if (typeof override === 'string' && TIERS[override]) {
    // SEC-007: Compute auto-tier for comparison — warn if override disagrees
    const autoTier = computeAutoTier(diffStats, planMeta)
    if (autoTier && autoTier !== override) {
      warn(`Tier override "${override}" disagrees with auto-detected "${autoTier}" — using override. This may increase compute time.`)
    }
    return { ...TIERS[override], reason: `User override: ${override} (auto-detected: ${autoTier ?? 'unknown'})` }
  }

  // Signal 1: Total lines changed (primary signal)
  const totalLines = diffStats.insertions + diffStats.deletions

  // Signal 2: High-risk files present?
  const hasHighRisk = diffStats.files.some(f => matchesAnyPattern(f, HIGH_RISK_PATTERNS))

  // Signal 3: Plan type (from frontmatter, if available)
  // NOTE: planMeta is null for standalone review (no plan context).
  // In standalone mode, only Signal 1, 2, and 4 are used.
  const planType = planMeta?.type  // 'feat', 'fix', 'refactor'

  // Signal 4: File count (secondary)
  const fileCount = diffStats.files.length

  // Tier selection — highest matching wins
  if (totalLines > 2000 || hasHighRisk || (planType === 'feat' && fileCount > 20)) {
    return { ...TIERS.thorough,
      reason: totalLines > 2000 ? `Large changeset (${totalLines} lines)`
        : hasHighRisk ? 'High-risk files detected'
        : `Large feature (${fileCount} files)` }
  }

  if (totalLines <= 100 && !hasHighRisk && planType === 'fix') {
    return { ...TIERS.light,
      reason: `Small fix (${totalLines} lines, no high-risk files)` }
  }

  return { ...TIERS.standard,
    reason: `Default (${totalLines} lines, ${fileCount} files)` }
}
```

## Convergence Evaluation

Used by Phase 7.5 to decide: converge, retry, or halt.

**Inputs**: Current TOME finding counts, convergence history, tier config
**Outputs**: Verdict (`converged` | `retry` | `halted`)

```javascript
function evaluateConvergence(currentFindingCount, p1Count, checkpoint, config, scopeStats) {
  const round = checkpoint.convergence.round
  // SEC-005: Apply arc_convergence_max_cycles override with clamping (1-5)
  const rawMaxCycles = config?.review?.arc_convergence_max_cycles
  // SEC-002 FIX: Use Number.isNaN instead of || to avoid falsy-zero bug (parseInt("1") || 3 = 1, but parseInt("0") || 3 = 3)
  // SEC-005 FIX: Type guard — reject arrays/objects from YAML (parseInt([3], 10) returns 3 silently)
  const parsedMaxCycles = (rawMaxCycles != null && (typeof rawMaxCycles === 'number' || typeof rawMaxCycles === 'string'))
    ? parseInt(String(rawMaxCycles), 10) : NaN
  const maxCycles = !Number.isNaN(parsedMaxCycles)
    ? Math.max(1, Math.min(5, parsedMaxCycles))
    // BACK-001 NOTE: checkpoint.convergence.max_rounds is a legacy field — not read by evaluateConvergence.
    // The canonical source is tier.maxCycles (from checkpoint.convergence.tier). max_rounds remains
    // in checkpoint schema for backward compatibility but is effectively dead data.
    : checkpoint.convergence.tier?.maxCycles ?? TIERS.standard.maxCycles
  // SEC-003 FIX: Add upper bound (100) to prevent threshold=9999 from bypassing convergence
  // QUAL-005 FIX: Match rawMaxCycles pattern — separate extraction from parsing, type-guard before parseInt
  const rawThresholdVal = config?.review?.arc_convergence_finding_threshold
  const rawThreshold = (rawThresholdVal != null && (typeof rawThresholdVal === 'number' || typeof rawThresholdVal === 'string'))
    ? parseInt(String(rawThresholdVal), 10) : NaN
  const findingThreshold = !Number.isNaN(rawThreshold) ? Math.max(0, Math.min(100, rawThreshold)) : 0
  // Validate ratio: reject values outside (0.1, 0.9)
  const rawRatio = parseFloat(config?.review?.arc_convergence_improvement_ratio ?? 0.5)
  const improvementRatio = isNaN(rawRatio) ? 0.5 : Math.max(0.1, Math.min(0.9, rawRatio))

  // Get previous round's finding count
  // BACK-002 NOTE: Invariant: round === history.length throughout the convergence lifecycle.
  // Oscillation detection (line 134) uses history.length; evaluation uses round. They MUST stay in sync.
  const prevFindings = round === 0 ? Infinity
    : checkpoint.convergence.history[round - 1]?.findings_after ?? Infinity

  // Decision cascade
  // BACK-003 NOTE: findingThreshold checks P1 count only (not total findings).
  // The talisman key arc_convergence_finding_threshold is a P1-specific threshold.
  if (p1Count <= findingThreshold) {
    return 'converged'  // P1 count below acceptable threshold
  }

  // Smart convergence scoring (v1.38.0+) — scope-aware early convergence
  // When diff-scope data is available, compute a composite score from P3 dominance,
  // pre-existing noise, and trend signals. High scores (>= threshold) trigger early
  // convergence even when total finding count hasn't reached zero.
  // scopeStats is optional — null/undefined for pre-v1.38.0 TOMEs or disabled diff-scope.
  if (scopeStats && config?.review?.diff_scope?.enabled !== false) {
    const smartScoringEnabled = config?.review?.convergence?.smart_scoring !== false  // Default: true
    if (smartScoringEnabled) {
      const score = computeConvergenceScore(scopeStats, checkpoint, config)
      const convergenceThreshold = parseFloat(config?.review?.convergence?.convergence_threshold ?? 0.7)
      const safeThreshold = isNaN(convergenceThreshold) ? 0.7 : Math.max(0.1, Math.min(1.0, convergenceThreshold))
      if (score.total >= safeThreshold) {
        return 'converged'  // Smart scoring: remaining findings are mostly P3/pre-existing noise
      }
    }
  }
  if (round + 1 >= maxCycles) {
    return 'halted'     // Max cycles reached — circuit breaker
  }
  // BACK-016 FIX: Check P1 progress alongside total count — severity shift (P1→P3) is meaningful
  // even when total count unchanged. prevP1 defaults to Infinity for round 0 (same as prevFindings).
  const prevP1 = round === 0 ? Infinity
    : checkpoint.convergence.history[round - 1]?.p1_remaining ?? Infinity
  if (currentFindingCount >= prevFindings && p1Count >= prevP1) {
    return 'halted'     // Findings not decreasing AND P1 not improving — truly stagnant
  }
  // BACK-005 FIX: Oscillation detection — compare only against round N-2 (A→B→A pattern).
  // Previous version compared ALL prior rounds, but scope changes (full → focused) make
  // cross-scope count comparisons unreliable.
  if (checkpoint.convergence.history.length >= 2) {
    const twoRoundsBack = checkpoint.convergence.history[checkpoint.convergence.history.length - 2]
    if (twoRoundsBack && twoRoundsBack.findings_after === currentFindingCount) {
      return 'halted'   // Oscillation detected (A→B→A pattern)
    }
  }
  // Improvement ratio check (guard prevFindings > 0 for NaN safety)
  if (currentFindingCount > 0 && prevFindings > 0 &&
      currentFindingCount / prevFindings > (1 - improvementRatio)) {
    return 'halted'     // Improvement too small — diminishing returns
  }

  return 'retry'        // Findings decreasing meaningfully — another cycle
}
```

## Smart Convergence Scoring (v1.38.0+)

Computes a composite convergence score from scope-aware signals. Used by `evaluateConvergence()` to detect early convergence when remaining findings are mostly noise (P3 severity or pre-existing code).

**Inputs**: `scopeStats` (from TOME parsing), `checkpoint`, `config`
**Outputs**: `{ total, components, reason }` — score between 0.0 and 1.0
**Error handling**: Missing/null scopeStats → returns null (caller must guard). P1 > 0 → returns 0.0 (hard gate).

```javascript
function computeConvergenceScore(scopeStats, checkpoint, config) {
  if (!scopeStats || typeof scopeStats !== 'object') return null

  const { p1Count, p3Count, preExistingCount, inDiffCount, totalFindings } = scopeStats

  // Hard gate: P1 findings prevent smart convergence — always retry or fix
  if (p1Count > 0) {
    return { total: 0.0, components: { p3: 0, preExisting: 0, trend: 0, base: 0 }, reason: 'p1_active' }
  }

  // Guard: no findings = fully converged
  if (totalFindings === 0) {
    return { total: 1.0, components: { p3: 0, preExisting: 0, trend: 0, base: 1.0 }, reason: 'zero_findings' }
  }

  // Edge case: zero in-diff findings — all findings are pre-existing
  // If nothing in the PR diff remains, this is ideal convergence
  if (inDiffCount === 0 && totalFindings > 0) {
    return { total: 1.0, components: { p3: 0, preExisting: 1.0, trend: 0, base: 1.0 }, reason: 'zero_in_diff' }
  }

  // Component 1: P3 dominance ratio (weight: 0.4)
  // High P3 ratio means remaining findings are low-severity polish items
  const p3Ratio = totalFindings > 0 ? p3Count / totalFindings : 0

  // Component 2: Pre-existing noise ratio (weight: 0.3)
  // High pre-existing ratio means findings aren't caused by this PR
  const preExistingRatio = totalFindings > 0 ? preExistingCount / totalFindings : 0

  // Component 3: Trend — findings decreasing from previous round? (weight: 0.2)
  const round = checkpoint.convergence?.round ?? 0
  const prevFindings = round === 0 ? Infinity
    : checkpoint.convergence.history[round - 1]?.findings_after ?? Infinity
  const trendDecreasing = (totalFindings < prevFindings) ? 1.0 : 0.0

  // Component 4: Base (weight: 0.1) — always contributes minimum score
  const base = 1.0

  // Weights — hardcoded for v1.38.0. Talisman-configurable in future version.
  // Sum must equal 1.0: 0.4 + 0.3 + 0.2 + 0.1 = 1.0
  const total = 0.4 * p3Ratio + 0.3 * preExistingRatio + 0.2 * trendDecreasing + 0.1 * base

  return {
    total: Math.round(total * 100) / 100,  // Round to 2 decimal places
    components: {
      p3: Math.round(p3Ratio * 100) / 100,
      preExisting: Math.round(preExistingRatio * 100) / 100,
      trend: trendDecreasing,
      base
    },
    reason: null
  }
}
```

### Score Interpretation

| Score Range | Verdict Effect | Meaning |
|-------------|---------------|---------|
| >= 0.7 | `converged` | Remaining findings are mostly P3/pre-existing noise — safe to stop |
| 0.5 - 0.7 | No effect (existing logic decides) | Mixed signals — let improvement ratio and cycle limits decide |
| < 0.5 | No effect (existing logic decides) | Active findings remain — existing halting conditions apply |
| 0.0 | Always | P1 findings present — never converge via smart scoring |

### Talisman Config Keys (smart convergence)

Under `review:` section. Requires `diff_scope.enabled: true` (default) for scope stats to be available.

```yaml
review:
  convergence:
    smart_scoring: true              # Enable smart convergence scoring (default: true)
    convergence_threshold: 0.7       # Score >= this = converged (default: 0.7, range: 0.1-1.0)
    p3_dominance_threshold: 0.7      # RESERVED — per-component threshold for future use
    noise_threshold: 0.5             # RESERVED — per-component threshold for future use
```

## Progressive Review Focus

For re-review rounds (pass 2+), narrow scope to mend-modified files + 1-hop dependencies.

**Inputs**: Mend-modified files, resolution report, full file list
**Outputs**: Focused file list capped at mend-modified + 10 dependencies
**Error handling**: Dependency extraction failure → fall back to mend-modified files only

```javascript
function buildProgressiveFocus(resolutionReport, originalChangedFiles) {
  const mendModifiedFiles = extractFixedFiles(resolutionReport)
  // EC-7: Include files with unfixed P1/P2 findings
  const unfixedFiles = extractUnfixedFiles(resolutionReport, ['P1', 'P2'])
  const allFocusFiles = [...new Set([...mendModifiedFiles, ...unfixedFiles])]

  let dependencies = []
  try {
    dependencies = collectOneHopDependencies(allFocusFiles, 10)  // max 10
  } catch (e) {
    warn(`Dependency collection failed: ${e.message} — using mend-modified files only`)
  }

  const focusScope = [...new Set([...allFocusFiles, ...dependencies])]

  // EC-9: Guard against empty focusScope
  if (focusScope.length === 0) {
    if (mendModifiedFiles.length > 0) {
      // Paradox: fixed files exist but none in scope — fall back to full changed_files
      warn(`focusScope empty despite ${mendModifiedFiles.length} fixed files — using full scope`)
      return { focus_files: originalChangedFiles, mend_modified: mendModifiedFiles, unfixed_files: unfixedFiles, dependency_files: [] }
    }
    return null  // Signal: no files modified, halt convergence
  }

  return {
    focus_files: focusScope,
    mend_modified: mendModifiedFiles,
    unfixed_files: unfixedFiles,
    dependency_files: dependencies,
  }
}
```

### 1-Hop Dependency Collection

```javascript
function collectOneHopDependencies(modifiedFiles, maxDeps) {
  if (!modifiedFiles || modifiedFiles.length === 0) return []  // Guard: empty input → empty Grep match
  const deps = new Set()
  for (const file of modifiedFiles) {
    // Extract imports from the modified file (reuse from chunk-orchestrator.md)
    const imports = extractImports(file)
    for (const imp of imports) {
      if (!modifiedFiles.includes(imp)) deps.add(imp)
    }
    // Find files that import the modified file (reverse dependencies)
    // SEC: Escape basename for regex safety (dots, brackets, etc.)
    const escapedBasename = basename(file).replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    const importers = Grep(`import.*${escapedBasename}|require.*${escapedBasename}`, { type: ext(file) })
    for (const importer of importers) {
      if (!modifiedFiles.includes(importer)) deps.add(importer)
    }
  }
  return [...deps].slice(0, maxDeps)
}
```

## Talisman Config Keys (arc-specific)

Under `review:` section in talisman.yml. Uses `arc_` prefix to avoid collision with existing chunked review convergence keys.

```yaml
review:
  # Arc review-mend convergence (v1.37.0+)
  # NOTE: These keys use 'arc_' prefix to distinguish from chunked review
  # convergence keys (convergence_tier_override, convergence_density_threshold, etc.)
  arc_convergence_tier_override: null     # Force: "light" | "standard" | "thorough" | null
  arc_convergence_max_cycles: null        # Hard override: 1-5 (overrides tier, use sparingly)
  arc_convergence_finding_threshold: 0    # P1 findings below this count = converged (default: 0)
  arc_convergence_improvement_ratio: 0.5  # Findings must decrease by this ratio to continue (default: 0.5)
```

**Validation**:
- `arc_convergence_max_cycles`: Clamped to 1-5 range. Values outside are silently clamped.
- `arc_convergence_improvement_ratio`: Clamped to 0.1-0.9 range. NaN → 0.5 default.
- `arc_convergence_tier_override`: Must be a key of `TIERS` or null. Invalid values ignored with warning.

## Scope Limitation Note

**SCOPE-BIAS** (P3 — partially mitigated in v1.38.0): `findings_before` comparison is biased by scope reduction (full → focused review). Pass 1 reviews all changed files; pass 2+ reviews only mend-modified files + dependencies. A decrease in findings may reflect narrower scope rather than code improvement.

**v1.38.0 mitigation**: Smart convergence scoring (`computeConvergenceScore()`) partially addresses this by evaluating finding COMPOSITION (P3 ratio, pre-existing ratio) rather than raw count. A focused review with 5 P3 pre-existing findings scores higher than 5 P1 in-diff findings, correctly identifying the former as noise. However, the raw `findings_before` vs `findings_after` comparison in `evaluateConvergence()` (line ~145) still uses counts without scope adjustment. Full scope-adjusted ratio remains a future improvement.
