---
name: rune:work
description: |
  Multi-agent work execution using Agent Teams. Parses a plan into tasks,
  summons swarm workers that claim and complete tasks independently,
  and runs quality gates before completion.

  <example>
  user: "/rune:work plans/feat-user-auth-plan.md"
  assistant: "The Tarnished marshals the Ash to forge the plan..."
  </example>

  <example>
  user: "/rune:work"
  assistant: "No plan specified. Looking for recent plans..."
  </example>
user-invocable: true
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

# /rune:work — Multi-Agent Work Execution

Parses a plan into tasks with dependencies, summons swarm workers, and coordinates parallel implementation.

**Load skills**: `context-weaving`, `rune-echoes`, `rune-orchestration`

## Usage

```
/rune:work plans/feat-user-auth-plan.md              # Execute a specific plan
/rune:work plans/feat-user-auth-plan.md --approve    # Require plan approval per task
/rune:work                                            # Auto-detect recent plan
```

## Pipeline Overview

```
Phase 0: Parse Plan → Extract tasks with dependencies
    ↓
Phase 1: Forge Team → TeamCreate + TaskCreate pool
    ↓
Phase 2: Summon Workers → Self-organizing swarm
    ↓ (workers claim → implement → complete → repeat)
Phase 3: Monitor → TaskList polling, stale detection
    ↓
Phase 4: Ward Check → Project quality gates
    ↓
Phase 5: Echo Persist → Save learnings
    ↓
Output: Implemented feature with commits
```

## Phase 0: Parse Plan

### Find Plan

If no plan specified:
```bash
# Look for recent plans
ls -t plans/*.md 2>/dev/null | head -5
```

If multiple found, ask user which to execute. If none found, suggest `/rune:plan` first.

### Extract Tasks

Read the plan and extract implementation tasks:

1. Look for checkbox items (`- [ ]`), numbered lists, or "Tasks" sections
2. Identify dependencies between tasks (Phase ordering, explicit "depends on" references)
3. Classify each task:
   - **Implementation task**: Writing code (assigned to rune-smith)
   - **Test task**: Writing tests (assigned to trial-forger)
   - **Independent**: Can run in parallel
   - **Sequential**: Must wait for dependencies

```javascript
// Example task extraction
tasks = [
  { subject: "Write User model", type: "impl", blockedBy: [] },
  { subject: "Write User model tests", type: "test", blockedBy: [] },
  { subject: "Write UserService", type: "impl", blockedBy: ["#1"] },
  { subject: "Write UserService tests", type: "test", blockedBy: ["#3"] },
  { subject: "Write API routes", type: "impl", blockedBy: ["#3"] },
  { subject: "Write API route tests", type: "test", blockedBy: ["#5"] },
]
```

### Confirm with User

Present extracted tasks and ask for confirmation:

```
Extracted {N} tasks from plan:

Implementation:
  1. Write User model
  3. Write UserService (depends on #1)
  5. Write API routes (depends on #3)

Tests:
  2. Write User model tests
  4. Write UserService tests (depends on #3)
  6. Write API route tests (depends on #5)

Proceed with {N} tasks and {W} workers?
```

## Phase 1: Forge Team

```javascript
// 1. Pre-create guard: cleanup stale team if exists (see team-lifecycle-guard.md)
// Validate identifier before rm -rf
if (!/^[a-zA-Z0-9_-]+$/.test(timestamp)) throw new Error("Invalid work identifier")
try { TeamDelete() } catch (e) {
  Bash("rm -rf ~/.claude/teams/rune-work-{timestamp}/ ~/.claude/tasks/rune-work-{timestamp}/ 2>/dev/null")
}
TeamCreate({ team_name: "rune-work-{timestamp}" })

// 2. Create output directories
Bash(`mkdir -p "tmp/work/${timestamp}/patches" "tmp/work/${timestamp}/proposals"`)

// 3. Write state file
Write("tmp/.rune-work-{timestamp}.json", {
  team_name: "rune-work-{timestamp}",
  started: new Date().toISOString(),
  status: "active",
  plan: planPath,
  expected_workers: workerCount
})

// 4. Generate inscription.json (see roundtable-circle/references/inscription-schema.md)
Write(`tmp/work/${timestamp}/inscription.json`, {
  workflow: "rune-work",
  timestamp: timestamp,
  plan: planPath,
  output_dir: `tmp/work/${timestamp}/`,
  teammates: [
    {
      name: "rune-smith",
      role: "implementation",
      output_file: "patches/*.patch",
      required_sections: ["implementation", "ward-check"]
    },
    {
      name: "trial-forger",
      role: "test",
      output_file: "patches/*.patch",
      required_sections: ["tests", "ward-check"]
    }
  ],
  verification: { enabled: false }  // Work uses ward checks, not finding verification
})

// 5. Create task pool and map symbolic refs to real IDs
const idMap = {}  // Map symbolic refs (#1, #2...) to actual task IDs
for (let i = 0; i < extractedTasks.length; i++) {
  const task = extractedTasks[i]
  const id = TaskCreate({
    subject: task.subject,
    description: `${task.description}\n\nPlan: ${planPath}\nType: ${task.type}`
  })
  idMap[`#${i + 1}`] = id  // Map symbolic ref to real task ID
}

