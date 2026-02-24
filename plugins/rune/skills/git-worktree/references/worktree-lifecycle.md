# Worktree Lifecycle

Each worker's worktree follows a 6-phase lifecycle from creation through cleanup, with crash recovery handling.

**Inputs**: Task spawn with `isolation: "worktree"`
**Outputs**: Merged commits on feature branch, cleaned-up worktree
**Preconditions**: Git worktree mode active (flag or talisman config)

## 6-Phase Lifecycle

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

## Worker Crash Handling

If a worker crashes mid-commit:
1. Check `git status --porcelain` in the worktree
2. `git reset --hard HEAD` to discard partial changes
3. Remove worktree via `git worktree remove --force`
4. Return task to pool for reclaim
