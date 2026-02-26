# Risk Context Injection — Phase 3 Enhancement

> Injects Goldmask risk data into each inspector's prompt when `riskMap` is available from Phase 1.3.

## Injection Protocol

For each inspector, build a `riskContext` string from three sources:

### Section 1+3: File Risk Tiers + Blast Radius

Render from `risk-map.json` using the shared [risk-context-template.md](../../goldmask/references/risk-context-template.md).

```javascript
if (riskMap) {
  riskContext = renderRiskContextTemplate(riskMap, inspectorFiles)
}
```

### Section 2: Wisdom Advisories Passthrough

Filter wisdom data for inspector-relevant files. Each advisory includes file path, intent classification, caution score, and advisory text.

```javascript
if (wisdomData) {
  const advisories = filterWisdomForFiles(wisdomData, inspectorFiles)
  if (advisories.length > 0) {
    riskContext += "\n\n### Caution Zones\n\n"
    for (const adv of advisories) {
      riskContext += `- **\`${adv.file}\`** -- ${adv.intent} intent (caution: ${adv.cautionScore}). ${adv.advisory}\n`
    }
    riskContext += "\n**IMPORTANT**: Preserve the original design intent of these code sections."
    riskContext += " Your inspection must flag changes that break defensive, constraint, or compatibility behavior.\n"
  }
}
```

### Inspector-Specific Risk Guidance

| Inspector | Guidance |
|-----------|----------|
| `grace-warden` | Prioritize completeness checks on CRITICAL-tier files. Requirements touching these have outsized impact. |
| `ruin-prophet` | CRITICAL-tier files with DEFENSIVE or CONSTRAINT intent require extra scrutiny — they guard against known failure modes. |
| `sight-oracle` | CRITICAL-tier files with high churn suggest unstable architecture — check for coupling issues. |
| `vigil-keeper` | Files with ownership concentration (1-2 owners) have bus factor risk — check test coverage and documentation. |

## Rendering Rule

Only inject when `riskContext` is non-empty. Empty risk context = omit entirely. See [risk-context-template.md](../../goldmask/references/risk-context-template.md) for rendering rules.