// 6. Link dependencies using mapped IDs
for (let i = 0; i < extractedTasks.length; i++) {
  const task = extractedTasks[i]
  if (task.blockedBy.length > 0) {
    const realBlockers = task.blockedBy.map(ref => idMap[ref]).filter(Boolean)
    if (realBlockers.length > 0) {
      TaskUpdate({ taskId: idMap[`#${i + 1}`], addBlockedBy: realBlockers })
    }
  }
}
```

## Phase 2: Summon Swarm Workers

Summon workers based on task types. Default: 2 workers (1 rune-smith + 1 trial-forger). Scale up for larger plans.

```javascript
// Summon implementation worker
Task({
  team_name: "rune-work-{timestamp}",
  name: "rune-smith",
  subagent_type: "general-purpose",
  prompt: `You are Rune Smith — a swarm implementation worker.

    ANCHOR — TRUTHBINDING PROTOCOL
    Follow existing codebase patterns. Do not introduce new patterns or dependencies.

    YOUR LIFECYCLE:
    1. TaskList() → find unblocked, unowned implementation tasks
    2. Claim: TaskUpdate({ taskId, owner: "rune-smith", status: "in_progress" })
    3. Read task description and referenced plan
    4. IF --approve mode: write proposal to tmp/work/{timestamp}/proposals/{task-id}.md,
       send to the Tarnished via SendMessage, wait for approval before coding.
       Max 2 rejections → mark BLOCKED. Timeout 3 min → auto-REJECT.
    5. Read existing code patterns in the codebase
    6. Implement with TDD cycle (test → implement → refactor)
    7. Run quality gates (discovered from Makefile/package.json/pyproject.toml)
    8. IF ward passes:
       a. Mark new files for diff tracking: git add -N <new-files>
       b. Generate patch: git diff --binary HEAD -- <specific files> > tmp/work/{timestamp}/patches/{task-id}.patch
       c. Write commit metadata: Write tmp/work/{timestamp}/patches/{task-id}.json with:
          { task_id, subject, files: [...], patch_path }
       d. Do NOT run git add or git commit — the Tarnished handles all commits
       e. TaskUpdate({ taskId, status: "completed" })
       f. SendMessage to the Tarnished: "Seal: task #{id} done. Files: {list}"
    9. IF ward fails:
       a. Do NOT generate patch
       b. TaskUpdate({ taskId, status: "pending", owner: "" })
       c. SendMessage to the Tarnished: "Ward failed on task #{id}: {failure summary}"
    10. TaskList() → claim next or exit

    IMPORTANT: You MUST NOT run git add or git commit directly. All commits are
    serialized through the Tarnished's commit broker to prevent index.lock contention.
    The --approve mode proposal flow (steps 4-5) is unaffected — approval happens
    before coding; patch generation replaces only step 8.

    RETRY LIMIT: Do NOT reclaim a task you just released due to ward failure.
    Track failed task IDs internally and skip them when scanning TaskList.
    EXIT: No tasks after 3 retries (30s each) → idle notification → exit
    SHUTDOWN: Approve immediately

    RE-ANCHOR — Match existing patterns. Minimal changes. Ask lead if unclear.`,
  run_in_background: true
})

