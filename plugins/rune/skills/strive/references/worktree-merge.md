# Worktree Merge Broker — work.md Phase 3.5 Reference

Merge broker for worktree mode. Called between waves and after the final wave to merge worktree branches into the feature branch. Coexists with the existing commit broker — selected by `worktreeMode` flag.

## Overview

In worktree mode, workers commit directly in their git worktrees instead of generating patches. After each wave completes, the merge broker merges worker branches into the feature branch sequentially.

```
Patch mode:  Worker → patch → commitBroker() → git apply → git commit
Worktree mode: Worker → git commit → mergeBroker() → git merge --no-ff → cleanup
```

## Merge Broker Algorithm

```javascript
// State: maintained across waves for deduplication
const mergedBranches = new Set()
const mergeSHAs = []

function mergeBroker(completedBranches, featureBranch) {
  // Inputs: completedBranches[] (from Task results or Seal messages)
  //         featureBranch (current branch name)
  // Outputs: merged feature branch, updated mergeSHAs[]
  // Preconditions: All wave workers have exited, branches exist
  // Error handling: Merge conflict → escalate to user (NEVER auto-resolve)

  const BRANCH_RE = /^[a-zA-Z0-9][a-zA-Z0-9._\/-]*$/

  // Sort by task ID for deterministic merge order
  const sorted = completedBranches.sort((a, b) => a.taskId - b.taskId)

  for (const entry of sorted) {
    const { branchName, taskId, workerName, worktreePath } = entry

    // 1. Dedup guard: skip if already merged (compaction recovery, duplicate Seal)
    if (mergedBranches.has(branchName)) {
      warn(`Task ${taskId}: duplicate merge request for branch ${branchName} -- skipping`)
      continue
    }

    // 2. Validate branch name against BRANCH_RE
    if (!branchName || !BRANCH_RE.test(branchName)) {
      warn(`Task ${taskId}: invalid branch name "${branchName}" -- skipping merge`)
      continue
    }

    // 3. Empty branch detection: skip if no commits ahead of feature branch
    const commitCount = Bash(`git log "${featureBranch}".."${branchName}" --oneline | wc -l`).trim()
    if (commitCount === "0") {
      log(`Task ${taskId}: no changes on branch ${branchName} -- skipping merge (completed-no-change)`)
      cleanupWorktree(worktreePath, branchName)
      mergedBranches.add(branchName)
      continue
    }

    // 4. Merge with --no-ff for clear history
    //    Use file-based commit message (consistent with commitBroker pattern)
    const safeWorkerName = workerName.replace(/[^a-zA-Z0-9_-]/g, '').slice(0, 32)
    Write(`tmp/work/${timestamp}/patches/${taskId}-merge-msg.txt`,
      `rune: merge ${safeWorkerName} [worktree]`)
    const mergeResult = Bash(
      `git merge --no-ff "${branchName}" -F "tmp/work/${timestamp}/patches/${taskId}-merge-msg.txt"`
    )

    if (mergeResult.exitCode !== 0) {
      // 5. Conflict handling — escalate to user (C1: NO auto-resolve)
      handleMergeConflict(branchName, taskId, featureBranch)
      continue
    }

    // 6. Record merge SHA
    const sha = Bash("git rev-parse HEAD").trim()
    mergedBranches.add(branchName)
    mergeSHAs.push(sha)
    log(`Task ${taskId}: merged branch ${branchName} (${sha.slice(0, 8)})`)

    // 7. Cleanup worktree and branch
    cleanupWorktree(worktreePath, branchName)
  }
}
```

## Conflict Detection and Resolution

**CRITICAL (C1)**: On merge conflict, escalate to the user via AskUserQuestion. Do NOT use `git checkout --theirs` or any automatic conflict resolution — this replaces entire files and discards valid changes.

