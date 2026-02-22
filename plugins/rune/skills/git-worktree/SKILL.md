---
name: git-worktree
description: |
  Knowledge skill for git worktree isolation in /rune:strive. Loaded when worktree
  mode is active (--worktree flag or work.worktree.enabled talisman). Covers
  worktree lifecycle, merge strategy, conflict resolution, wave-based execution,
  and talisman configuration.
  Keywords: worktree, isolation, wave, merge broker, branch merge, conflict.

  <example>
  Context: Orchestrator activating worktree mode for /rune:strive
  user: "/rune:strive plans/feat-api-plan.md --worktree"
  assistant: "Worktree mode active. Workers will operate in isolated worktrees with direct commit."
  </example>

  <example>
  Context: Merge conflict during wave merge
  user: (internal — merge broker detects conflict)
  assistant: "Conflict detected in src/api.ts during Wave 1 merge. Escalating to user."
  </example>
user-invocable: false
disable-model-invocation: false  # Intentional: model loads this skill when worktree mode detected
allowed-tools:
  - Read
  - Glob
  - Grep
---

# Git Worktree — Isolation Mode for /rune:strive

## Overview

Git worktree mode gives each swarm worker its own isolated working copy via
`isolation: "worktree"` on the Task tool. Workers commit directly in their
worktrees instead of generating patches. After each wave of workers completes,
the orchestrator merges worktree branches back into the feature branch.

**Two execution modes** coexist in `/rune:strive`:

| Mode | Flag | Worker Behavior | Commit Strategy |
|------|------|----------------|-----------------|
| **Patch** (default) | `--patch` or no flag | Shared working tree | Patch -> commit broker |
| **Worktree** | `--worktree` | `isolation: "worktree"` | Direct commit -> merge broker |

Talisman override: `work.worktree.enabled: true` makes worktree mode the default.

## Worktree Lifecycle

Each worker's worktree follows this lifecycle:

```
1. CREATE — SDK creates worktree with unique branch when Task spawns
   - Automatic: git worktree add <path> -b <branch>
   - Worker CWD set to worktree path
   - Branch name: SDK-assigned (included in Task result)

2. WORK — Worker implements task in isolated worktree
   - Full read/write access to all project files (copy)
   - Changes are invisible to other workers
   - Worker follows normal lifecycle (claim -> implement -> ward)

3. COMMIT — Worker commits directly (replaces patch generation)
   - git add <specific-files>
   - Write commit message to a temp file
   - git commit -F <commit-msg-file>  # SEC-011: no inline -m
   - Exactly ONE commit per task (enforced by prompt)
   - Worker MUST NOT push or merge

4. SEAL — Worker reports completion with branch name
   - Format: "Seal: task #{id} done. Branch: {branch}. Files: {list}"
   - Branch name also stored in task metadata (backup channel)

5. MERGE — Orchestrator merges branch after wave completes
   - git merge --no-ff {branch} -m "rune: merge {worker} [worktree]"
   - Sequential merge order (by task ID) for deterministic history

6. CLEANUP — Orchestrator removes worktree and branch
   - git worktree remove {worktreePath}
   - git branch -d {branch} (merged) or -D (aborted)
   - git worktree prune (final cleanup)
```

**Worker crash handling**: If a worker crashes mid-commit:
1. Check `git status --porcelain` in the worktree
2. `git reset --hard HEAD` to discard partial changes
3. Remove worktree via `git worktree remove --force`
4. Return task to pool for reclaim

## Merge Strategy

Worktree mode uses **sequential merge with `--no-ff`** for clear, revertable history.

### Why Sequential (not Octopus)

| Strategy | Pros | Cons |
|----------|------|------|
| Sequential `--no-ff` | Conflict isolation, partial progress, revertable | Slower for many branches |
| Octopus merge | Single commit | All-or-nothing, no conflict resolution |
| Rebase | Linear history | Rewrites SHAs, harder to audit |
| Cherry-pick | Selective | Loses branch context |

**Decision**: Sequential `--no-ff` (ADR 4) because:
- Know exactly which two branches conflict
- 3 of 5 can merge cleanly even if 2 conflict
- Each merge is individually revertable via `git revert -m1`
- Deterministic history (sorted by task ID)

### Merge Broker Algorithm

See [worktree-merge.md](../work/references/worktree-merge.md) for the
complete merge broker algorithm, including:
- Branch validation against `BRANCH_RE`
- Deduplication guard (`mergedBranches` Set)
- Empty branch detection (skip no-change workers)
- Pre-wave checkpoint tags
- Conflict escalation flow
- Cleanup procedures

