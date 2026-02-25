---
name: strive
description: |
  Multi-agent work execution using Agent Teams. Parses a plan into tasks,
  summons swarm workers that claim and complete tasks independently,
  and runs quality gates before completion.

  <example>
  user: "/rune:strive plans/feat-user-auth-plan.md"
  assistant: "The Tarnished marshals the Ash to forge the plan..."
  </example>

  <example>
  user: "/rune:strive"
  assistant: "No plan specified. Looking for recent plans..."
  </example>
user-invocable: true
disable-model-invocation: false
argument-hint: "[plan-path] [--approve] [--worktree] [--todos-dir <path>]"
allowed-tools:
  - Task
  - TaskCreate
  - TaskList
  - TaskUpdate
  - TaskGet
  - TeamCreate
  - TeamDelete
  - SendMessage
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
  - AskUserQuestion
---

**Runtime context** (preprocessor snapshot):
- Active workflows: !`ls tmp/.rune-*-*.json 2>/dev/null | grep -c '"active"' || echo 0`
- Current branch: !`git branch --show-current 2>/dev/null || echo "unknown"`

# /rune:strive — Multi-Agent Work Execution

Parses a plan into tasks with dependencies, summons swarm workers, and coordinates parallel implementation.

**Load skills**: `roundtable-circle`, `context-weaving`, `rune-echoes`, `rune-orchestration`, `codex-cli`, `git-worktree` (when worktree mode active), `polling-guard`, `zsh-compat`

## Usage

```
/rune:strive plans/feat-user-auth-plan.md              # Execute a specific plan
/rune:strive plans/feat-user-auth-plan.md --approve    # Require plan approval per task
/rune:strive plans/feat-user-auth-plan.md --worktree   # Use git worktree isolation (experimental)
/rune:strive                                            # Auto-detect recent plan
```

## Pipeline Overview

```
Phase 0: Parse Plan -> Extract tasks, clarify ambiguities, detect --worktree flag
    |
Phase 0.5: Environment Setup -> Branch check, stash dirty files, SDK canary (worktree)
    |
Phase 1: Forge Team -> TeamCreate + TaskCreate pool
    |
Phase 2: Summon Workers -> Self-organizing swarm
    | (workers claim -> implement -> complete -> repeat)
Phase 3: Monitor -> TaskList polling, stale detection
    |
Phase 3.5: Commit/Merge Broker -> Apply patches or merge worktree branches (orchestrator-only)
    |
Phase 3.7: Codex Post-monitor Critique -> Architectural drift detection (optional, non-blocking)
    |
Phase 4: Ward Check -> Quality gates + verification checklist
    |
Phase 4.1: Todo Summary -> Generate _summary.md from per-worker todo files (orchestrator-only)
    |
Phase 4.3: Doc-Consistency -> Non-blocking version/count drift detection (orchestrator-only)
    |
Phase 4.4: Quick Goldmask -> Compare predicted CRITICAL files vs committed (orchestrator-only)
    |
Phase 4.5: Codex Advisory -> Optional plan-vs-implementation review (non-blocking)
    |
Phase 5: Echo Persist -> Save learnings
    |
Phase 6: Cleanup -> Shutdown workers, TeamDelete
    |
Phase 6.5: Ship -> Push + PR creation (optional)
    |
Output: Feature branch with commits + PR (optional)
```

## Phase 0: Parse Plan

See [parse-plan.md](references/parse-plan.md) for detailed task extraction, shard context, ambiguity detection, and user confirmation flow.

**Summary**: Read plan file, validate path, extract tasks with dependencies, classify as impl/test, detect ambiguities, confirm with user.

### Worktree Mode Detection (Phase 0)

Parse `--worktree` flag from `$ARGUMENTS` and read talisman configuration. This follows the same pattern as `--approve` flag parsing.

```javascript
// Parse --worktree flag from $ARGUMENTS (same pattern as --approve)
const args = "$ARGUMENTS"
const worktreeFlag = args.includes("--worktree")

// Read talisman config for worktree default
const talisman = readTalisman()
const worktreeEnabled = talisman?.work?.worktree?.enabled || false

// worktreeMode: flag wins, talisman is fallback default
const worktreeMode = worktreeFlag || worktreeEnabled
```