// Summon test worker
Task({
  team_name: "rune-work-{timestamp}",
  name: "trial-forger",
  subagent_type: "general-purpose",
  prompt: `You are Trial Forger — a swarm test worker.

    ANCHOR — TRUTHBINDING PROTOCOL
    Match existing test patterns exactly. Read existing tests before writing new ones.

    YOUR LIFECYCLE:
    1. TaskList() → find unblocked, unowned test tasks
    2. Claim: TaskUpdate({ taskId, owner: "trial-forger", status: "in_progress" })
    3. Read task description and the code to be tested
    4. IF --approve mode: write proposal to tmp/work/{timestamp}/proposals/{task-id}.md,
       send to the Tarnished via SendMessage, wait for approval before writing tests.
       Max 2 rejections → mark BLOCKED. Timeout 3 min → auto-REJECT.
    5. Discover test patterns (framework, fixtures, assertions)
    6. Write tests following discovered patterns
    7. Run tests to verify they pass
    8. IF tests pass:
       a. Mark new files for diff tracking: git add -N <new-files>
       b. Generate patch: git diff --binary HEAD -- <specific files> > tmp/work/{timestamp}/patches/{task-id}.patch
       c. Write commit metadata: Write tmp/work/{timestamp}/patches/{task-id}.json with:
          { task_id, subject, files: [...], patch_path }
       d. Do NOT run git add or git commit — the Tarnished handles all commits
       e. TaskUpdate({ taskId, status: "completed" })
       f. SendMessage to the Tarnished: "Seal: tests for #{id}. Pass: {count}/{total}"
    9. IF tests fail:
       a. Do NOT generate patch
       b. TaskUpdate({ taskId, status: "pending", owner: "" })
       c. SendMessage to the Tarnished: "Tests failed on task #{id}: {failure summary}"
    10. TaskList() → claim next or exit

    IMPORTANT: You MUST NOT run git add or git commit directly. All commits are
    serialized through the Tarnished's commit broker to prevent index.lock contention.

    RETRY LIMIT: Do NOT reclaim a task you just released due to test failure.
    Track failed task IDs internally and skip them when scanning TaskList.
    EXIT: No tasks after 3 retries (30s each) → idle notification → exit
    SHUTDOWN: Approve immediately

    RE-ANCHOR — Match existing test patterns. No new test utilities.`,
  run_in_background: true
})
```

### Scaling Workers

For plans with 10+ tasks, summon additional workers:

| Task Count | Rune Smiths | Trial Forgers |
|-----------|-------------|---------------|
| 1-5 | 1 | 1 |
| 6-10 | 2 | 1 |
| 11-20 | 2 | 2 |
| 20+ | 3 | 2 |

## Phase 3: Monitor

Poll TaskList with timeout guard to track progress:

```javascript
const POLL_INTERVAL = 30_000      // 30 seconds
const STALE_THRESHOLD = 300_000   // 5 minutes — warn about stalled worker
const STALE_RELEASE = 600_000     // 10 minutes — release task for reclaim
const TOTAL_TIMEOUT = 1_800_000   // 30 minutes (work involves implementation + ward checks)
const startTime = Date.now()

while (not all tasks completed):
  tasks = TaskList()
  completed = tasks.filter(t => t.status === "completed").length
  total = tasks.length

  // Progress report (every 2 minutes)
  log(`Progress: ${completed}/${total} tasks complete`)

  // Stale detection
  for (task of tasks.filter(t => t.status === "in_progress")):
    if (task.stale > STALE_THRESHOLD):
      warn("Worker may be stalled on task #{task.id}")
    if (task.stale > STALE_RELEASE):
      TaskUpdate({ taskId: task.id, owner: "", status: "pending" })

  // Commit broker: process completed task patches (see Phase 3.5)

  // Total timeout
  if (Date.now() - startTime > TOTAL_TIMEOUT):
    warn("Work timeout reached (30 min). Collecting partial results.")
    break

  sleep(POLL_INTERVAL)

