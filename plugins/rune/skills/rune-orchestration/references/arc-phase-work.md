# Phase 5: WORK — Full Algorithm

Invoke `/rune:work` logic on the enriched plan. Swarm workers implement tasks with incremental commits.

**Team**: `arc-work-{id}` (delegated to `/rune:work` --- manages its own TeamCreate/TeamDelete with guards)
**Tools**: Full access (Read, Write, Edit, Bash, Glob, Grep)
**Timeout**: 35 min (PHASE_TIMEOUTS.work = 2_100_000 — inner 30m + 5m setup)
**Inputs**: id (string), enriched plan path (`tmp/arc/{id}/enriched-plan.md`), concern context (optional: `tmp/arc/{id}/concern-context.md`), verification report (optional: `tmp/arc/{id}/verification-report.md`), `--approve` flag
**Outputs**: `tmp/arc/{id}/work-summary.md` + committed code on feature branch
**Error handling**: Halt if <50% tasks complete. Partial work is committed via incremental commits (E5).
**Consumers**: arc.md (Phase 5 stub)

> **Note**: `sha256()`, `updateCheckpoint()`, `exists()`, and `warn()` are dispatcher-provided utilities available in the arc orchestrator context. Phase reference files call these without import.

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
// Delegation pattern: /rune:work creates its own team (e.g., rune-work-{timestamp}).
// Arc reads the team name back from the work state file or teammate idle notification.
// The team name is recorded in checkpoint for cancel-arc discovery.
// SEC-12 FIX: Use Glob() to resolve wildcard — Read() does not support glob expansion.
// CDX-2 NOTE: Glob matches ALL work state files, not just the current arc session's.
// Glob returns files sorted by mtime (most recent first), so [0] picks the latest.
// If multiple state files exist from prior runs, warn but proceed with most recent.
const workStateFiles = Glob("tmp/.rune-work-*.json")
if (workStateFiles.length > 1) warn(`Multiple work state files found (${workStateFiles.length}) — using most recent`)
const workTeamName = workStateFiles.length > 0
  ? JSON.parse(Read(workStateFiles[0])).team_name
  : `rune-work-${Date.now()}`
// SEC-2 FIX: Validate team_name from state file before storing in checkpoint (TOCTOU defense)
if (!/^[a-zA-Z0-9_-]+$/.test(workTeamName)) throw new Error(`Invalid team_name from state file: ${workTeamName}`)
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

## Team Lifecycle

Delegated to `/rune:work` — manages its own TeamCreate/TeamDelete with guards (see [team-lifecycle-guard.md](team-lifecycle-guard.md)). Arc records the actual `team_name` in checkpoint for cancel-arc discovery.

Arc MUST record the actual `team_name` created by `/rune:work` in the checkpoint. This enables `/rune:cancel-arc` to discover and shut down the work team if the user cancels mid-pipeline. The work command creates its own team with its own naming convention — arc reads the team name back after delegation.

Arc runs `prePhaseCleanup(checkpoint)` before delegation (ARC-6). See arc.md Inter-Phase Cleanup Guard section.

## Feature Branch Strategy

Before delegating to `/rune:work`, the arc orchestrator ensures a feature branch exists (see arc.md Pre-flight: Branch Strategy COMMIT-1). If already on a feature branch, the current branch is used. `/rune:work`'s own Phase 0.5 (env setup) skips branch creation when invoked from arc context.
