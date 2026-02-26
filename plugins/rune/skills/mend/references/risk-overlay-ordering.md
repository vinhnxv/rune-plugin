# Risk-Overlaid Severity Ordering — Phase 1 Goldmask Enhancement

> When `parsedRiskMap` is available from Phase 0.5, overlay risk tiers on finding severity ordering.
> Ensures CRITICAL-tier files are fixed first within each priority level.
> Skip condition: When `parsedRiskMap` is `null`, original severity ordering is preserved.

## Algorithm

```javascript
// Only runs when Phase 0.5 produced a valid parsedRiskMap
if (parsedRiskMap) {
  // Annotate each finding with risk tier
  for (const finding of allFindings) {
    const fileRisk = parsedRiskMap.files?.find(f => f.path === finding.file)
    if (fileRisk) {
      finding.riskTier = fileRisk.tier       // CRITICAL, HIGH, MEDIUM, LOW, STALE
      finding.riskScore = fileRisk.risk_score // 0.0-1.0
    } else {
      finding.riskTier = 'UNKNOWN'
      finding.riskScore = 0
    }
  }

  // Within same priority level, sort by risk tier (CRITICAL first)
  // Deterministic tiebreaker: alphabetical file path when tier and priority are equal (BACK-004)
  const tierOrder = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3, STALE: 4, UNKNOWN: 5 }
  allFindings.sort((a, b) => {
    if (a.priority !== b.priority) return a.priority - b.priority  // P1 first
    const tierDiff = (tierOrder[a.riskTier] ?? 5) - (tierOrder[b.riskTier] ?? 5)
    if (tierDiff !== 0) return tierDiff
    return (a.file ?? '').localeCompare(b.file ?? '')  // alphabetical tiebreaker for CI reproducibility
  })

  // Promote P3 findings in CRITICAL files to effective P2
  for (const finding of allFindings) {
    if (finding.priority === 3 && finding.riskTier === 'CRITICAL') {
      finding.promotedReason = "P3 promoted: CRITICAL-tier file (Goldmask risk overlay)"
      finding.effectivePriority = 2  // Treat as P2 for ordering and triage
    }
  }

  const promotedCount = allFindings.filter(f => f.promotedReason).length
  if (promotedCount > 0) {
    warn(`Phase 1: ${promotedCount} P3 findings promoted to effective P2 (CRITICAL-tier files)`)
  }
}
```
