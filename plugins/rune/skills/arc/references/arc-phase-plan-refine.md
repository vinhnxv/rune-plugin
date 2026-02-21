# Phase 2.5: PLAN REFINEMENT — Full Algorithm

Extract CONCERN details from reviewer outputs and propagate as context to the work phase. Orchestrator-only --- no team creation, no agents.

**Team**: None (orchestrator-only)
**Tools**: Read, Write, Glob, Grep
**Timeout**: 3 min (PHASE_TIMEOUTS.plan_refine = 180_000 — orchestrator-only, no team)
**Trigger**: Any CONCERN verdict exists. If all PASS, skip.
**Inputs**: id (string), reviewer verdict paths (`tmp/arc/{id}/reviews/{name}-verdict.md`), checkpoint object
**Outputs**: `tmp/arc/{id}/concern-context.md` (or skipped if no CONCERNs)
**Error handling**: Non-blocking -- proceed with unrefined plan + deferred concerns as context
**Consumers**: SKILL.md (Phase 2.5 stub)

> **Note**: `sha256()`, `updateCheckpoint()`, `exists()`, and `warn()` are dispatcher-provided utilities available in the arc orchestrator context. Phase reference files call these without import.

## Algorithm

```javascript
updateCheckpoint({ phase: "plan_refine", status: "in_progress", phase_sequence: 3, team_name: null })

// Canonical reviewers — hardcoded for self-containment (matches Phase 2 plan review)
const reviewers = [
  { name: "scroll-reviewer", focus: "Document quality" },
  { name: "decree-arbiter", focus: "Technical soundness" },
  { name: "knowledge-keeper", focus: "Documentation coverage" }
]

// parseVerdict — duplicated from arc-phase-plan-review.md for self-containment.
// This phase is orchestrator-only (no team) and may be invoked as a standalone reference.
// Duplication is intentional to avoid cross-file dependency. Must stay in sync with Phase 2.
const parseVerdict = (reviewer, output) => {
  const pattern = /^<!-- VERDICT:([a-zA-Z_-]+):(PASS|CONCERN|BLOCK) -->$/m
  const match = output.match(pattern)
  if (!match) { warn(`Reviewer ${reviewer} output lacks verdict marker — defaulting to CONCERN.`); return "CONCERN" }
  if (match[1] !== reviewer) warn(`Verdict marker reviewer mismatch: expected ${reviewer}, found ${match[1]}.`)
  return match[2]
}

// STEP 1: Extract concerns from reviewer outputs
const concerns = []
for (const reviewer of reviewers) {
  const outputPath = `tmp/arc/${id}/reviews/${reviewer.name}-verdict.md`
  if (!exists(outputPath)) continue
  const output = Read(outputPath)
  const verdict = parseVerdict(reviewer.name, output)
  if (verdict === "CONCERN") {
    // SEC-8 FIX: Slice before regex to bound input size (ReDoS mitigation)
    // BACK-7 FIX: Also sanitize inline code (single backtick)
    const sanitized = output
      .slice(0, 5000)
      .replace(/<!--[\s\S]*?-->/g, '')
      .replace(/```[\s\S]*?```/g, '[code block removed]')
      .replace(/`[^`]+`/g, '[code removed]')
      .slice(0, 2000)
    concerns.push({ reviewer: reviewer.name, verdict: "CONCERN", content: sanitized })
  }
}

// STEP 2: Skip if no concerns
if (concerns.length === 0) {
  updateCheckpoint({ phase: "plan_refine", status: "skipped", phase_sequence: 3, team_name: null })
  // Proceed directly to Phase 2.7 (VERIFICATION GATE)
  return
}

// STEP 3: Generate concern-context.md
// Phase 2.5 is extraction-only. It does NOT modify the plan.
const concernContext = concerns.map(c => `## ${c.reviewer} — CONCERN\n\n${c.content}`).join('\n\n---\n\n')
Write(`tmp/arc/${id}/concern-context.md`, `# Plan Review Concerns\n\n` +
  `Total concerns: ${concerns.length}\n` +
  `Reviewers with concerns: ${concerns.map(c => c.reviewer).join(', ')}\n\n` +
  `Workers should address these concerns during implementation.\n\n` + concernContext)

