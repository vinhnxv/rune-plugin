# Monitor Utility — Parameterized Polling for Agent Teams

> Shared polling utility used by all 7 Rune commands (`review`, `audit`, `work`, `mend`, `plan`, `forge`, `arc`). Each command calls `waitForCompletion` with its own configuration instead of inlining a polling loop. ~147 lines of polling logic across 7 commands collapse into a single parameterized reference.

## Table of Contents

- [Function Signature](#function-signature)
- [Pseudocode](#pseudocode)
- [Checkpoint Reporting](#checkpoint-reporting)
- [Per-Command Configuration](#per-command-configuration)
- [Usage Example](#usage-example)
- [Notes](#notes)

## Function Signature

### Contract

| Field | Description |
|-------|-------------|
| **Inputs** | `teamName` (string) — active team name; `expectedCount` (number) — total tasks to monitor; `opts` (object) — per-command configuration (see table below, includes optional `onCheckpoint` callback) |
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
  opts.onCheckpoint         // Milestone callback — OPTIONAL (undefined = no checkpoint reporting)
```

## Pseudocode

```javascript
function waitForCompletion(teamName, expectedCount, opts) {
  const {
    pollIntervalMs = 30_000,
    staleWarnMs = 300_000,
    timeoutMs,                // undefined = skip timeout check
    autoReleaseMs,            // undefined = no auto-release
    label = "Monitor",
    onCheckpoint              // undefined = no checkpoint reporting
  } = opts

  const startTime = Date.now()
  const milestones = [25, 50, 75, 100]
  let lastMilestone = 0       // tracks highest milestone already reported
  let checkpointCount = 0
  const reportedBlockerIds = new Set()  // tracks stale task IDs already reported as blockers
  const taskStartTimes = {}   // taskId -> timestamp when first seen in_progress

  while (true) {
    const tasks = TaskList()
    const completed = tasks.filter(t => t.status === "completed")
    const inProgress = tasks.filter(t => t.status === "in_progress")

    // Derive task.stale: elapsed ms since task entered in_progress
    for (const t of inProgress) {
      if (!taskStartTimes[t.id]) taskStartTimes[t.id] = Date.now()
      t.stale = Date.now() - taskStartTimes[t.id]
    }
    // Clean up completed tasks from tracking maps
    for (const t of completed) {
      delete taskStartTimes[t.id]
      reportedBlockerIds.delete(t.id)
    }

    log(`${label} progress: ${completed.length}/${expectedCount} tasks`)

    // All done
    if (completed.length >= expectedCount) {
      // Fire 100% checkpoint if callback provided and not yet reported
      if (onCheckpoint && lastMilestone < 100) {
        checkpointCount++
        onCheckpoint({
          n: checkpointCount, label, completed: completed.length,
          total: expectedCount, percentage: 100,
          active: [], blockers: [], decision: "COMPLETE"
        })
      }
      return { completed, incomplete: [], timedOut: false }
    }

    // Checkpoint reporting (milestone-based, NOT every poll cycle)
    if (onCheckpoint) {
      const percentage = Math.floor((completed.length / expectedCount) * 100)
      const staleTasks = inProgress.filter(t => t.stale > staleWarnMs)
      const nextMilestone = milestones.find(m => m > lastMilestone && percentage >= m)
      const hasNewBlocker = staleTasks.some(t => !reportedBlockerIds.has(t.id))

      if (nextMilestone || hasNewBlocker) {
        checkpointCount++
        lastMilestone = nextMilestone || lastMilestone
        if (hasNewBlocker) staleTasks.forEach(t => reportedBlockerIds.add(t.id))
        const decision = staleTasks.length > 0 ? "INVESTIGATE" : "CONTINUE"
        onCheckpoint({
          n: checkpointCount,
          label,
          completed: completed.length,
          total: expectedCount,
          percentage,
          active: inProgress.map(t => t.subject),
          blockers: staleTasks.map(t => `#${t.id} ${t.subject} (stale >${Math.floor(t.stale / 60_000)}min)`),
          decision
        })
      }
    }

    // Stale detection
    for (const task of inProgress) {
      if (autoReleaseMs && task.stale > autoReleaseMs) {
        warn(`${label}: task #${task.id} stalled (>${autoReleaseMs / 60_000}min) — auto-releasing`)
        TaskUpdate({ taskId: task.id, owner: "", status: "pending" })
        delete taskStartTimes[task.id]
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

## Checkpoint Reporting

When `onCheckpoint` is provided, `waitForCompletion` emits structured progress reports at significant milestones rather than every poll cycle. This gives the user visibility into long-running workflows without noise.

### Display Triggers

Checkpoints fire when **either** condition is met:
1. **Milestone crossing** — completed percentage crosses 25%, 50%, 75%, or 100%
2. **Blocker detection** — a stalled task (> `staleWarnMs`) is detected after the last milestone

Each milestone fires at most once. The 100% checkpoint fires on completion.

### Checkpoint Template

```markdown
## Checkpoint {N} — {workflow_label}
Progress: {completed}/{total} ({percentage}%)
Active: {in_progress task subjects}
Blockers: {stalled tasks > staleWarnMs, or omit if none}
Decision: {CONTINUE | INVESTIGATE | COMPLETE}
```

### Decision Values

| Decision | Condition | Action |
|----------|-----------|--------|
| `CONTINUE` | No blockers, progress normal | Keep polling |
| `COMPLETE` | All tasks finished successfully | Return final results |
| `INVESTIGATE` | Stalled task detected | Log warning, check if auto-release applies |

### Future Decision Values

The following values are planned but **not yet emitted** by the pseudocode:

| Decision | Condition | Planned Action |
|----------|-----------|----------------|
| `ADJUST` | > 75% complete, minor issues | Consider scope reduction |
| `ESCALATE` | Multiple stalls or repeated blocker | Alert user via `AskUserQuestion` |

### Callback Signature

The `onCheckpoint` callback receives a single object:

```
onCheckpoint({ n, label, completed, total, percentage, active, blockers, decision })
```

| Field | Type | Description |
|-------|------|-------------|
| `n` | number | Checkpoint sequence number (1-indexed) |
| `label` | string | Workflow label (e.g., "Work", "Review") |
| `completed` | number | Count of completed tasks |
| `total` | number | Total expected tasks |
| `percentage` | number | Integer percentage (0-100) |
| `active` | string[] | Subjects of in_progress tasks |
| `blockers` | string[] | Descriptions of stalled tasks (empty if none) |
| `decision` | string | One of: CONTINUE, COMPLETE, INVESTIGATE |

### Cross-References

- [Standing Orders](standing-orders.md) — SO-5 (Ember Overload) may trigger ESCALATE
- [Damage Control](../../rune-orchestration/references/damage-control.md) — DC-3 (Fading Ash) for stalled agent recovery
- [Risk Tiers](risk-tiers.md) — Tier 2+ tasks warrant closer checkpoint attention

## Per-Command Configuration

Each command passes its own `opts` to `waitForCompletion`:

| Command | `timeoutMs` | `staleWarnMs` | `autoReleaseMs` | `pollIntervalMs` | `label` | `onCheckpoint` |
|---------|-------------|---------------|-----------------|-------------------|---------|----------------|
| `review` | 600,000 (10 min) | 300,000 (5 min) | — | 30,000 (30s) | `"Review"` | — |
| `audit` | 900,000 (15 min) | 300,000 (5 min) | — | 30,000 (30s) | `"Audit"` | — |
| `work` | 1,800,000 (30 min) | 300,000 (5 min) | 600,000 (10 min) | 30,000 (30s) | `"Work"` | Yes (milestone) |
| `mend` | 900,000 (15 min) | 300,000 (5 min) | 600,000 (10 min) | 30,000 (30s) | `"Mend"` | — |
| `plan` | — (none) | 300,000 (5 min) | — | 30,000 (30s) | `"Plan Research"` | — |
| `forge` | — (none) | 300,000 (5 min) | 300,000 (5 min)* | 30,000 (30s) | `"Forge"` | — |
| `arc` | Per-phase (varies) | 300,000 (5 min) | — | 30,000 (30s) | `"Arc: {phase}"` | Planned |

**Key differences**:
- `review` and `audit` have no `autoReleaseMs` because each Ash produces unique findings that cannot be reclaimed by another Ash.
- `work` and `mend` enable auto-release because their tasks are fungible (any worker can pick up a released task).
- `forge` enables auto-release (5 min) because enrichment tasks are reassignable. *When `staleWarnMs === autoReleaseMs` (as in forge), warn and release fire on the same poll tick — this is by design since forge's stale detection and release are a single action.
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

// In work.md Phase 3 (with auto-release + optional checkpoint reporting):
const result = waitForCompletion(teamName, taskCount, {
  timeoutMs: 1_800_000,
  staleWarnMs: 300_000,
  autoReleaseMs: 600_000,
  pollIntervalMs: 30_000,
  label: "Work",
  // onCheckpoint is optional — omit to disable milestone reporting
  onCheckpoint: (cp) => {
    log(`## Checkpoint ${cp.n} — ${cp.label}`)
    log(`Progress: ${cp.completed}/${cp.total} (${cp.percentage}%)`)
    log(`Active: ${cp.active.join(", ") || "none"}`)
    if (cp.blockers.length) log(`Blockers: ${cp.blockers.join(", ")}`)
    log(`Decision: ${cp.decision}`)
  }
})
```

## Notes

- **Timeout is optional**: When `timeoutMs` is `undefined`, the loop runs until all tasks complete. This matches `plan` and `forge` which have no hard timeout.
- **Auto-release is optional**: When `autoReleaseMs` is `undefined`, stale tasks only produce warnings. This matches `review` and `audit` where Ash findings are non-fungible.
- **No retry logic**: `TaskList()` errors propagate naturally. Retry logic is out of scope for Phase 1.
- **Final sweep**: On timeout, a final `TaskList()` call captures any tasks that completed during the last poll interval. This matches the existing pattern in `review.md`, `audit.md`, `work.md`, and `mend.md`.
- **Arc per-phase budgets**: Arc does not call `waitForCompletion` directly with a single timeout. Instead, each delegated phase (work, review, mend, audit) uses its own inner timeout. Arc wraps these with a safety-net phase timeout (`PHASE_TIMEOUTS`) plus the global `ARC_TOTAL_TIMEOUT` (90 min) ceiling.
- **Checkpoint reporting is optional**: When `onCheckpoint` is `undefined`, no milestone tracking occurs. Existing callers without `onCheckpoint` get identical behavior. Currently used by `work`. Arc integration is planned but not yet wired.

## Phase 2: Event-Driven Fast Path

> Added in Phase 2 (BRIDGE). When `TaskCompleted` hooks write filesystem signal files, the monitor can detect completion via a 5-second filesystem check instead of a 30-second `TaskList()` API poll — reducing token cost to near-zero per monitoring cycle (~99.8% reduction). The fast path activates automatically when a signal directory exists; otherwise, the Phase 1 polling fallback runs unchanged.

### How It Works

```text
TaskCompleted hook fires
    ↓
scripts/on-task-completed.sh writes signal file to tmp/.rune-signals/{team}/
    ↓
Monitor checks signal files (5s interval, filesystem read — near-zero token cost)
    ↓
All signals present (.all-done sentinel) → proceed
    ↓
(Fallback: if no signal directory exists → Phase 1 TaskList polling at 30s)
```

### Signal Directory Setup (Orchestrator Responsibility)

Before spawning Ashes, the orchestrator (Tarnished) must create the signal directory and expected-count file. If this setup is skipped, the monitor automatically falls back to Phase 1 polling.

```javascript
// Pseudocode — added to each command BEFORE spawning Ashes
const signalDir = `tmp/.rune-signals/${teamName}`

// Clear stale signals from any crashed previous run
Bash(`rm -rf "${signalDir}" && mkdir -p "${signalDir}"`)

// Write expected task count — read by on-task-completed.sh
Write(`${signalDir}/.expected`, String(expectedTaskCount))

// Write inscription — read by on-teammate-idle.sh for quality gates
Write(`${signalDir}/inscription.json`, JSON.stringify({
  workflow: "rune-review",  // or rune-work, rune-plan, etc.
  timestamp: timestamp,
  output_dir: `tmp/reviews/${identifier}/`,
  teammates: [
    { name: "forge-warden", output_file: "forge-warden.md" },
    // ... per command configuration
  ]
}))
```

### Dual-Path Pseudocode

The `waitForCompletion` function from Phase 1 gains a dual-path upgrade. The signal path is chosen when `tmp/.rune-signals/{teamName}/` exists; otherwise the existing polling path runs unchanged.

```javascript
function waitForCompletion(teamName, expectedCount, opts) {
  const {
    pollIntervalMs = 30_000,
    staleWarnMs = 300_000,
    timeoutMs,
    autoReleaseMs,
    label = "Monitor",
    onCheckpoint
  } = opts

  const startTime = Date.now()
  const signalDir = `tmp/.rune-signals/${teamName}`
  const useSignals = exists(signalDir) && exists(`${signalDir}/.expected`)

  if (useSignals) {
    // ═══ FAST PATH: Filesystem signals (5s interval, near-zero token cost) ═══
    // Token cost per check: 0 (filesystem existence check, not API call)
    // Final TaskList() call on completion: ~100 tokens (one-time)
    log(`${label}: Signal directory detected — event-driven monitoring (5s interval)`)
    let iteration = 0

    while (true) {
      iteration++

      // Check .all-done sentinel (written atomically by on-task-completed.sh)
      if (exists(`${signalDir}/.all-done`)) {
        let meta
        try {
          meta = JSON.parse(Read(`${signalDir}/.all-done`))
        } catch (err) {
          warn(`${label}: .all-done file corrupted, falling back to TaskList polling`)
          useSignals = false
          continue
        }
        log(`${label}: All ${meta.total} signals received at ${meta.completed_at}`)
        return { completed: TaskList(), incomplete: [], timedOut: false }
      }

      // Timeout check
      if (timeoutMs !== undefined && Date.now() - startTime > timeoutMs) {
        const doneCount = Glob(`${signalDir}/*.done`).length
        warn(`${label}: Timeout after ${timeoutMs / 60_000} min. ${doneCount}/${expectedCount} signals received.`)
        const finalTasks = TaskList()
        return {
          completed: finalTasks.filter(t => t.status === "completed"),
          incomplete: finalTasks.filter(t => t.status !== "completed"),
          timedOut: true
        }
      }

      // Progress logging every 3rd check (~15s), plus first iteration
      if (iteration === 1 || iteration % 3 === 0) {
        const doneCount = Glob(`${signalDir}/*.done`).length
        log(`${label}: Progress: ${doneCount}/${expectedCount} tasks signaled`)
      }

      sleep(5_000)  // 5s — filesystem check, not API call
    }

  } else {
    // ═══ FALLBACK: Phase 1 polling (30s interval, TaskList API calls) ═══
    log(`${label}: No signal directory — falling back to TaskList polling (${pollIntervalMs / 1000}s interval)`)
    // ... (existing Phase 1 pseudocode from above runs unchanged) ...
  }
}
```

### Security Considerations (Phase 2)

When implementing the signal-based fast path:
1. **Path validation**: Canonicalize CWD via `realpath` before constructing signal paths
2. **Atomic writes**: Use `mv -n` (noclobber) to prevent symlink attacks
3. **Input sanitization**: Validate team name matches `^[a-zA-Z0-9_-]+$`

See `scripts/on-task-completed.sh` for reference implementation.

### Performance Characteristics

| Metric | Phase 1 (Polling) | Phase 2 (Signals) |
|--------|-------------------|-------------------|
| Check interval | 30s | 5s |
| Token cost per check | ~500 (TaskList API) | 0 (filesystem read) |
| Average detection latency | ~15s | ~2.5s |
| Final TaskList call | Every check | Once on completion (~100 tokens) |
| Scales with agent count | O(N) per check | O(1) per check (single `.all-done` existence check) |

### Signal Cleanup

Signal directories are cleaned:
1. **Per-workflow:** In Phase 7 (Cleanup), after `TeamDelete`:
   ```bash
   rm -rf "tmp/.rune-signals/${teamName}"
   ```
2. **Global:** Via `/rune:rest`:
   ```bash
   rm -rf tmp/.rune-signals/ 2>/dev/null
   ```

### Concurrency Notes

- **Atomic writes**: Hook script uses `tmp + mv` pattern — monitor never sees incomplete signal files
- **TOCTOU in `.all-done`**: SAFE — sentinel is written atomically by the hook, not computed by the monitor
- **Concurrent hook invocations**: SAFE — each writes to a unique `{task_id}.done` file (no shared state)
- **Multiple concurrent workflows**: SAFE — team-name-scoped signal directories prevent cross-workflow interference

### Stability Trigger

Phase 2 is activated when `TaskCompleted` and `TeammateIdle` hooks are proven stable across 3+ consecutive plugin releases with zero hook-related regressions.

## References

- [Inscription Schema](inscription-schema.md) — Output contract for monitored tasks
- [Task Templates](task-templates.md) — Task creation patterns used before monitoring
