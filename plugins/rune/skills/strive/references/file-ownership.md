# File Ownership and Task Pool (Phase 1)

## Task Pool Creation

1. Extract file targets (`fileTargets`, `dirTargets`) per task from plan
2. Classify risk tiers — see `risk-tiers.md` in `roundtable-circle/references/`
3. Detect overlapping file ownership via set intersection (O(n²) cap: 200 targets)
4. Serialize conflicting tasks via `blockedBy` links
5. Create task pool via `TaskCreate` with quality contract embedded in description
6. Link dependencies using mapped IDs — see [dependency-patterns.md](dependency-patterns.md) for named patterns and anti-patterns
7. Compute wave groupings (worktree mode only) using DFS depth algorithm
8. Write `task_ownership` to inscription.json for runtime enforcement (SEC-STRIVE-001)

## Runtime File Ownership Enforcement (SEC-STRIVE-001)

After creating the task pool, write `task_ownership` to `inscription.json` mapping each task to its file/dir targets. The `validate-strive-worker-paths.sh` PreToolUse hook reads this at runtime to block writes outside assigned scope.

```javascript
// Build task_ownership mapping for inscription.json
const taskOwnership = {}
for (const task of extractedTasks) {
  const targets = extractFileTargets(task)
  if (targets.files.length > 0 || targets.dirs.length > 0) {
    taskOwnership[task.id] = {
      owner: task.assignedWorker || "unassigned",
      files: targets.files,
      dirs: targets.dirs
    }
  }
  // Tasks with no extractable targets are unrestricted (not added to task_ownership)
}
```

### Inscription Format

```json
{
  "workflow": "rune-work",
  "timestamp": "20260225-015124",
  "task_ownership": {
    "task-1": { "owner": "rune-smith-1", "files": ["src/auth.ts"], "dirs": ["src/auth/"] },
    "task-2": { "owner": "rune-smith-2", "files": ["src/api/users.ts"], "dirs": ["src/api/"] }
  }
}
```

The hook uses a **flat union** approach: all tasks' file targets are merged into one allowlist. This means worker-A can write to worker-B's files, but files NOT in ANY task's target list are blocked. Talisman `work.unrestricted_shared_files` array is appended to every task's allowlist (for shared config files like `package.json`).

## Quality Contract

Embedded in every task description:

```
Quality requirements (mandatory):
- Type annotations on ALL function signatures (params + return types)
- Use `from __future__ import annotations` at top of every Python file
- Docstrings on all public functions, classes, and modules
- Specific exception types (no bare except, no broad Exception catch)
- Tests must cover edge cases (empty input, None values, type mismatches)
```