When `worktreeMode === true`:
- Load `git-worktree` skill for merge strategy knowledge
- Phase 1 computes wave groupings after task extraction (step 5.3)
- Phase 2 spawns workers with `isolation: "worktree"` per wave
- Phase 3 uses wave-aware monitoring loop
- Phase 3.5 uses `mergeBroker()` instead of `commitBroker()`
- Workers commit directly instead of generating patches

## Phase 0.5: Environment Setup

Before forging the team, verify the git environment is safe for work. Checks branch safety (warns on `main`/`master`), handles dirty working trees with stash UX, and validates worktree prerequisites when in worktree mode.

**Skip conditions**: Invoked via `/rune:arc` (arc handles COMMIT-1), or `work.skip_branch_check: true` in talisman.

See [env-setup.md](references/env-setup.md) for the full protocol — branch check, dirty tree detection, stash UX, and worktree validation.

## Phase 1: Forge Team

```javascript
// Pre-create guard: teamTransition protocol (see team-lifecycle-guard.md)
// STEP 1: Validate (defense-in-depth)
if (!/^[a-zA-Z0-9_-]+$/.test(timestamp)) throw new Error("Invalid work identifier")
if (timestamp.includes('..')) throw new Error('Path traversal detected in work identifier')

// STEP 2: TeamDelete with retry-with-backoff (3 attempts: 0s, 3s, 8s)
// STEP 3: Filesystem fallback (only when STEP 2 failed)
// STEP 4: TeamCreate with "Already leading" catch-and-recover
// STEP 5: Post-create verification

// Create signal directory for event-driven sync
const signalDir = `tmp/.rune-signals/rune-work-${timestamp}`
Bash(`mkdir -p "${signalDir}" && find "${signalDir}" -mindepth 1 -delete`)
Write(`${signalDir}/.expected`, String(extractedTasks.length))
Write(`${signalDir}/inscription.json`, JSON.stringify({
  workflow: "rune-work",
  timestamp: timestamp,
  output_dir: `tmp/work/${timestamp}/`,
  teammates: [
    { name: "rune-smith", output_file: "work-summary.md" },
    { name: "trial-forger", output_file: "work-summary.md" }
  ]
}))

// Create output directories
Bash(`mkdir -p "tmp/work/${timestamp}/patches" "tmp/work/${timestamp}/proposals" "tmp/work/${timestamp}/todos"`)

// Per-task file-todos: create source-qualified todos directory
// See file-todos/references/integration-guide.md for resolveTodosDir() contract
const talisman = readTalisman()
const todosDir = resolveTodosDir($ARGUMENTS, talisman, "work")
//   standalone: "todos/work/"
//   arc (--todos-dir tmp/arc/{id}/todos/): "tmp/arc/{id}/todos/work/"
Bash(`mkdir -p "${todosDir}"`)


// Compute total worker count (scaling logic in worker-prompts.md)
const workerCount = smithCount + forgerCount

// Write state file with session identity for cross-session isolation
const configDir = Bash(`cd "\${CLAUDE_CONFIG_DIR:-$HOME/.claude}" 2>/dev/null && pwd -P`).trim()
const ownerPid = Bash(`echo $PPID`).trim()
Write("tmp/.rune-work-{timestamp}.json", {
  team_name: "rune-work-{timestamp}",
  started: new Date().toISOString(),
  status: "active",
  config_dir: configDir,
  owner_pid: ownerPid,
  session_id: "${CLAUDE_SESSION_ID}",
  plan: planPath,
  expected_workers: workerCount,
  ...(worktreeMode && { worktree_mode: true, waves: [], current_wave: 0, merged_branches: [] })
})
```

### File Ownership and Task Pool

1. Extract file targets (`fileTargets`, `dirTargets`) per task from plan
2. Classify risk tiers — see `risk-tiers.md` in `roundtable-circle/references/`
3. Detect overlapping file ownership via set intersection (O(n²) cap: 200 targets)
4. Serialize conflicting tasks via `blockedBy` links
5. Create task pool via `TaskCreate` with quality contract embedded in description
6. Link dependencies using mapped IDs — see [dependency-patterns.md](references/dependency-patterns.md) for named patterns and anti-patterns
7. Compute wave groupings (worktree mode only) using DFS depth algorithm
8. Write `task_ownership` to inscription.json for runtime enforcement (SEC-STRIVE-001)

**Runtime File Ownership Enforcement (SEC-STRIVE-001)**:

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