// STEP 4: All-CONCERN escalation (3x CONCERN, 0 PASS)
// BACK-8 FIX: Reuse already-parsed data from STEP 1 instead of re-reading verdict files.
// This eliminates redundant I/O and TOCTOU risk from reading files twice.
const reviewersWithVerdictFiles = reviewers.filter(r => exists(`tmp/arc/${id}/reviews/${r.name}-verdict.md`))
const allConcern = reviewersWithVerdictFiles.length > 0 && concerns.length === reviewersWithVerdictFiles.length
if (allConcern) {
  const forgeNote = checkpoint.flags.no_forge
    ? "\n\nNote: Forge enrichment was skipped (--no-forge). CONCERNs may be more likely on a raw plan."
    : ""

  // BACK-002 FIX: --confirm flag gates escalation behavior
  // Default (no --confirm): auto-proceed with warnings
  // With --confirm: pause for user input
  if (!checkpoint.flags.confirm) {
    warn(`All ${reviewersWithVerdictFiles.length} reviewers raised CONCERN — auto-proceeding (use --confirm to pause)`)
    // Fall through to implementation with concern context already written at STEP 3
  } else {
  const escalationResponse = AskUserQuestion({
    question: `All ${reviewersWithVerdictFiles.length} reviewers raised concerns (no PASS verdicts).${forgeNote} Proceed to implementation?`,
    header: "Escalate",
    options: [
      { label: "Proceed with warnings", description: "Implementation will include concern context" },
      { label: "Halt and fix manually", description: "Fix plan, then /rune:arc --resume" },
      { label: "Re-run plan review", description: "Revert to Phase 2 with updated plan" }
    ]
  })

  // CDX-015 MITIGATION (P3): Handle all-CONCERN escalation response branches
  // SEC-2 FIX: Null-guard AskUserQuestion return value
  if (!escalationResponse) {
    updateCheckpoint({ phase: "plan_refine", status: "failed", phase_sequence: 3, team_name: null })
    error("Arc halted — escalation dialog returned null. Fix plan, then /rune:arc --resume")
    return
  }
  if (escalationResponse.includes("Halt")) {
    updateCheckpoint({ phase: "plan_refine", status: "failed", phase_sequence: 3, team_name: null })
    error("Arc halted by user at all-CONCERN escalation. Fix plan, then /rune:arc --resume")
    return
  } else if (escalationResponse.includes("Re-run")) {
    // CROSS-PHASE CHECKPOINT DEMOTION: Resets plan_review to "pending"
    // This is the only phase that can mutate another phase's checkpoint state.
    // On --resume, the dispatcher will re-run Phase 2 (PLAN REVIEW) from scratch.
    updateCheckpoint({
      phase: "plan_review", status: "pending", phase_sequence: 2,
      artifact: null, artifact_hash: null
    })
    updateCheckpoint({ phase: "plan_refine", status: "pending", phase_sequence: 3, team_name: null })
    error("Arc reverted to Phase 2 (PLAN REVIEW). Run /rune:arc --resume to re-review.")
    return
  }
  // "Proceed with warnings" — fall through to normal completion below
  } // end else (--confirm flag set)
}

// STEP 5: Verify written content and update checkpoint
const writtenContent = Read(`tmp/arc/${id}/concern-context.md`)
updateCheckpoint({
  phase: "plan_refine", status: "completed",
  artifact: `tmp/arc/${id}/concern-context.md`, artifact_hash: sha256(writtenContent),
  phase_sequence: 3, team_name: null
})
```

**Output**: `tmp/arc/{id}/concern-context.md` (or skipped if no CONCERNs)

**Failure policy**: Non-blocking -- proceed with unrefined plan + deferred concerns as context.

## Cross-Phase Mutation

This phase can **demote `plan_review` checkpoint to "pending"** when the user selects "Re-run plan review" during all-CONCERN escalation. This is the only phase in the arc pipeline that mutates another phase's checkpoint state. The dispatcher's `--resume` logic will detect `plan_review.status === "pending"` and re-run Phase 2 from scratch.
