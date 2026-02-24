# Risk Tier Sorting and Promotion

Shared risk tier enumeration, ordering constants, sorting algorithm, and P3-to-P2 promotion logic used by mend (Phase 1), forge (Phase 2), and inspect (Phase 1.3.3).

**Inputs**: `parsedRiskMap` (object with `files` array), `allFindings` or `scopeFiles` (array), `requirements` (array, inspect only)
**Outputs**: Risk-annotated and re-sorted findings/files, promoted findings (mend/inspect)
**Preconditions**: `parsedRiskMap` is non-null and has a valid `files` array

## Tier Enumeration and Ordering

```javascript
const TIER_ORDER = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3, STALE: 4, UNKNOWN: 5 }
```

Risk tiers assigned by lore-analyst based on git history metrics (churn frequency, ownership concentration, co-change coupling).

## getMaxRiskTier Helper

Returns the highest risk tier among a list of files.

```javascript
// Generic signature — callers pass their own risk data structure
// mend/inspect: riskFiles is a flat array (RiskEntry[])
// forge: parsedRiskMap is { files: RiskEntry[] }
function getMaxRiskTier(files: string[], riskFiles: RiskEntry[]): string {
  const tierOrder = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3, STALE: 4, UNKNOWN: 5 }
  let maxTier = 'UNKNOWN'
  for (const f of files) {
    const entry = riskFiles.find(r => r.path === f)
    const tier = entry?.tier ?? 'UNKNOWN'
    if ((tierOrder[tier] ?? 5) < (tierOrder[maxTier] ?? 5)) {
      maxTier = tier
    }
  }
  return maxTier
}
```

**Note**: Forge signature differs — second param is the full parsed risk-map object (`{ files: RiskEntry[] }`), not a flat `RiskEntry[]` array. The lookup uses `parsedRiskMap.files?.find(...)`.

## Sorting Algorithm (Risk-Weighted)

Re-sort items by risk tier after standard priority ordering:

```javascript
// Within same priority level, sort by risk tier (CRITICAL first)
// Deterministic tiebreaker: alphabetical file path (BACK-004)
items.sort((a, b) => {
  if (a.priority !== b.priority) return a.priority - b.priority  // P1 first
  const tierDiff = (TIER_ORDER[a.riskTier] ?? 5) - (TIER_ORDER[b.riskTier] ?? 5)
  if (tierDiff !== 0) return tierDiff
  return (a.file ?? '').localeCompare(b.file ?? '')  // alphabetical tiebreaker for CI reproducibility
})
```

## P3-to-P2 Promotion Logic

Promote P3 findings in CRITICAL-tier files to effective P2:

```javascript
for (const finding of allFindings) {
  if (finding.priority === 3 && finding.riskTier === 'CRITICAL') {
    finding.promotedReason = "P3 promoted: CRITICAL-tier file (Goldmask risk overlay)"
    finding.effectivePriority = 2  // Treat as P2 for ordering and triage
  }
}

const promotedCount = allFindings.filter(f => f.promotedReason).length
if (promotedCount > 0) {
  warn(`Phase N: ${promotedCount} P3 findings promoted to effective P2 (CRITICAL-tier files)`)
}
```

## Risk-Boosted Scoring (Forge-Specific)

Forge applies score boosts to Forge Gaze agent selections based on file risk:

```javascript
if (maxRiskTier === 'CRITICAL') {
  // Boost all agent scores by 0.15 (heuristic — subject to tuning)
  for (const agentEntry of agents) {
    agentEntry[1] = Math.min(agentEntry[1] + 0.15, 1.0)
  }
  section.riskBoost = 0.15
  section.autoIncludeResearchBudget = true
} else if (maxRiskTier === 'HIGH') {
  // Boost by 0.08
  for (const agentEntry of agents) {
    agentEntry[1] = Math.min(agentEntry[1] + 0.08, 1.0)
  }
  section.riskBoost = 0.08
}
// MEDIUM/LOW/STALE/UNKNOWN: no boost
```

## inspect-Specific: Dual Inspector Gate

When inspect encounters CRITICAL-tier files, it conditionally activates dual inspector assignment:

```javascript
if (maxRiskTier === 'CRITICAL') {
  req.inspectionPriority = 'HIGH'
  req.riskNote = "Touches CRITICAL-tier files — requires thorough inspection"
  // Dual inspector gate: only activate when plan has security-sensitive sections
  // OR talisman explicitly enables dual_inspector_gate
  const hasSecurity = requirements.some(r => /security|auth|crypt|token|inject|xss|sqli/i.test(r.text))
  const dualGateEnabled = inspectConfig.dual_inspector_gate ?? hasSecurity
  if (dualGateEnabled) {
    req.assignedInspectors = ['grace-warden', 'ruin-prophet']
  }
} else if (maxRiskTier === 'HIGH') {
  req.inspectionPriority = 'ELEVATED'
}
```