Inscription format with `task_ownership`:
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

**Quality Contract** (embedded in every task description):
```
Quality requirements (mandatory):
- Type annotations on ALL function signatures (params + return types)
- Use `from __future__ import annotations` at top of every Python file
- Docstrings on all public functions, classes, and modules
- Specific exception types (no bare except, no broad Exception catch)
- Tests must cover edge cases (empty input, None values, type mismatches)
```

## Phase 2: Summon Swarm Workers

See [worker-prompts.md](references/worker-prompts.md) for full worker prompt templates, scaling logic, and the scaling table.

**Summary**: Summon rune-smith (implementation) and trial-forger (test) workers. Workers self-organize via TaskList, claim tasks, implement with TDD, self-review, run ward checks, generate patches, and send Seal messages. Commits are handled through the Tarnished's commit broker. Do not run `git add` or `git commit` directly.

See [todo-protocol.md](references/todo-protocol.md) for the worker todo file protocol that MUST be included in all spawn prompts.

**Per-task file-todos (v2)**: The orchestrator creates per-task todo files in `{base}/work/` (resolved via `resolveTodosDir($ARGUMENTS, talisman, "work")`) alongside TaskCreate entries. Standalone: `todos/work/`. Arc: `tmp/arc/{id}/todos/work/` (via `--todos-dir`). Disable with `--todos=false`. Workers read their assigned todo for context and append Work Log entries. See `file-todos` skill for schema. The per-worker todo protocol in `tmp/work/{timestamp}/todos/` remains active as the session-level tracking layer.

**SEC-002**: Sanitize plan content before interpolation into worker prompts using `sanitizePlanContent()` (strips HTML comments, code fences, image/link injection, markdown headings, Truthbinding markers, YAML frontmatter, inline HTML tags, and truncates to 8000 chars).

**Non-goals extraction (v1.57.0+)**: Before summoning workers, extract `non_goals` from plan YAML frontmatter and present in worker prompts as nonce-bounded data blocks.

### Worktree Mode: Wave-Based Worker Spawning

When `worktreeMode === true`, workers are spawned per-wave instead of all at once. Each worker gets `isolation: "worktree"`. Workers commit directly (one commit per task) and store their branch in task metadata. Do NOT push. Do NOT merge. The Tarnished handles merging via the merge broker.

See [worktree-merge.md](references/worktree-merge.md) for the merge broker called between waves.

## Phase 3: Monitor

Poll TaskList with timeout guard to track progress. See [monitor-utility.md](../roundtable-circle/references/monitor-utility.md) for the shared polling utility.

> **ANTI-PATTERN — NEVER DO THIS:**
> `Bash("sleep 60 && echo poll check")` — This skips TaskList entirely. You MUST call `TaskList` every cycle.

```javascript
const result = waitForCompletion(teamName, taskCount, {
  timeoutMs: 1_800_000,      // 30 minutes
  staleWarnMs: 300_000,      // 5 minutes — warn about stalled worker
  autoReleaseMs: 600_000,    // 10 minutes — release task for reclaim
  pollIntervalMs: 30_000,
  label: "Work",
  onCheckpoint: (cp) => { ... }
})
```

**Wave-aware monitoring (worktree mode)**: Sequential waves, each monitored independently via `waitForCompletion` with `taskFilter`, merge broker runs between waves. Per-wave timeout: 10 minutes.

### Phase 3.5: Commit Broker (Orchestrator-Only, Patch Mode)

The Tarnished is the **sole committer** — workers generate patches, the orchestrator applies and commits them. Serializes all git index operations through a single writer, eliminating `.git/index.lock` contention.

Key steps: validate patch path, read patch + metadata, skip empty patches, dedup by taskId, apply with `--3way` fallback, reset staging area, stage specific files via `--pathspec-from-file`, commit with `-F` message file.

**Recovery on restart**: Scan `tmp/work/{timestamp}/patches/` for metadata JSON with no recorded commit SHA — re-apply unapplied patches.

### Phase 3.5: Merge Broker (Worktree Mode, Orchestrator-Only)

Replaces the commit broker when `worktreeMode === true`. Called between waves. See [worktree-merge.md](references/worktree-merge.md) for the complete algorithm, conflict resolution flow, and cleanup procedures.