```javascript
function handleMergeConflict(branchName, taskId, featureBranch) {
  // Identify conflicting files
  const conflictFiles = Bash("git diff --name-only --diff-filter=U").trim()

  AskUserQuestion({
    questions: [{
      question: `Merge conflict merging branch \`${branchName}\` (task #${taskId}):\n\nConflicting files:\n${conflictFiles}\n\nHow to resolve?`,
      header: "Merge Conflict",
      options: [
        { label: "Manual resolve", description: "Pause pipeline -- resolve conflicts manually, then continue" },
        { label: "Accept incoming (theirs)", description: "Accept ALL changes from the worker branch" },
        { label: "Keep current (ours)", description: "Keep current branch state, discard worker changes" },
        { label: "Abort merge", description: "git merge --abort -- mark task as NEEDS_MANUAL_MERGE" }
      ],
      multiSelect: false
    }]
  })

  // Handle user choice:
  // "Manual resolve":
  //   1. Instruct user: "Resolve conflicts in the listed files, then run: git add <files> && git commit"
  //   2. Wait for user confirmation (AskUserQuestion with "Continue" button)
  //   3. Verify merge completed: git merge HEAD (exit 0 = clean)
  //   4. Record SHA, add to mergedBranches
  //
  // "Accept incoming (theirs)":
  //   1. For EACH conflicting file: git checkout --theirs <file> && git add <file>
  //   2. git commit -F <merge-msg-file>
  //   3. Record SHA, add to mergedBranches
  //   NOTE: Only used on explicit user request — never automatic
  //
  // "Keep current (ours)":
  //   1. For EACH conflicting file: git checkout --ours <file> && git add <file>
  //   2. git commit -F <merge-msg-file>
  //   3. Record SHA, add to mergedBranches
  //
  // "Abort merge":
  //   1. Bash("git merge --abort")
  //   2. Mark task as NEEDS_MANUAL_MERGE in task metadata
  //   3. warn(`Task ${taskId}: merge aborted -- marked NEEDS_MANUAL_MERGE`)
  //   4. Do NOT add to mergedBranches (can be retried)
  //   5. Cleanup worktree but keep branch for manual retry
}
```

## Pre-Wave Checkpoint

Before merging each wave's branches, create a lightweight git tag for atomic rollback:

```javascript
function createWaveCheckpoint(waveIndex) {
  // Tag format: rune-wave-{N}-pre-merge
  // Allows: git reset --hard rune-wave-0-pre-merge (rollback entire wave merge)
  const tagName = `rune-wave-${waveIndex}-pre-merge`
  Bash(`git tag -f "${tagName}"`)
  log(`Wave ${waveIndex}: checkpoint tag created (${tagName})`)
}

// Usage in wave loop:
// createWaveCheckpoint(waveIndex)
// mergeBroker(waveBranches, featureBranch)
```

## Worktree Cleanup

```javascript
function cleanupWorktree(worktreePath, branchName) {
  // 1. Check for uncommitted changes in worktree (EC-1: worker crash mid-commit)
  if (worktreePath) {
    const worktreeStatus = Bash(`git -C "${worktreePath}" status --porcelain 2>/dev/null`).trim()
    if (worktreeStatus !== "") {
      warn(`Worktree ${worktreePath} has uncommitted changes -- resetting before removal`)
      Bash(`git -C "${worktreePath}" reset --hard HEAD 2>/dev/null`)
    }
  }

  // 2. Remove worktree (retry with --force on failure)
  if (worktreePath) {
    const removeResult = Bash(`git worktree remove "${worktreePath}" 2>/dev/null`)
    if (removeResult.exitCode !== 0) {
      warn(`Worktree removal failed for ${worktreePath} -- forcing removal`)
      Bash(`git worktree remove --force "${worktreePath}" 2>/dev/null`)
    }
  }

  // 3. Delete merged branch
  //    Use -d (not -D) for merged branches -- -D for aborted merges only
  const deleteResult = Bash(`git branch -d "${branchName}" 2>/dev/null`)
  if (deleteResult.exitCode !== 0) {
    warn(`Branch deletion failed for ${branchName} -- forcing deletion`)
    Bash(`git branch -D "${branchName}" 2>/dev/null`)
  }
}
```

## Phase 6 Worktree Garbage Collection

At cleanup time (Phase 6), collect any orphaned worktrees and branches from failed runs:

```javascript
function worktreeGarbageCollection(timestamp) {
  // 1. Prune stale worktree entries
  Bash("git worktree prune")

  // 2. Remove orphaned worktrees matching rune-work pattern
  const worktreeList = Bash("git worktree list --porcelain").trim()
  const worktreeEntries = worktreeList.split("\n\n").filter(e => e.includes("rune-work-"))
  for (const entry of worktreeEntries) {
    const pathMatch = entry.match(/^worktree (.+)$/m)
    if (pathMatch) {
      warn(`Removing orphaned worktree: ${pathMatch[1]}`)
      Bash(`git worktree remove --force "${pathMatch[1]}" 2>/dev/null`)
    }
  }

  // 3. Cleanup orphaned branches (retry-with-backoff pattern)
  const CLEANUP_DELAYS = [0, 3000, 8000]
  const orphanBranches = Bash("git branch --list 'rune-work-*' 2>/dev/null").trim()
  if (orphanBranches) {
    for (const branch of orphanBranches.split('\n').map(b => b.trim()).filter(Boolean)) {
      // Skip current branch
      if (branch.startsWith('*')) continue
      const cleanBranch = branch.replace(/^\*?\s*/, '')
      if (!BRANCH_RE.test(cleanBranch)) continue
      Bash(`git branch -D "${cleanBranch}" 2>/dev/null`)
    }
  }

  // 4. Final prune pass
  Bash("git worktree prune")
}
```

## Worker-to-Branch Mapping

Workers encode branch information via two channels (backup for compaction recovery):

### Channel 1: Seal Message (Primary)

```
Seal: task #{id} done. Branch: {branchName}. Files: {list}
```

The orchestrator extracts `Branch:` from Seal messages to build `completedBranches[]`.

### Channel 2: Task Metadata (Backup)

```javascript
// Worker writes branch name to task metadata before Seal
TaskUpdate({ taskId, metadata: { branch: worktreeBranch } })