// Final sweep: re-read TaskList once more before reporting timeout
tasks = TaskList()
```

**Total timeout**: Hard limit of 30 minutes (work legitimately takes longer due to implementation + ward checks). After timeout, a final sweep collects any results that completed during the last poll interval.

### Phase 3.5: Commit Broker (Orchestrator-Only)

The Tarnished is the **sole committer** — workers generate patches, the orchestrator applies and commits them. This serializes all git index operations through a single writer, eliminating `.git/index.lock` contention entirely.

```javascript
// On receiving "Seal: task #{id} done" from worker:
function commitBroker(taskId) {
  const patchPath = `tmp/work/${timestamp}/patches/${taskId}.patch`
  const metaPath = `tmp/work/${timestamp}/patches/${taskId}.json`

  // 1. Validate patch path
  if (!patchPath.match(/^tmp\/work\/\d+\/patches\/[\w-]+\.patch$/)) {
    warn(`Invalid patch path for task ${taskId}`)
    return
  }

  // 2. Read patch and metadata
  const patchContent = Read(patchPath)
  const meta = Read(metaPath)

  // 3. Skip empty patches (worker reverted own changes)
  if (patchContent.trim() === "") {
    log(`Task ${taskId}: completed-no-change (empty patch)`)
    return
  }

  // 4. Deduplicate: reject if taskId already committed
  if (committedTaskIds.has(taskId)) {
    warn(`Task ${taskId}: duplicate Seal — already committed`)
    return
  }

  // 5. Apply with 3-way merge fallback
  result = Bash(`git apply --3way "${patchPath}"`)
  if (result.exitCode !== 0) {
    warn(`Task ${taskId}: patch conflict — marking NEEDS_MANUAL_MERGE`)
    return
  }

  // 6. Validate and stage files
  // SECURITY: Validate each file path against safe character set to prevent shell injection
  const SAFE_PATH = /^[a-zA-Z0-9._\-\/]+$/
  for (const file of meta.files) {
    if (!SAFE_PATH.test(file)) {
      warn(`Task ${taskId}: unsafe file path "${file}" — skipping`)
      return
    }
  }
  // Quote each path individually for shell safety (SAFE_PATH already rejects spaces)
  Bash(`git add ${meta.files.map(f => `"${f}"`).join(' ')}`)
  // Sanitize commit subject: strip control chars, limit length, write to file (not -m)
  const safeSubject = meta.subject.replace(/[^a-zA-Z0-9 ._\-:()]/g, '').slice(0, 72)
  Write(`tmp/work/${timestamp}/patches/${taskId}-msg.txt`,
    `rune: ${safeSubject} [ward-checked]`)
  Bash(`git commit -F "tmp/work/${timestamp}/patches/${taskId}-msg.txt"`)

  // 7. Record commit SHA
  const sha = Bash("git rev-parse HEAD").trim()
  committedTaskIds.add(taskId)
  commitSHAs.push(sha)

  // 8. Update plan checkboxes (existing single-writer pattern)
}
```

**Recovery on restart**: Scan `tmp/work/{timestamp}/patches/` for metadata JSON with no recorded commit SHA → re-apply unapplied patches.

## Phase 4: Ward Check

After all tasks complete, run project-wide quality gates:

```javascript
// Discover wards
wards = discoverWards()
// Possible sources: Makefile, package.json, pyproject.toml, talisman.yml

// SECURITY: Validate ward commands — block shell metacharacters from talisman.yml commands
const SAFE_WARD = /^[a-zA-Z0-9._\-\/ ]+$/
for (const ward of wards) {
  if (!SAFE_WARD.test(ward.command)) {
    warn(`Ward "${ward.name}": command contains unsafe characters — skipping`)
    warn(`  Blocked command: ${ward.command.slice(0, 80)}`)
    continue
  }
  result = Bash(ward.command)
  if (result.exitCode !== 0) {
    warn(`Ward failed: ${ward.name}`)
    // Create fix task if ward fails
    TaskCreate({ subject: `Fix ${ward.name} failure`, description: result.output })
    // Summon worker to fix
  }
}
```

### Ward Discovery Protocol

```
1. Makefile → targets: check, test, lint, format
2. package.json → scripts: test, lint, typecheck, build
3. pyproject.toml → [tool.ruff], [tool.mypy], [tool.pytest]
4. Cargo.toml → cargo test, cargo clippy
5. go.mod → go test, go vet
6. .claude/talisman.yml → ward_commands override
7. Fallback: skip wards, warn user
```

## Phase 5: Echo Persist

```javascript
if (exists(".claude/echoes/workers/")) {
  // Persist implementation patterns discovered during work
  appendEchoEntry(".claude/echoes/workers/MEMORY.md", {
    layer: "inscribed",
    source: `rune:work ${timestamp}`,
    // ... patterns, gotchas, quality gate results
  })
}
```

## Phase 6: Cleanup & Report

```javascript
// 1. Shutdown all workers
for (const worker of allWorkers) {
  SendMessage({ type: "shutdown_request", recipient: worker })
}

// 2. Wait for approvals (max 30s)

// 3. Cleanup team with fallback (see team-lifecycle-guard.md)
// timestamp validated at Phase 1: /^[a-zA-Z0-9_-]+$/
try { TeamDelete() } catch (e) {
  Bash("rm -rf ~/.claude/teams/rune-work-{timestamp}/ ~/.claude/tasks/rune-work-{timestamp}/ 2>/dev/null")
}

// 4. Update state file to completed
Write("tmp/.rune-work-{timestamp}.json", {
  team_name: "rune-work-{timestamp}",
  started: startTimestamp,
  status: "completed",
  completed: new Date().toISOString(),
  plan: planPath,
  expected_workers: workerCount
})

// 5. Report to user
```

### Completion Report

```
⚔ The Tarnished has claimed the Elden Throne.

Tasks: {completed}/{total}
Workers: {smith_count} Rune Smiths, {forger_count} Trial Forgers
Wards: {passed}/{total} passed
Commits: {commit_count}

Files changed:
- {file list with change summary}