Key guarantees: sorted by task ID for deterministic merge order, dedup guard, `--no-ff` merge, file-based commit message, escalate conflicts to user via `AskUserQuestion` (NEVER auto-resolve), worktree cleanup on completion.

### Phase 3.7: Codex Post-monitor Architectural Critique (Optional, Non-blocking)

After all workers complete and the commit/merge broker finishes, optionally run Codex to detect architectural drift between committed code and the plan. Non-blocking, opt-in via `codex.post_monitor_critique.enabled`.

**Skip conditions**: Codex unavailable, `codex.disabled`, feature not enabled, `work` not in `codex.workflows`, or `total_worker_commits <= 3`.

See [codex-post-monitor.md](references/codex-post-monitor.md) for the full protocol — feature gate, nonce-bounded prompt injection, codex-exec.sh invocation, error classification, and ward check integration.

## Phase 4: Quality Gates

Read and execute [quality-gates.md](references/quality-gates.md) before proceeding.

**Phase 4 — Ward Check**: Discover wards from Makefile/package.json/pyproject.toml, execute each with SAFE_WARD validation, run 10-point verification checklist. On ward failure, create fix task and summon worker.

**Phase 4.1 — Todo Summary**: Orchestrator generates `todos/_summary.md` after all workers exit. See [todo-protocol.md](references/todo-protocol.md) for full algorithm. Also updates per-task todo frontmatter status to `complete` for finished tasks and `blocked` for failed tasks. Scans `resolveTodosDir($ARGUMENTS, talisman, "work")` only (not other source subdirectories).

**Phase 4.3 — Doc-Consistency**: Non-blocking version/count drift detection. See `doc-consistency.md` in `roundtable-circle/references/`.

**Phase 4.4 — Quick Goldmask**: Compare plan-time CRITICAL file predictions against committed files. Emits WARNINGs only. Non-blocking.

**Phase 4.5 — Codex Advisory**: Optional plan-vs-implementation review via `codex exec`. INFO-level findings only. Talisman kill switch: `codex.work_advisory.enabled: false`.

## Phase 5: Echo Persist

```javascript
if (exists(".claude/echoes/workers/")) {
  appendEchoEntry(".claude/echoes/workers/MEMORY.md", {
    layer: "inscribed",
    source: `rune:strive ${timestamp}`,
  })
}
```

## Phase 6: Cleanup & Report

```javascript
// 0. Cache task list BEFORE team cleanup (TaskList() requires active team)
const allTasks = TaskList()

// 1. Dynamic member discovery — reads team config to find ALL teammates
// 2. Send shutdown_request to all members
// 2.5. Grace period — sleep 15s to let teammates deregister before TeamDelete
// 3. Cleanup team with retry-with-backoff (3 attempts: 0s, 5s, 10s)
//    Total budget: 15s grace + 15s retry = 30s max
//    Filesystem fallback when TeamDelete fails
// 3.5: Fix stale todo file statuses (FLAW-008 — active → interrupted)
// 3.55: Per-task file-todos cleanup:
//       Scope to resolveTodosDir($ARGUMENTS, talisman, "work") — work/ subdirectory only
//       Filter by work_session == timestamp (session isolation)
//       Mark in_progress todos as interrupted for this session's tasks
// 3.6: Worktree garbage collection (worktree mode only)
//      git worktree prune + remove orphaned worktrees matching rune-work-*
// 3.7: Restore stashed changes if Phase 0.5 stashed (git stash pop)
// 4. Update state file to completed (preserve session identity fields)
```

## Phase 6.5: Ship (Optional)

See [ship-phase.md](references/ship-phase.md) for gh CLI pre-check, ship decision flow, PR template generation, and smart next steps.

**Summary**: Offer to push branch and create PR. Generates PR body from plan metadata, task list, ward results, verification warnings, and todo summary. See [todo-protocol.md](references/todo-protocol.md) for PR body Work Session format. The PR body also includes a file-todos status table sourced from `resolveTodosDir($ARGUMENTS, talisman, "work")` (counts by status/priority). Suppressed when `--todos=false`.

### Completion Report

```
The Tarnished has claimed the Elden Throne.

Plan: {planPath}
Branch: {currentBranch}

Tasks: {completed}/{total}
Workers: {smith_count} Rune Smiths, {forger_count} Trial Forgers
Wards: {passed}/{total} passed
Commits: {commit_count}
Time: {duration}

Files changed:
- {file list with change summary}

Artifacts: tmp/work/{timestamp}/
```

