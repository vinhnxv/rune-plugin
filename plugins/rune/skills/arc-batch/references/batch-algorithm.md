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
  ├── Main loop: for each plan → claude -p "/rune:arc ..."
  │   ├── pre_run_git_health() — stuck rebase, stale lock, MERGE_HEAD, dirty tree
  │   ├── Retry loop (max 3 attempts, --resume on retry)
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
      "completed_at": "ISO-8601 | null"
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
  "stop_on_divergence": false
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
| Batch total_budget exceeded | Break loop, mark remaining as failed | arc-batch.sh budget guard |
| Batch total_timeout exceeded | Break loop, mark remaining as failed | arc-batch.sh timeout guard |
| Main branch divergence | Break loop when stop_on_divergence=true | arc-batch.sh divergence guard |
