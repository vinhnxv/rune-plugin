# Batch Algorithm Reference

Full orchestration pseudocode for `/rune:arc-batch`. The SKILL.md body contains the executable version; this reference documents the design rationale and edge cases.

## Architecture (V2 — Stop Hook Pattern, v1.59.0)

```
SKILL.md (orchestration layer)
  ├── Phase 0: Parse $ARGUMENTS → plan list
  ├── Phase 1: Pre-flight → arc-batch-preflight.sh (validation)
  ├── Phase 2: Dry run (if --dry-run) → early return
  ├── Phase 3: Initialize batch-progress.json
  ├── Phase 4: Confirm batch → AskUserQuestion
  └── Phase 5: Start loop → write state file + Skill("arc", firstPlan)
                │
                └── Stop hook drives all subsequent iterations:

scripts/arc-batch-stop-hook.sh (Stop hook — loop driver)
  ├── Guard: jq available?
  ├── Guard: stdin cap (64KB)
  ├── Guard: CWD extraction from hook input
  ├── Guard: .claude/arc-batch-loop.local.md exists?
  ├── Guard: symlink check
  ├── Guard: active flag = true?
  ├── Guard: numeric field validation
  ├── Guard: max_iterations reached?
  ├── Read batch-progress.json
  │   ├── Mark current in_progress plan → completed
  │   └── Find next pending plan
  ├── No more plans?
  │   └── rm state file → block stop with summary prompt
  └── More plans?
      ├── Increment iteration in state file
      ├── Git cleanup (checkout main, pull --ff-only)
      ├── Clean stale teams/tasks dirs
      └── Output: {"decision":"block","reason":"<arc prompt>"}
```

**Key difference from V1**: Each arc run executes as a native Claude Code turn. No subprocess spawning, no Bash tool timeout limit, no orphaned processes. The Stop hook intercepts session end and re-injects the next arc prompt.

**Inspired by**: [ralph-wiggum plugin](https://github.com/anthropics/claude-code/tree/main/plugins/ralph-wiggum) Stop hook pattern.

## V1 Architecture (DEPRECATED — arc-batch.sh)

The V1 architecture used `scripts/arc-batch.sh` to spawn `claude -p` subprocesses in a loop. This was broken because the Bash tool timeout (max 600s / 10 min) is far shorter than a single arc run (45-240 min). The parent process would be killed, orphaning the child `claude -p` process, causing the batch to get stuck after the first plan.

See `scripts/arc-batch.sh` (deprecated) for the V1 implementation.

## State File Format

The Stop hook reads and writes `.claude/arc-batch-loop.local.md`:

```yaml
---
active: true
iteration: 1
max_iterations: 0
total_plans: 4
no_merge: false
plugin_dir: /path/to/rune/plugin
plans_file: tmp/arc-batch/plan-list.txt
progress_file: tmp/arc-batch/batch-progress.json
started_at: "2026-02-21T00:00:00Z"
---

Batch arc loop state. Do not edit manually.
Use /rune:cancel-arc-batch to stop.
```

## Stop Hook Loop Flow

```
Claude session turn N:
  1. /rune:arc completes (or user ends turn)
  2. Claude stops responding → Stop hook fires
  3. arc-batch-stop-hook.sh reads state file
  4. Marks current plan completed in batch-progress.json
  5. Finds next pending plan
  6. Outputs blocking JSON → Claude starts new turn with arc prompt
  7. /rune:arc runs for next plan
  8. Repeat from step 2

Final iteration:
  3. Stop hook reads state file, finds no more pending plans
  4. Removes state file
  5. Outputs blocking JSON with summary prompt
  6. Claude reads batch-progress.json, presents summary
  7. Stop hook fires again, no state file → exit 0 (allows stop)
```

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

## Edge Case Matrix (V2)

| Edge Case | Handler | Location |
|-----------|---------|----------|
| Empty glob (zsh NOMATCH) | Glob tool handles expansion | SKILL.md Phase 0 |
| Plan file doesn't exist | arc-batch-preflight.sh validates | scripts/ |
| Plan file is symlink | arc-batch-preflight.sh rejects | scripts/ |
| Duplicate plan in list | arc-batch-preflight.sh deduplicates | scripts/ |
| Path traversal (`..`) | arc-batch-preflight.sh rejects | scripts/ |
| Auto-merge disabled | SKILL.md detects and prompts | SKILL.md Phase 1 |
| State file missing | Stop hook exits 0 (no active batch) | arc-batch-stop-hook.sh |
| State file is symlink | Stop hook exits 0 (security guard) | arc-batch-stop-hook.sh |
| State file corrupt/non-YAML | Stop hook removes state file, exits 0 | arc-batch-stop-hook.sh |
| jq unavailable | Stop hook exits 0 (cannot parse progress) | arc-batch-stop-hook.sh |
| stdin exceeds 64KB | Stop hook exits 0 (safety cap) | arc-batch-stop-hook.sh |
| max_iterations reached | Stop hook removes state file, exits 0 | arc-batch-stop-hook.sh |
| Progress file missing | Stop hook removes state file, exits 0 | arc-batch-stop-hook.sh |
| No more pending plans | Stop hook removes state file, blocks with summary prompt | arc-batch-stop-hook.sh |
| Git checkout/pull fails | Stop hook skips git ops, includes in prompt | arc-batch-stop-hook.sh |
| Context window growth | Auto-compaction handles; state in file not context | Claude Code |
| Cancel mid-batch | `/rune:cancel-arc-batch` removes state file | commands/cancel-arc-batch.md |
| Cancel arc also cancels batch | `/rune:cancel-arc` Step 0 removes batch state file | commands/cancel-arc.md |
| on-session-stop.sh conflict | GUARD 5 defers when batch state file present | scripts/on-session-stop.sh |
| Stale teams between plans | Stop hook cleans teams/tasks dirs | arc-batch-stop-hook.sh |

## V1 Edge Cases (DEPRECATED — arc-batch.sh)

These edge cases applied to the V1 subprocess architecture and are no longer relevant:

| Edge Case | V1 Handler | V2 Status |
|-----------|-----------|-----------|
| Bash tool timeout (600s) | Root cause of V1 failure | Eliminated — no Bash subprocess |
| `claude -p` not available | SKILL.md check | Eliminated — uses native Skill() |
| `setsid` unavailable | Fallback to direct exec | Eliminated — no subprocess |
| Claude hangs after completion | Checkpoint watchdog | Eliminated — Stop hook fires naturally |
| `$!` captures tee PID | Direct redirect fix | Eliminated — no subprocess |
| JSON output buffers | `--output-format text` | Eliminated — no subprocess |
