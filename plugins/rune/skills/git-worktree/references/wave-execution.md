# Wave-Based Execution

Tasks are grouped into waves by dependency depth to enable parallel execution while respecting dependencies. Each wave completes fully before the next begins.

**Inputs**: Task list with dependency graph (blockedBy relationships)
**Outputs**: Sequentially merged wave results on feature branch
**Preconditions**: Tasks decomposed with dependency information

## Wave Grouping by Dependency Depth

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

## Dependency Depth Calculation

```
depthOf(task):
  if task has no blockers: return 0
  return 1 + max(depthOf(blocker) for blocker in task.blockedBy)

waves = groupBy(tasks, depthOf)
```

## Cycle Detection

Uses DFS white/gray/black coloring. Cycle detected -> abort with error listing the cycle path.

## Wave Execution Flow

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