Next steps:
1. /rune:review — Review the implementation
2. git push — Push to remote
3. Create PR
```

## Error Handling

| Error | Recovery |
|-------|----------|
| Worker stalled (>5 min) | Warn lead, release after 10 min |
| Total timeout (>30 min) | Final sweep, collect partial results, commit applied patches |
| Worker crash | Task returns to pool for reclaim |
| Ward failure | Create fix task, summon worker to fix |
| All workers crash | Abort, report partial progress |
| Plan has no extractable tasks | Ask user to restructure plan |
| Conflicting file edits | Workers write to separate files; lead resolves conflicts |
| Empty patch (worker reverted own changes) | Skip commit, log as "completed-no-change" |
| Patch conflict (two workers on same file) | `git apply --3way` fallback; mark NEEDS_MANUAL_MERGE on failure |

## --approve Flag (Plan Approval Per Task)

When `--approve` is set, each worker must propose an implementation plan before coding. This provides a genuine safety gate routed to the **human user**.

### Approval Flow

```
For each task when --approve is active:
  1. Worker reads task, proposes implementation plan
  2. Worker writes proposal to tmp/work/{timestamp}/proposals/{task-id}.md
  3. Worker sends plan to leader via SendMessage
  4. Leader presents to user via AskUserQuestion:
     - Full file path to the proposal
     - Complete list of files the worker intends to modify
     - Options: Approve / Reject with feedback / Skip task
  5. User responds:
     - Approve → worker proceeds with implementation
     - Reject with feedback → worker revises plan, re-proposes
     - Skip → task marked SKIPPED, worker moves to next
  6. Max 2 rejection cycles per task, then mark BLOCKED (do NOT auto-skip)
  7. Timeout: 3 minutes → auto-REJECT with warning (fail-closed, not fail-open)
```

### Proposal File Format

Workers write proposals to `tmp/work/{timestamp}/proposals/{task-id}.md`:

```markdown
# Proposal: {task-subject}

## Approach
{description of implementation approach}

## Files to Modify
- path/to/file1.ts — {what changes}
- path/to/file2.ts — {what changes}

## Files to Create
- path/to/new-file.ts — {purpose}

## Risks
- {any risks or trade-offs}
```

### Integration with Arc

When used via `/rune:arc --approve`, the flag applies **only to Phase 3 (WORK)**, not to Phase 5 (MEND).

## Incremental Commits (E5)

After each task completion, workers commit their work incrementally. This provides atomic, traceable commits per task.

### Commit Lifecycle (via Commit Broker)

```
After each task completion:
  1. Worker implements task
  2. Ward checks run (project quality gates)
  3. If ward passes:
     - Worker generates patch: git diff --binary HEAD -- <files> > patches/{task-id}.patch
     - Worker writes metadata: patches/{task-id}.json
     - Worker sends Seal to Tarnished
     - Tarnished commit broker applies patch, stages, and commits
     - Tarnished updates plan checkboxes
     - Worker continues to next task
  4. If ward fails:
     - Worker does NOT generate patch
     - Worker flags task for review
     - Worker continues to next task (other tasks may be independent)
```

**Why a commit broker?** With up to 5 parallel workers (3 Rune Smiths + 2 Trial Forgers), direct `git add`/`git commit` from workers causes `.git/index.lock` contention. The broker serializes only the fast commit step (sub-second) — worker parallelism is unaffected.

### Commit Message Format

```
rune: <task-subject> [ward-checked]
```

- Example: `rune: Add input validation to login form [ward-checked]`
- Prefix `rune:` makes commits identifiable as machine-generated
- `[ward-checked]` indicates automated quality gate passed (pre-review, not pre-approved)

### Commit Message Sanitization

Task subjects MUST be sanitized before inclusion in commit messages:
- Strip newlines and control characters
- Limit to 72 characters
- Escape shell metacharacters
- Use `git commit -F <message-file>` (not inline `-m`) to avoid shell injection

### Plan Checkbox Updates (Orchestrator-Only)

To prevent race conditions when multiple workers modify the same plan file concurrently,
**only the Tarnished (orchestrator) updates plan checkboxes** — workers MUST NOT edit the plan file.

When the orchestrator receives a "Seal: task done" message from a worker:
1. Read the plan file
2. Find matching task line (fuzzy match on task subject from the completed task)
3. Update `- [ ]` to `- [x]`
4. Write updated plan file

This serializes all plan file writes through a single writer, eliminating read-modify-write races.

When invoked via `/rune:arc` (Phase 3), the work sub-orchestrator (team lead of the work team) handles checkbox updates — not the arc-level orchestrator.