// Orchestrator reads from metadata if Seal message lost (compaction recovery)
const task = TaskGet(taskId)
const branch = task.metadata?.branch
```

### Collecting Branches After Wave Completion

```javascript
function collectWaveBranches(waveTasks) {
  // Inputs: waveTasks[] (completed tasks for this wave)
  // Outputs: completedBranches[] for mergeBroker()

  const completedBranches = []

  for (const task of waveTasks) {
    // Primary: from Task result (isolation: "worktree" returns worktreeBranch)
    let branchName = task.result?.worktreeBranch
    let worktreePath = task.result?.worktreePath

    // Backup: from task metadata (set by worker in Seal flow)
    if (!branchName) {
      const taskDetail = TaskGet(task.id)
      branchName = taskDetail.metadata?.branch
    }

    // Fallback: discover via git worktree list
    if (!branchName) {
      warn(`Task ${task.id}: no branch info in result or metadata -- discovering via git worktree list`)
      const worktrees = Bash("git worktree list --porcelain").trim()
      // Correlate by worker name or path pattern
      // This is best-effort -- log warning if unable to match
    }

    if (branchName) {
      completedBranches.push({
        branchName,
        taskId: task.id,
        workerName: task.owner || "unknown",
        worktreePath
      })
    } else {
      warn(`Task ${task.id}: unable to determine worktree branch -- skipping merge`)
    }
  }

  return completedBranches
}
```

## Error Handling Matrix

| Error | Exit Code | Recovery |
|-------|-----------|----------|
| Merge conflict (content) | 1 | Escalate to user via AskUserQuestion. Options: manual resolve, accept theirs, accept ours, abort |
| Merge failure (non-conflict) | 128/129 | Log error, `git merge --abort`, mark NEEDS_MANUAL_MERGE |
| Worktree creation failure | N/A | Retry once, fallback to patch mode for that task |
| Worktree locked by process | N/A | `git worktree remove --force`, log warning |
| Branch name collision | N/A | Append unique suffix, or delete stale branch from previous failed run |
| Worker writes wrong dir | N/A | Worker prompt specifies absolute paths for output files |
| Wave timeout (partial) | N/A | Merge completed branches, return timed-out tasks to pool |
| Empty branch (no commits) | N/A | Skip merge, log as completed-no-change |
| Branch not found | 128 | Skip merge, warn, check if worker crashed before committing |
| Disk full during merge | 128 | Abort merge, warn user, suggest cleanup |
| Partial wave merge failure | N/A | Roll back to pre-wave checkpoint tag, mark all wave tasks as NEEDS_MANUAL_MERGE |

## Merge Broker vs Commit Broker

| Aspect | Commit Broker (Patch Mode) | Merge Broker (Worktree Mode) |
|--------|---------------------------|------------------------------|
| Input | `.patch` files | Git branches from worktrees |
| Apply method | `git apply --3way` | `git merge --no-ff` |
| Commit message | `rune: {subject} [ward-checked]` | `rune: merge {worker} [worktree]` |
| Conflict handling | Mark NEEDS_MANUAL_MERGE | Escalate to user (interactive) |
| Dedup mechanism | `committedTaskIds` Set | `mergedBranches` Set |
| SHA recording | `commitSHAs[]` | `mergeSHAs[]` |
| Cleanup | N/A (patches are files) | Remove worktree + delete branch |
| When called | After waitForCompletion | Between waves + after final wave |
| File-based commit message | `{taskId}-msg.txt` | `{taskId}-merge-msg.txt` |

## committedFiles Compatibility (GAP-6)

The merge broker must produce a `committedFiles` list compatible with Phase 4.3 (Doc-Consistency) consumers:

```javascript
// After all waves merged, collect all files changed across merge commits
function getCommittedFiles(featureBranch, baseSHA) {
  const files = Bash(`git diff --name-only "${baseSHA}".."${featureBranch}"`).trim()
  return files.split('\n').filter(Boolean)
}
```

This replaces the patch-based `meta.files` collection from commitBroker. The output format is identical: an array of relative file paths.

## Integration Points

- **Phase 0**: `worktreeMode` flag determines which broker is active
- **Phase 1 (Forge Team)**: Wave computation runs after dependency linking (sub-step 5.3 of TaskCreate loop in work.md)
- **Phase 2**: Workers spawned with `isolation: "worktree"` per wave
- **Phase 3**: Wave-aware monitoring loop (monitor current wave, merge, spawn next)
- **Phase 3.5**: `mergeBroker()` replaces `commitBroker()` when `worktreeMode === true`
- **Phase 4**: Ward check runs on merged feature branch (post-merge)
- **Phase 4.3**: `committedFiles` from `getCommittedFiles()` instead of patch metadata
- **Phase 6**: `worktreeGarbageCollection()` added to cleanup sequence
