# Batch Algorithm Reference

Full orchestration pseudocode for `/rune:arc-batch`. The SKILL.md body contains the executable version; this reference documents the design rationale and edge cases.

## Architecture

```
SKILL.md (orchestration layer)
  ├── Phase 0: Parse $ARGUMENTS → plan list
  ├── Phase 1: Pre-flight → arc-batch-preflight.sh (validation)
  ├── Phase 2: Dry run (if --dry-run) → early return
  ├── Phase 3: Initialize batch-progress.json
  ├── Phase 4: Confirm batch → AskUserQuestion
  ├── Phase 5: Run batch → arc-batch.sh (execution layer)
  └── Phase 6: Present summary

scripts/arc-batch.sh (execution layer)
  ├── Pre-flight: jq, git availability
  ├── Config: read batch-config.json
  ├── Signal handling: SIGINT/SIGTERM/SIGHUP trap
  ├── Main loop: for each plan → [timeout] [setsid] claude -p "..."
  │   ├── pre_run_git_health() — stuck rebase, stale lock, MERGE_HEAD, dirty tree
  │   ├── Retry loop (max 3 attempts, --resume on retry)
  │   ├── Watchdog polling (10s): process alive? + checkpoint status check
  │   │   └── Checkpoint complete + process hung 60s → SIGTERM → SIGKILL after 5s
  │   ├── On success: cleanup_state("inter") — checkout main, pull, delete branch
  │   └── On failure: cleanup_state("failed") — hard reset, checkout main
  └── Final summary: update progress, exit code
```

## Process Isolation Strategy

### With `setsid` (Linux, macOS with coreutils)

```
arc-batch.sh (session leader)
  └── setsid claude -p "..." (new session, new process group)
        └── child processes (inherit PGID from setsid)
```

Signal handling: `kill -TERM $PID` kills the `claude` process. Child processes receive SIGHUP when session leader dies.

### Without `setsid` (macOS default)

```
arc-batch.sh (parent)
  └── claude -p "..." (same session, child process)
        └── child processes
```

Signal handling: `kill -TERM $PID` kills `claude` directly. Child processes may need explicit cleanup.

### Checkpoint-Based Completion Detection (v1.57.1)

```
arc-batch.sh (parent)                    claude -p "arc pipeline" (child)
─────────────────────                    ────────────────────────────────
Snapshot: ls .claude/arc/ (before)       Phase 1-9: work, review, mend...
Spawn claude -p ...                      → Creates .claude/arc/arc-{ts}/checkpoint.json
                                         → Updates checkpoint at each phase transition
Watchdog loop (every 10s):               Phase 9.5: merge done!
  1. Process alive? (kill -0)              → checkpoint: merge.status = "completed"
  2. Detect new arc session ID             Completion stamp...
     (diff pre/post ls .claude/arc/)       (process may hang here)
  3. Read checkpoint.json
     → merge + ship both done?
     → 6 consecutive detections (60s grace)
     → kill -TERM → wait 5s → kill -KILL
```

**Arc session tracing**: Before spawning claude, arc-batch snapshots existing arc session dirs. After spawn, it diffs the listing to find the new `arc-{timestamp}` dir, then verifies `plan_file` matches the current plan. The arc session ID is recorded in `batch-progress.json` for traceability.

**No pipeline modifications needed**: Checkpoint is already written by the arc dispatcher at every phase transition — arc-batch.sh is a passive observer.

## Progress File Schema

```json
{
  "schema_version": 1,
  "status": "running | completed | finished | interrupted",
  "started_at": "ISO-8601",
  "updated_at": "ISO-8601",
  "completed_at": "ISO-8601 | null",
  "total_duration_s": 0,
  "total_plans": 3,
  "plans": [
    {
      "path": "plans/feat-a.md",
      "status": "pending | in_progress | completed | failed",
      "error": "null | error message",
      "completed_at": "ISO-8601 | null",
      "arc_session_id": "arc-{timestamp} | null"
    }
  ]
}
```

## Config File Schema

Config values are resolved via **3-layer priority**: hardcoded defaults → `talisman.yml` (`arc.batch.*`) → future CLI flags.

```json
{
  "plans_file": "tmp/arc-batch/plan-list.txt",
  "plugin_dir": "/path/to/rune/plugin",
  "progress_file": "tmp/arc-batch/batch-progress.json",
  "no_merge": false,
  "max_retries": 3,
  "max_budget": 15.0,
  "max_turns": 200,
  "total_budget": null,
  "total_timeout": null,
  "stop_on_divergence": false,
  "per_plan_timeout": 7200
}
```

## Edge Case Matrix

| Edge Case | Handler | Location |
|-----------|---------|----------|
| Empty glob (zsh NOMATCH) | Glob tool handles expansion | SKILL.md Phase 0 |
| Plan file doesn't exist | arc-batch-preflight.sh validates | scripts/ |
| Plan file is symlink | arc-batch-preflight.sh rejects | scripts/ |
| Duplicate plan in list | arc-batch-preflight.sh deduplicates | scripts/ |
| Path traversal (`..`) | arc-batch-preflight.sh rejects | scripts/ |
| `claude -p` not available | SKILL.md checks `command -v claude` | SKILL.md Phase 0 |
| Auto-merge disabled | SKILL.md detects and prompts | SKILL.md Phase 1 |
| Arc fails at Phase 5 | Retry --resume up to 3x, then skip | arc-batch.sh |
| Post-merge branch cleanup | checkout main, pull --ff-only | arc-batch.sh cleanup_state |
| Ctrl+C mid-batch | trap sends TERM to child PID | arc-batch.sh cleanup() |
| Stuck rebase from prior arc | pre_run_git_health() aborts | arc-batch.sh |
| Stale .git/index.lock | pre_run_git_health() removes | arc-batch.sh |
| `setsid` unavailable (macOS) | Falls back to direct execution | arc-batch.sh HAS_SETSID |
| Claude hangs after completion | Checkpoint watchdog detects done, kills in ~60s | arc-batch.sh watchdog loop |
| Claude hangs (checkpoint not written) | `timeout --kill-after=30` kills process (exit 124) | arc-batch.sh per_plan_timeout |
| Arc session ID unknown | Pre/post spawn `ls .claude/arc/` diff + plan_file match | arc-batch.sh session tracing |
| `$!` captures tee PID (not claude) | Direct redirect (`> file`) — no pipe | arc-batch.sh FIX-2 |
| JSON output buffers (0-byte logs) | `--output-format text` for streaming | arc-batch.sh FIX-3 |
| Path with spaces/tildes rejected | Denylist (metacharacters) instead of allowlist | arc-batch.sh validate_path |
| Spend tracking inflated | 50% heuristic instead of max_budget | arc-batch.sh FIX-4 |
| Batch total_budget exceeded | Break loop, mark remaining as failed | arc-batch.sh budget guard |
| Batch total_timeout exceeded | Break loop, mark remaining as failed | arc-batch.sh timeout guard |
| Main branch divergence | Break loop when stop_on_divergence=true | arc-batch.sh divergence guard |
