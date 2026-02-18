# Review-Mend Convergence — Shared Reference

Shared tier selection, convergence evaluation, and progressive focus logic for both arc (Phase 6-7.5 loop) and standalone `/rune:review --cycles N`.

## 3-Tier Adaptive Convergence

The number of review-mend cycles scales with changeset complexity.

| Tier | Review-Mend Cycles | Trigger |
|------|-------------------|---------|
| **LIGHT** | 1-2 | ≤100 lines changed AND no high-risk files AND type=fix |
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

function selectReviewMendTier(diffStats, planMeta, config) {
  // User override via talisman.yml (arc-specific namespace per decree-arbiter P1)
  // NOTE: Uses arc_convergence_tier_override (not convergence_tier_override)
  // to avoid collision with chunked review's convergence_tier_override key.
  const override = config?.review?.arc_convergence_tier_override
  if (override && TIERS[override]) {
    return { ...TIERS[override], reason: `User override: ${override}` }
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
function evaluateConvergence(currentFindingCount, p1Count, checkpoint, config) {
  const round = checkpoint.convergence.round
  const maxCycles = checkpoint.convergence.tier?.maxCycles ?? TIERS.standard.maxCycles
  const findingThreshold = Math.max(0, parseInt(config?.review?.arc_convergence_finding_threshold ?? 0, 10)) || 0
  // Validate ratio: reject values outside (0.1, 0.9)
  const rawRatio = parseFloat(config?.review?.arc_convergence_improvement_ratio ?? 0.5)
  const improvementRatio = isNaN(rawRatio) ? 0.5 : Math.max(0.1, Math.min(0.9, rawRatio))

  // Get previous round's finding count
  const prevFindings = round === 0 ? Infinity
    : checkpoint.convergence.history[round - 1]?.findings_after ?? Infinity

  // Decision cascade
  if (p1Count <= findingThreshold) {
    return 'converged'  // P1 count below acceptable threshold
  }
  if (round + 1 >= maxCycles) {
    return 'halted'     // Max cycles reached — circuit breaker
  }
  if (currentFindingCount >= prevFindings) {
    return 'halted'     // Findings not decreasing — diverging or stagnant
  }
  // Oscillation detection: finding count matches a prior round (ported from convergence-gate.md)
  if (checkpoint.convergence.history.length >= 2 &&
      checkpoint.convergence.history.some(h => h.findings_after === currentFindingCount)) {
    return 'halted'     // Oscillation detected
  }
  // Improvement ratio check (guard prevFindings > 0 for NaN safety)
  if (currentFindingCount > 0 && prevFindings > 0 &&
      currentFindingCount / prevFindings > (1 - improvementRatio)) {
    return 'halted'     // Improvement too small — diminishing returns
  }

  return 'retry'        // Findings decreasing meaningfully — another cycle
}
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
  # Arc review-mend convergence (v1.38.0+)
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

**SCOPE-BIAS** (P3 — unresolved): `findings_before` comparison is biased by scope reduction (full → focused review). Pass 1 reviews all changed files; pass 2+ reviews only mend-modified files + dependencies. A decrease in findings may reflect narrower scope rather than code improvement. This is a known limitation — consider scope-adjusted ratio in a future version.