## Conflict Resolution

**Critical rule (C1)**: No auto-resolution. On ANY merge conflict, escalate to user.

```
Conflict detected in {file}
  |
  v
AskUserQuestion: How to resolve?
  |
  +-- "Accept theirs" -> git checkout --theirs {file} && git add {file}
  +-- "Accept ours"   -> git checkout --ours {file} && git add {file}
  +-- "Manual resolve" -> pause pipeline, user edits, git add, continue
  +-- "Abort merge"   -> git merge --abort, mark NEEDS_MANUAL_MERGE
```

**Why no auto-resolve**: `git checkout --theirs` replaces the ENTIRE file with the
incoming version, discarding all "ours" changes. This is too destructive for automated use.
User must make an informed choice for each conflict.

## Wave-Based Execution

Tasks are grouped into **waves** by dependency depth to enable parallel execution
while respecting dependencies:

```
Wave 0: Tasks with no dependencies
    -> Workers run in parallel worktrees
    -> After all complete: merge all Wave 0 branches
    |
Wave 1: Tasks whose deps are all in Wave 0
    -> Workers start from merged state
    -> After all complete: merge all Wave 1 branches
    |
Wave N: Tasks whose deps are all in Wave 0..N-1
    -> Same pattern
```

### Dependency Depth Calculation

```
depthOf(task):
  if task has no blockers: return 0
  return 1 + max(depthOf(blocker) for blocker in task.blockedBy)

waves = groupBy(tasks, depthOf)
```

**Cycle detection**: Uses DFS white/gray/black coloring. Cycle detected -> abort
with error listing the cycle path.

### Wave Execution Flow

```
for wave in 0..maxWave:
  1. Create pre-wave checkpoint: git tag rune-wave-{N}-pre-merge
  2. Spawn workers for this wave with isolation: "worktree"
  3. Monitor wave (TaskList polling, same as patch mode)
  4. After all wave tasks complete: run merge broker
  5. Log: "Wave {N}/{maxWave} complete ({completed}/{total} tasks)"
  6. If all wave tasks failed: abort (do not proceed to next wave)
```

**Max workers per wave**: Capped by `work.worktree.max_workers_per_wave` (default: 3)
or `min(work.max_workers, 3)` if not configured.

## Talisman Configuration

```yaml
work:
  worktree:
    enabled: false                    # Default: patch mode
    max_workers_per_wave: 3           # Max parallel workers per wave
    merge_strategy: "sequential"      # Only "sequential" supported
    auto_cleanup: true                # Remove worktrees after merge
    conflict_resolution: "escalate"   # "escalate" (ask user) | "abort"
```

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `work.worktree.enabled` | boolean | `false` | Make worktree mode the default |
| `work.worktree.max_workers_per_wave` | number | `3` | Max parallel workers per wave |
| `work.worktree.merge_strategy` | string | `"sequential"` | Merge strategy (only sequential) |
| `work.worktree.auto_cleanup` | boolean | `true` | Auto-remove worktrees after merge |
| `work.worktree.conflict_resolution` | string | `"escalate"` | Conflict handling mode |

**Relationship to existing keys**:
- `work.max_workers` caps total workers across the session
- `work.worktree.max_workers_per_wave` caps per-wave concurrency
- Effective per-wave cap: `min(max_workers, max_workers_per_wave)`

## State File Extensions

When worktree mode is active, the state file (`tmp/.rune-work-{timestamp}.json`)
includes additional fields:

```javascript
{
  // ... existing fields ...
  worktree_mode: true,           // Absent in patch mode (falsy)
  waves: [[taskIds], [taskIds]], // Task IDs grouped by wave
  current_wave: 0,               // Currently executing wave index
  merged_branches: []             // Branches successfully merged
}
```

## Safety Notes

- **Blast radius reduction**: A rogue worker only damages its own worktree (primary benefit)
- **Disk usage**: Each worktree creates a full working copy (shared `.git` objects)
- **Dependency blindness**: Workers cannot see other workers' uncommitted changes
- **SDK canary**: Phase 0 validates `isolation: "worktree"` support before proceeding
- **Experimental**: Worktree mode is marked experimental in initial release

## References

- [worktree-merge.md](../work/references/worktree-merge.md) — Merge broker algorithm, conflict handling, cleanup
- [worker-prompts.md](../work/references/worker-prompts.md) — Worker prompt templates (patch + worktree modes)
- [parse-plan.md](../work/references/parse-plan.md) — Task extraction and dependency parsing
