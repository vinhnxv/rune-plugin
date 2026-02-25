# Background Dispatch — Non-Blocking Strive Mode (Phase 3)

Non-blocking dispatch mode for `/rune:strive`. Workers run in the background after the
orchestrator exits its current turn. Progress is checked via `/rune:status` between sessions.

**SDK constraint (REAL-005)**: Background workers cannot block the main session turn.
This mode follows the arc-batch Stop hook pattern — the orchestrator sets up the dispatch
state, returns, and a Stop hook fires to launch workers when Claude finishes responding.
This is NOT a persistent background orchestrator; it is a one-shot wave dispatch.

## Invocation

```
/rune:strive --background [plan.md]
/rune:strive -bg [plan.md]
```

To check progress after dispatch:
```
/rune:status [timestamp]
```

To gather results once complete:
```
/rune:strive --collect [timestamp]
```

---

## Dispatch State File Schema

Written to `tmp/.rune-dispatch-{timestamp}.json` before the orchestrator exits.

```json
{
  "timestamp": "20260226-014500",
  "plan_path": "plans/feature-plan.md",
  "team_name": "rune-work-20260226-014500",
  "started_at": "2026-02-26T01:45:00Z",
  "status": "dispatched",

  // Session isolation triple (SEC-004)
  "config_dir": "/Users/alice/.claude",
  "owner_pid": "12345",
  "session_id": "${CLAUDE_SESSION_ID}",

  // Worker inventory
  "worker_count": 2,
  "expected_task_count": 8,

  // Signal directory for progress (PERF-002)
  "signal_dir": "tmp/.rune-signals/rune-work-20260226-014500/",

  // Question relay directory
  "question_dir": "tmp/work/20260226-014500/questions/",

  // Lock file path (PERF-005)
  "lock_path": "tmp/.rune-dispatch-20260226-014500.lock"
}
```

**State file location**: `tmp/.rune-dispatch-{timestamp}.json` (gitignored, session-scoped).

---

## Dispatch Lock File Enforcement (PERF-005)

Only one active background dispatch per session is allowed. Before writing the dispatch
state file, the orchestrator checks for an existing lock:

```javascript
// PERF-005: Single active dispatch per session
const lockFiles = Glob("tmp/.rune-dispatch-*.lock")
const activeLocks = lockFiles.filter(f => {
  try {
    const lock = JSON.parse(Read(f))
    return lock.owner_pid === Bash("echo $PPID").trim() && lock.status === "active"
  } catch { return false }
})

if (activeLocks.length > 0) {
  const existingTimestamp = activeLocks[0].match(/\.rune-dispatch-(.+)\.lock/)?.[1]
  error(`A background dispatch is already active for this session (${existingTimestamp}).`)
  error(`Check status: /rune:status ${existingTimestamp}`)
  error(`Or collect results: /rune:strive --collect ${existingTimestamp}`)
  return
}

// Write lock file (SEC-005: owner-only permissions)
Bash(`mkdir -m 700 -p tmp/ && touch tmp/.rune-dispatch-${timestamp}.lock`)
Write(`tmp/.rune-dispatch-${timestamp}.lock`, JSON.stringify({
  timestamp,
  owner_pid: Bash("echo $PPID").trim(),
  session_id: "${CLAUDE_SESSION_ID}",
  status: "active",
  created_at: new Date().toISOString()
}))
```

Lock file is removed when `--collect` gathers results or when the dispatch is explicitly cancelled.

---

## Signal Directory for Progress (PERF-002)

Workers write `.done` signal files when tasks complete, making progress visible without
requiring TaskList API calls on every poll:

```
tmp/.rune-signals/{team_name}/{task-id}.done
```

The `/rune:status` skill reads the signal directory first and only calls `TaskList` when
the signal count differs from the expected task count. This reduces API overhead for
long-running dispatches (PERF-002).

Signal directory created with restricted permissions (SEC-005):

```bash
mkdir -m 700 -p "tmp/.rune-signals/${team_name}/"
```

---

## Question Cap (SEC-006)

Background workers cannot use `AskUserQuestion` — there is no user session to respond.
Workers write questions to files instead:

```
tmp/work/{timestamp}/questions/{task-id}.question   # worker writes question
tmp/work/{timestamp}/questions/{task-id}.answer     # orchestrator or user writes answer
```

**SEC-006**: Workers may ask at most 3 questions per task. After 3 unanswered questions,
the worker auto-resolves using its best judgment and logs the decision in its worker log.
This prevents unbounded blocking in background mode.

---

## --collect Flag

Gather background dispatch results after workers complete:

```
/rune:strive --collect [timestamp]
```

The collect phase:
1. Reads `tmp/.rune-dispatch-{timestamp}.json` state file
2. Runs ward check across all modified files
3. Runs commit broker to commit accepted patches
4. Generates worker log summary at `tmp/work/{timestamp}/worker-logs/_summary.md`
5. Removes lock file and marks dispatch state as `completed`

---

## SDK Constraints Acknowledgment (REAL-005)

Background mode does NOT implement a persistent background orchestrator. The design models
after the arc-batch Stop hook pattern (Forge Revision 3):

1. Orchestrator parses plan, creates tasks, and writes dispatch state file
2. Orchestrator exits its turn (returns to user)
3. Stop hook fires: reads dispatch state, writes arc-batch-style loop file
4. Next Claude turn: loop file detected → workers spawned as teammates
5. Workers run in-process (tmux or in-process teammate mode)

This means workers are launched in the NEXT Claude session turn, not truly in the background.
The term "background" refers to the user's perspective — they can start other tasks while
the dispatch runs.

**What this is NOT**:
- Not a daemon process running while Claude is idle
- Not truly async (workers block the Claude session they run in)
- Not multi-session (workers share the session that drives the next turn)

---

## Talisman Configuration

Configure background dispatch under `dispatch:` in `.claude/talisman.yml`:

```yaml
dispatch:
  enabled: true                          # Default: true. Set false to disable --background flag.
  default_mode: background               # "background" | "foreground". Default: foreground.
  auto_collect_on_complete: true         # Auto-run --collect after all workers finish. Default: true.
  status_poll_interval_seconds: 30       # /rune:status refresh interval. Default: 30.
  question_cap: 3                        # Max questions per worker in background mode (SEC-006). Default: 3.
  lock_enforcement: true                 # Enforce single active dispatch per session (PERF-005). Default: true.
```

---

## Security Requirements

| Requirement | Reference | Enforcement |
|-------------|-----------|-------------|
| Session isolation triple in state file | SEC-004 | config_dir + owner_pid + session_id fields |
| Signal dir created with owner-only perms | SEC-005 | `mkdir -m 700` |
| Lock file created with owner-only perms | SEC-005 | `mkdir -m 700` before touch |
| Question cap prevents unbounded blocking | SEC-006 | Worker checks question count before writing |
| Timestamp format validated before path use | SEC-004 | `/^\d{8}-\d{6}$/` regex in /rune:status |
