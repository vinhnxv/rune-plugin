# Phase 5: WORK — Full Algorithm

Invoke `/rune:work` logic on the enriched plan. Swarm workers implement tasks with incremental commits.

**Team**: `arc-work-{id}` (delegated to `/rune:work` -- manages its own TeamCreate/TeamDelete with guards)
**Tools**: Full access (Read, Write, Edit, Bash, Glob, Grep)
**Duration**: Max 35 minutes (inner 30m + 5m setup)
**Inputs**: id (string), enriched plan path (`tmp/arc/{id}/enriched-plan.md`), concern context (optional: `tmp/arc/{id}/concern-context.md`), verification report (optional: `tmp/arc/{id}/verification-report.md`), `--approve` flag
**Outputs**: `tmp/arc/{id}/work-summary.md` + committed code on feature branch
**Error handling**: Halt if <50% tasks complete. Partial work is committed via incremental commits (E5).
**Consumers**: arc.md (Phase 5 stub)

## Algorithm

```javascript
// STEP 1: Feature branch creation (if on main)
createFeatureBranchIfNeeded()

// STEP 2: Build context for workers
let workContext = ""

// Include reviewer concerns if any
if (exists(`tmp/arc/${id}/concern-context.md`)) {
  workContext += `\n\n## Reviewer Concerns\nSee tmp/arc/${id}/concern-context.md for full details.`
}

// Include verification warnings if any
if (exists(`tmp/arc/${id}/verification-report.md`)) {
  const verReport = Read(`tmp/arc/${id}/verification-report.md`)
  const issueCount = (verReport.match(/^- /gm) || []).length
  if (issueCount > 0) {
    workContext += `\n\n## Verification Warnings (${issueCount} issues)\nSee tmp/arc/${id}/verification-report.md.`
  }
}

// Quality contract for all workers
workContext += `\n\n## Quality Contract\nAll code must include:\n- Type annotations on all function signatures\n- Docstrings on all public functions, classes, and modules\n- Error handling with specific exception types (no bare except)\n- Test coverage target: >=80% for new code`

// STEP 3: Delegate to /rune:work
// /rune:work manages its own team lifecycle (TeamCreate, TaskCreate, worker spawning,
// monitoring, commit brokering, ward check, cleanup, TeamDelete).
// Arc records the team_name for cancel-arc discovery.
const workTeamName = /* team name created by /rune:work logic */
updateCheckpoint({ phase: "work", status: "in_progress", phase_sequence: 5, team_name: workTeamName })

// STEP 4: After work completes, produce work summary
Write(`tmp/arc/${id}/work-summary.md`, {
  tasks_completed: completedCount, tasks_failed: failedCount,
  files_committed: committedFiles, uncommitted_changes: uncommittedList, commits: commitSHAs
})

// STEP 5: Update checkpoint
updateCheckpoint({
  phase: "work", status: completedRatio >= 0.5 ? "completed" : "failed",
  artifact: `tmp/arc/${id}/work-summary.md`, artifact_hash: sha256(workSummary),
  phase_sequence: 5, commits: commitSHAs
})
```

**Output**: Implemented code (committed) + `tmp/arc/{id}/work-summary.md`

**Failure policy**: Halt if <50% tasks complete. Partial work is committed via incremental commits (E5).

## --approve Routing

The `--approve` flag routes to the **human user** via `AskUserQuestion` (not to the AI leader). This applies only to Phase 5. Do NOT propagate `--approve` when invoking `/rune:mend` in Phase 7 -- mend fixers apply deterministic fixes from TOME findings.

## Team Name Recording

Arc MUST record the actual `team_name` created by `/rune:work` in the checkpoint. This enables `/rune:cancel-arc` to discover and shut down the work team if the user cancels mid-pipeline. The work command creates its own team with its own naming convention -- arc reads the team name back after delegation.

## Feature Branch Strategy

Before delegating to `/rune:work`, the arc orchestrator ensures a feature branch exists (see arc.md Pre-flight: Branch Strategy COMMIT-1). If already on a feature branch, the current branch is used. `/rune:work`'s own Phase 0.5 (env setup) skips branch creation when invoked from arc context.
