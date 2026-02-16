# Phase 6: CODE REVIEW — Full Algorithm

Invoke `/rune:review` logic on the implemented changes. Summons Ash with Roundtable Circle lifecycle.

**Team**: `arc-review-{id}` (delegated to `/rune:review` -- manages its own TeamCreate/TeamDelete with guards)
**Tools**: Read, Glob, Grep, Write (own output file only)
**Timeout**: 15 min (PHASE_TIMEOUTS.code_review — inner 10m + 5m setup)
**Inputs**: id (string), gap analysis path (optional: `tmp/arc/{id}/gap-analysis.md`)
**Outputs**: `tmp/arc/{id}/tome.md`
**Error handling**: Does not halt — review always produces findings or a clean report. Timeout → partial results collected. Team creation failure → cleanup fallback via `rm -rf` (see [team-lifecycle-guard.md](team-lifecycle-guard.md)).
**Consumers**: arc.md (Phase 6 stub)

## Algorithm

```javascript
// STEP 1: Propagate gap analysis to reviewers as additional context
let reviewContext = ""
if (exists(`tmp/arc/${id}/gap-analysis.md`)) {
  const gapReport = Read(`tmp/arc/${id}/gap-analysis.md`)
  const missingMatch = gapReport.match(/\| MISSING \| (\d+) \|/)
  const missingCount = missingMatch ? parseInt(missingMatch[1], 10) : 0
  const partialMatch = gapReport.match(/\| PARTIAL \| (\d+) \|/)
  const partialCount = partialMatch ? parseInt(partialMatch[1], 10) : 0
  if (missingCount > 0 || partialCount > 0) {
    reviewContext = `\n\nGap Analysis Context: ${missingCount} MISSING, ${partialCount} PARTIAL criteria.\nSee tmp/arc/${id}/gap-analysis.md.`
  }
}

// STEP 2: Codex Oracle conditional inclusion
// Run Codex detection per roundtable-circle/references/codex-detection.md.
// If detected and "review" is in talisman.codex.workflows, include Codex Oracle.
// Codex Oracle findings use CDX prefix and participate in dedup and TOME aggregation.

// STEP 3: Delegate to /rune:review
// /rune:review manages its own team lifecycle (TeamCreate, Rune Gaze agent selection,
// Roundtable Circle 7-phase lifecycle, TOME aggregation, cleanup, TeamDelete).
// Arc records the team_name for cancel-arc discovery.
// Delegation pattern: /rune:review creates its own team (e.g., rune-review-{identifier}).
// Arc reads the team name from the review state file or teammate idle notification.
// SEC-12 FIX: Use Glob() to resolve wildcard — Read() does not support glob expansion.
const reviewStateFiles = Glob("tmp/.rune-review-*.json")
const reviewTeamName = reviewStateFiles.length > 0
  ? JSON.parse(Read(reviewStateFiles[0])).team_name
  : `rune-review-${Date.now()}`
updateCheckpoint({ phase: "code_review", status: "in_progress", phase_sequence: 6, team_name: reviewTeamName })

// BACK-5 FIX: Pass gap analysis context and review context to /rune:review
// so reviewers can focus on areas where implementation may be incomplete.
// reviewContext was built in STEP 1 from gap-analysis.md.

// STEP 4: TOME relocation
// Move TOME from review's output location to arc's artifact directory
// Source: tmp/reviews/{review-id}/TOME.md (produced by /rune:review)
// Target: tmp/arc/{id}/tome.md (consumed by Phase 7: MEND)
// This makes the TOME available at the canonical arc artifact path.

// STEP 5: Update checkpoint
updateCheckpoint({
  phase: "code_review", status: "completed",
  artifact: `tmp/arc/${id}/tome.md`, artifact_hash: sha256(tome), phase_sequence: 6
})
```

**Output**: `tmp/arc/{id}/tome.md`

**Failure policy**: Review always produces findings or a clean report. Does not halt.

## Gap Analysis Context Propagation

If Phase 5.5 produced a gap analysis with MISSING or PARTIAL criteria, the counts are injected as context for reviewers. This helps reviewers focus on areas where the implementation may be incomplete relative to the plan. The full gap-analysis.md path is provided so reviewers can read details on demand.

## Codex Oracle

Conditional on two checks:
1. `codex` CLI is detected on the system (see `roundtable-circle/references/codex-detection.md`)
2. `"review"` is listed in `talisman.codex.workflows` configuration

When both conditions are met, the Codex Oracle is included as an additional reviewer. Its findings use the `CDX` prefix and participate in the standard dedup hierarchy and TOME aggregation.

## TOME Relocation

`/rune:review` writes the TOME to its own output directory (`tmp/reviews/{review-id}/TOME.md`). The arc orchestrator relocates it to `tmp/arc/{id}/tome.md` so that Phase 7 (MEND) can find it at the canonical arc artifact path. This is a file copy, not a move -- the original remains for debugging.

## Docs-Only Work Output

If Phase 5 produced only documentation files, the review still runs correctly. Rune Gaze's docs-only override ensures Knowledge Keeper is summoned. The TOME will contain `DOC-` and `QUAL-` prefixed findings.
