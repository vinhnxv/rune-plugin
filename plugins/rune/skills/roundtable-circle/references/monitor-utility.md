# Monitor Utility — Parameterized Polling for Agent Teams

> Shared polling utility used by all 7 Rune commands (`review`, `audit`, `work`, `mend`, `plan`, `forge`, `arc`). Each command calls `waitForCompletion` with its own configuration instead of inlining a polling loop. ~147 lines of polling logic across 7 commands collapse into a single parameterized reference.

## Table of Contents

- [Function Signature](#function-signature)
- [Pseudocode](#pseudocode)
- [Per-Command Configuration](#per-command-configuration)
- [Usage Example](#usage-example)
- [Notes](#notes)

## Function Signature

### Contract

| Field | Description |
|-------|-------------|
| **Inputs** | `teamName` (string) — active team name; `expectedCount` (number) — total tasks to monitor; `opts` (object) — per-command configuration (see table below) |
| **Outputs** | `{ completed: Task[], incomplete: Task[], timedOut: boolean }` |
| **Preconditions** | Team exists (`TeamCreate` already called), tasks already created via `TaskCreate` |
| **Error handling** | `TaskList()` errors propagate naturally (no retry in Phase 1). Timeout produces partial results, never throws. |

```
waitForCompletion(teamName, expectedCount, opts):
  opts.pollIntervalMs       // Polling interval (default: 30_000)
  opts.staleWarnMs          // Warn threshold for in_progress tasks (default: 300_000)
  opts.timeoutMs            // Total timeout — OPTIONAL (undefined = no timeout)
  opts.autoReleaseMs        // Auto-release stale tasks — OPTIONAL (undefined = no auto-release)
  opts.label                // Display label for log messages (e.g., "Review", "Work")
```

## Pseudocode

```javascript
function waitForCompletion(teamName, expectedCount, opts) {
  const {
    pollIntervalMs = 30_000,
    staleWarnMs = 300_000,
    timeoutMs,                // undefined = skip timeout check
    autoReleaseMs,            // undefined = no auto-release
    label = "Monitor"
  } = opts

  const startTime = Date.now()

  while (true) {
    const tasks = TaskList()
    const completed = tasks.filter(t => t.status === "completed")
    const inProgress = tasks.filter(t => t.status === "in_progress")

    log(`${label} progress: ${completed.length}/${expectedCount} tasks`)

    // All done
    if (completed.length >= expectedCount) {
      return { completed, incomplete: [], timedOut: false }
    }

    // Stale detection
    for (const task of inProgress) {
      if (autoReleaseMs && task.stale > autoReleaseMs) {
        warn(`${label}: task #${task.id} stalled (>${autoReleaseMs / 60_000}min) — auto-releasing`)
        TaskUpdate({ taskId: task.id, owner: "", status: "pending" })
      } else if (task.stale > staleWarnMs) {
        warn(`${label}: task #${task.id} may be stalled (>${staleWarnMs / 60_000}min)`)
      }
    }

    // Timeout check (only if timeoutMs is defined)
    if (timeoutMs !== undefined && Date.now() - startTime > timeoutMs) {
      warn(`${label} timeout reached (${timeoutMs / 60_000} min). Collecting partial results.`)
      // Final sweep
      const finalTasks = TaskList()
      return {
        completed: finalTasks.filter(t => t.status === "completed"),
        incomplete: finalTasks.filter(t => t.status !== "completed"),
        timedOut: true
      }
    }

    sleep(pollIntervalMs)
  }
}
```

## Per-Command Configuration

Each command passes its own `opts` to `waitForCompletion`:

| Command | `timeoutMs` | `staleWarnMs` | `autoReleaseMs` | `pollIntervalMs` | `label` |
|---------|-------------|---------------|-----------------|-------------------|---------|
| `review` | 600,000 (10 min) | 300,000 (5 min) | — | 30,000 (30s) | `"Review"` |
| `audit` | 900,000 (15 min) | 300,000 (5 min) | — | 30,000 (30s) | `"Audit"` |
| `work` | 1,800,000 (30 min) | 300,000 (5 min) | 600,000 (10 min) | 30,000 (30s) | `"Work"` |
| `mend` | 900,000 (15 min) | 300,000 (5 min) | 600,000 (10 min) | 30,000 (30s) | `"Mend"` |
| `plan` | — (none) | 300,000 (5 min) | — | 30,000 (30s) | `"Plan Research"` |
| `forge` | — (none) | 300,000 (5 min) | 300,000 (5 min) | 30,000 (30s) | `"Forge"` |
| `arc` | Per-phase (varies) | 300,000 (5 min) | — | 30,000 (30s) | `"Arc: {phase}"` |

**Key differences**:
- `review` and `audit` have no `autoReleaseMs` because each Ash produces unique findings that cannot be reclaimed by another Ash.
- `work` and `mend` enable auto-release because their tasks are fungible (any worker can pick up a released task).
- `forge` enables auto-release (5 min) because enrichment tasks are reassignable.
- `plan` and `forge` have no `timeoutMs` — polling continues until all tasks complete or stale detection intervenes.
- `arc` uses `PHASE_TIMEOUTS` from its constants (see `arc.md`) which vary per phase.

## Usage Example

```javascript
// In review.md Phase 4:
const result = waitForCompletion(teamName, ashCount, {
  timeoutMs: 600_000,
  staleWarnMs: 300_000,
  pollIntervalMs: 30_000,
  label: "Review"
})

if (result.timedOut) {
  log(`Review completed with partial results: ${result.completed.length}/${ashCount} Ashes`)
}

// In plan.md Monitor Research (no timeout):
const result = waitForCompletion(teamName, researchTaskCount, {
  staleWarnMs: 300_000,
  pollIntervalMs: 30_000,
  label: "Plan Research"
})

// In work.md Phase 3 (with auto-release):
const result = waitForCompletion(teamName, taskCount, {
  timeoutMs: 1_800_000,
  staleWarnMs: 300_000,
  autoReleaseMs: 600_000,
  pollIntervalMs: 30_000,
  label: "Work"
})
```

## Notes

- **Timeout is optional**: When `timeoutMs` is `undefined`, the loop runs until all tasks complete. This matches `plan` and `forge` which have no hard timeout.
- **Auto-release is optional**: When `autoReleaseMs` is `undefined`, stale tasks only produce warnings. This matches `review` and `audit` where Ash findings are non-fungible.
- **No retry logic**: `TaskList()` errors propagate naturally. Retry logic is out of scope for Phase 1.
- **Final sweep**: On timeout, a final `TaskList()` call captures any tasks that completed during the last poll interval. This matches the existing pattern in `review.md`, `audit.md`, `work.md`, and `mend.md`.
- **Arc per-phase budgets**: Arc does not call `waitForCompletion` directly with a single timeout. Instead, each delegated phase (work, review, mend, audit) uses its own inner timeout. Arc wraps these with a safety-net phase timeout (`PHASE_TIMEOUTS`) plus the global `ARC_TOTAL_TIMEOUT` (90 min) ceiling.

## References

- [Inscription Schema](inscription-schema.md) — Output contract for monitored tasks
- [Task Templates](task-templates.md) — Task creation patterns used before monitoring