## --approve Flag (Plan Approval Per Task)

When `--approve` is set, each worker proposes an implementation plan before coding.

**Flow**: Worker reads task → writes proposal to `tmp/work/{timestamp}/proposals/{task-id}.md` → sends to leader → leader presents via `AskUserQuestion` → user approves/rejects/skips → max 2 rejection cycles → timeout 3 minutes → auto-REJECT (fail-closed).

**Proposal format**: Markdown with `## Approach`, `## Files to Modify`, `## Files to Create`, `## Risks` sections.

**Arc integration**: When used via `/rune:arc --approve`, the flag applies ONLY to Phase 5 (WORK), not to Phase 7 (MEND).

## Incremental Commits

Each task produces exactly one commit via the commit broker: `rune: <task-subject> [ward-checked]`.

Task subjects are sanitized: strip newlines + control chars, limit to 72 chars, use `git commit -F <message-file>` (not inline `-m`).

Only the Tarnished (orchestrator) updates plan checkboxes — workers do not edit the plan file.

## Key Principles

### For the Tarnished (Orchestrator)

- **Ship complete features**: Verify wards pass, plan checkboxes are checked, and offer to create a PR.
- **Fail fast on ambiguity**: Ask clarifying questions in Phase 0, not after workers have started implementing.
- **Branch safety first**: Do not let workers commit to `main` without explicit user confirmation.
- **Serialize git operations**: All commits go through the commit broker.

### For Workers (Rune Smiths & Trial Forgers)

- **Match existing patterns**: Read similar code before writing new code.
- **Test as you go**: Run wards after each task, not just at the end. Fix failures immediately.
- **One task, one patch**: Each task produces exactly one patch.
- **Self-review before ward**: Re-read every changed file before running quality gates.
- **Exit cleanly**: No tasks after 3 retries → idle notification → exit. Approve shutdown requests immediately.

## Error Handling

| Error | Recovery |
|-------|----------|
| Worker stalled (>5 min) | Warn lead, release after 10 min |
| Total timeout (>30 min) | Final sweep, collect partial results, commit applied patches |
| Worker crash | Task returns to pool for reclaim |
| Ward failure | Create fix task, summon worker to fix |
| All workers crash | Abort, report partial progress |
| Plan has no extractable tasks | Ask user to restructure plan |
| Conflicting file edits | File ownership serializes via blockedBy; commit broker handles residual conflicts |
| Empty patch (worker reverted) | Skip commit, log as "completed-no-change" |
| Patch conflict (two workers on same file) | `git apply --3way` fallback; mark NEEDS_MANUAL_MERGE on failure |
| `git push` failure (Phase 6.5) | Warn user, skip PR creation, show manual push command |
| `gh pr create` failure (Phase 6.5) | Warn user (branch was pushed), show manual command |
| Detached HEAD state | Abort with error — require user to checkout a branch first |
| `git stash push` failure (Phase 0.5) | Warn and continue with dirty tree |
| `git stash pop` failure (Phase 6) | Warn user — manual restore needed: `git stash list` |
| Merge conflict (worktree mode) | Escalate to user via AskUserQuestion — never auto-resolve |
| Worker crash in worktree | Worktree cleaned up on Phase 6, task returned to pool |
| Orphaned worktrees (worktree mode) | Phase 6 garbage collection: `git worktree prune` + force removal |

## Common Pitfalls

| Pitfall | Prevention |
|---------|------------|
| Committing to `main` | Phase 0.5 branch check (fail-closed) |
| Building wrong thing from ambiguous plan | Phase 0 clarification sub-step |
| 80% done syndrome | Phase 6.5 ship phase |
| Over-reviewing simple changes | Review guidance heuristic in completion report |
| Workers editing same files | File ownership conflict detection (Phase 1, step 5.1) serializes via blockedBy |
| Stale worker blocking pipeline | Stale detection (5 min warn, 10 min auto-release) |
| Ward failure cascade | Auto-create fix task, summon fresh worker |
| Dirty working tree conflicts | Phase 0.5 stash check |
| `gh` CLI not installed | Pre-check with fallback to manual instructions |
| Partial file reads | Step 5: "Read FULL target files" |
| Fixes that introduce new bugs | Step 6.5: Self-review checklist |
