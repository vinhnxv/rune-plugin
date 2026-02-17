# Phase 6: CODE REVIEW — Full Algorithm

Invoke `/rune:review` logic on the implemented changes. Summons Ash with Roundtable Circle lifecycle.

**Team**: `arc-review-{id}` (delegated to `/rune:review` — manages its own TeamCreate/TeamDelete with guards)
**Tools**: Read, Glob, Grep, Write (own output file only)
**Timeout**: 15 min (PHASE_TIMEOUTS.code_review = 900_000 — inner 10m + 5m setup)
**Inputs**: id (string), gap analysis path (optional: `tmp/arc/{id}/gap-analysis.md`)
**Outputs**: `tmp/arc/{id}/tome.md`
**Error handling**: Does not halt — review always produces findings or a clean report. Timeout → partial results collected. Team creation failure → cleanup fallback via `rm -rf` (see [team-lifecycle-guard.md](team-lifecycle-guard.md)).
**Consumers**: SKILL.md (Phase 6 stub)

> **Note**: `sha256()`, `updateCheckpoint()`, `exists()`, and `warn()` are dispatcher-provided utilities available in the arc orchestrator context. Phase reference files call these without import.

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
// SEC-001 FIX: Filter to current session timeframe to prevent cross-session confusion
const reviewStateFiles = Glob("tmp/.rune-review-*.json").filter(f => {
  try {
    const state = JSON.parse(Read(f))
    const age = Date.now() - new Date(state.started).getTime()
    return state.status === "active" && !Number.isNaN(age) && age < PHASE_TIMEOUTS.code_review
  } catch (e) { return false }
})
if (reviewStateFiles.length > 1) warn(`Multiple active review state files found (${reviewStateFiles.length}) — using most recent`)
const reviewTeamName = reviewStateFiles.length > 0
  ? JSON.parse(Read(reviewStateFiles[0])).team_name
  : `rune-review-${Date.now()}`
// SEC-2 FIX: Validate team_name from state file before storing in checkpoint (TOCTOU defense)
if (!/^[a-zA-Z0-9_-]+$/.test(reviewTeamName)) throw new Error(`Invalid team_name from state file: ${reviewTeamName}`)
updateCheckpoint({ phase: "code_review", status: "in_progress", phase_sequence: 6, team_name: reviewTeamName })

// BACK-5 FIX: Pass gap analysis context and review context to /rune:review
// so reviewers can focus on areas where implementation may be incomplete.
// reviewContext was built in STEP 1 from gap-analysis.md.

// STEP 4: TOME relocation (copy, not move — original remains for debugging)
// Source: tmp/reviews/{review-id}/TOME.md (produced by /rune:review)
// Target: tmp/arc/{id}/tome.md (consumed by Phase 7: MEND)
const reviewId = reviewTeamName.replace('rune-review-', '')
Bash(`cp -- "tmp/reviews/${reviewId}/TOME.md" "tmp/arc/${id}/tome.md"`)

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

## Delegation Steps (Phase 6 → review.md Phase 0)

<!-- See arc-delegation-checklist.md Phase 6 for the canonical contract -->

When arc invokes `/rune:review` logic, the delegated command MUST execute these Phase 0 steps
from review.md. Step ordering matters — scope building depends on default branch detection.

| # | review.md Phase 0 Step | Action | Notes |
|---|----------------------|--------|-------|
| 1 | Default branch detection | **RUN** | Review needs this to compute `git diff` base |
| 2 | Changed files scope building | **RUN** | Review needs file inventory for Ash assignment. Depends on step 1 |
| 3 | Abort conditions check | **RUN** | Graceful no-op if no reviewable changes |
| 4 | Custom Ash loading | **RUN** | `ashes.custom[]` filtered by `workflows: [review]` (no-op if none configured) |
| 5 | Codex Oracle detection | **RUN** | Per `codex-detection.md`, if `review` in `talisman.codex.workflows` |

**Steps SKIPPED** (arc handles or not applicable):
- Branch detection: arc already has the branch from pre-flight (COMMIT-1)
- Scope summary display: arc is automated — no user display needed
- Dry-run mode / `--partial` flag: arc always reviews full scope

## Codex Oracle

Conditional on two checks:
1. `codex` CLI is detected on the system (see `roundtable-circle/references/codex-detection.md`)
2. `"review"` is listed in `talisman.codex.workflows` configuration

When both conditions are met, the Codex Oracle is included as an additional reviewer. Its findings use the `CDX` prefix and participate in the standard dedup hierarchy and TOME aggregation.

## TOME Relocation

`/rune:review` writes the TOME to its own output directory (`tmp/reviews/{review-id}/TOME.md`). The arc orchestrator relocates it to `tmp/arc/{id}/tome.md` so that Phase 7 (MEND) can find it at the canonical arc artifact path. This is a file copy, not a move -- the original remains for debugging.

## Team Lifecycle

Delegated to `/rune:review` — manages its own TeamCreate/TeamDelete with guards (see [team-lifecycle-guard.md](team-lifecycle-guard.md)). Arc records the actual `team_name` in checkpoint for cancel-arc discovery.

Arc runs `prePhaseCleanup(checkpoint)` before delegation (ARC-6). See SKILL.md Inter-Phase Cleanup Guard section.

## Docs-Only Work Output

If Phase 5 produced only documentation files, the review still runs correctly. Rune Gaze's docs-only override ensures Knowledge Keeper is summoned. The TOME will contain `DOC-` and `QUAL-` prefixed findings.

## Crash Recovery

If this phase crashes before reaching cleanup, the following resources are orphaned:

| Resource | Location |
|----------|----------|
| Team config | `~/.claude/teams/rune-review-{identifier}/` |
| Task list | `~/.claude/tasks/rune-review-{identifier}/` |
| State file | `tmp/.rune-review-*.json` (stuck in `"active"` status) |
| Signal dir | `tmp/.rune-signals/rune-review-{identifier}/` |

### Recovery Layers

If this phase crashes, the orphaned resources above are recovered by the 3-layer defense:
Layer 1 (ORCH-1 resume), Layer 2 (`/rune:rest --heal`), Layer 3 (arc pre-flight stale scan).
Review phase teams use `rune-review-*` prefix — handled by the sub-command's own pre-create guard (not Layer 3).

See [team-lifecycle-guard.md](team-lifecycle-guard.md) §Orphan Recovery Pattern for full layer descriptions and coverage matrix.
