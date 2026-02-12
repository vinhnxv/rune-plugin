---
name: rune:work
description: |
  Multi-agent work execution using Agent Teams. Parses a plan into tasks,
  summons swarm workers that claim and complete tasks independently,
  and runs quality gates before completion.

  <example>
  user: "/rune:work plans/feat-user-auth-plan.md"
  assistant: "The Elden Lord marshals the Tarnished to forge the plan..."
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
try { TeamDelete() } catch (e) {
  Bash("rm -rf ~/.claude/teams/rune-work-{timestamp}/ ~/.claude/tasks/rune-work-{timestamp}/ 2>/dev/null")
}
TeamCreate({ team_name: "rune-work-{timestamp}" })

// 2. Create task pool with dependencies
for (const task of extractedTasks) {
  const id = TaskCreate({
    subject: task.subject,
    description: `${task.description}\n\nPlan: ${planPath}\nType: ${task.type}`
  })
  if (task.blockedBy.length > 0) {
    TaskUpdate({ taskId: id, addBlockedBy: task.blockedBy })
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
    4. IF --approve mode: write proposal to tmp/work/{id}/proposals/{task-id}.md,
       send to the Elden Lord via SendMessage, wait for approval before coding.
       Max 2 rejections → mark BLOCKED. Timeout 3 min → auto-REJECT.
    5. Read existing code patterns in the codebase
    6. Implement with TDD cycle (test → implement → refactor)
    7. Run quality gates (discovered from Makefile/package.json/pyproject.toml)
    8. IF ward passes: stage files (git add <specific files>),
       write sanitized commit message to tmp file,
       commit (git commit -F <msg-file>) with format:
       "rune: <task-subject> [ward-checked]"
       Then update plan checkboxes (- [ ] → - [x]).
    9. IF ward fails: do NOT commit, flag task for review, continue to next.
    10. TaskUpdate({ taskId, status: "completed" })
    11. SendMessage to the Elden Lord: "Seal: task #{id} done. Files: {list}"
    12. TaskList() → claim next or exit

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
    4. IF --approve mode: write proposal to tmp/work/{id}/proposals/{task-id}.md,
       send to the Elden Lord via SendMessage, wait for approval before writing tests.
       Max 2 rejections → mark BLOCKED. Timeout 3 min → auto-REJECT.
    5. Discover test patterns (framework, fixtures, assertions)
    6. Write tests following discovered patterns
    7. Run tests to verify they pass
    8. IF tests pass: stage files (git add <specific files>),
       write sanitized commit message to tmp file,
       commit (git commit -F <msg-file>) with format:
       "rune: <task-subject> [ward-checked]"
       Then update plan checkboxes (- [ ] → - [x]).
    9. IF tests fail: do NOT commit, flag task for review, continue to next.
    10. TaskUpdate({ taskId, status: "completed" })
    11. SendMessage to the Elden Lord: "Seal: tests for #{id}. Pass: {count}/{total}"
    12. TaskList() → claim next or exit

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

Poll TaskList to track progress:

```javascript
while (not all tasks completed):
  tasks = TaskList()
  completed = tasks.filter(t => t.status === "completed").length
  total = tasks.length

  // Progress report (every 2 minutes)
  log(`Progress: ${completed}/${total} tasks complete`)

  // Stale detection
  for (task of tasks.filter(t => t.status === "in_progress")):
    if (task.stale > 5 minutes):
      warn("Worker may be stalled on task #{task.id}")
      // After 10 min: release task for reclaim
      if (task.stale > 10 minutes):
        TaskUpdate({ taskId: task.id, owner: "", status: "pending" })

  sleep(30)
```

## Phase 4: Ward Check

After all tasks complete, run project-wide quality gates:

```javascript
// Discover wards
wards = discoverWards()
// Possible sources: Makefile, package.json, pyproject.toml, talisman.yml

for (const ward of wards) {
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
  appendEchoEntry("echoes/workers/MEMORY.md", {
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
try { TeamDelete() } catch (e) {
  Bash("rm -rf ~/.claude/teams/rune-work-{timestamp}/ ~/.claude/tasks/rune-work-{timestamp}/ 2>/dev/null")
}

// 4. Report to user
```

### Completion Report

```
Work complete!

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
| Worker crash | Task returns to pool for reclaim |
| Ward failure | Create fix task, summon worker to fix |
| All workers crash | Abort, report partial progress |
| Plan has no extractable tasks | Ask user to restructure plan |
| Conflicting file edits | Workers write to separate files; lead resolves conflicts |

## --approve Flag (Plan Approval Per Task)

When `--approve` is set, each worker must propose an implementation plan before coding. This provides a genuine safety gate routed to the **human user**.

### Approval Flow

```
For each task when --approve is active:
  1. Worker reads task, proposes implementation plan
  2. Worker writes proposal to tmp/work/{id}/proposals/{task-id}.md
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

Workers write proposals to `tmp/work/{id}/proposals/{task-id}.md`:

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

### Commit Lifecycle

```
After each task completion:
  1. Worker implements task
  2. Ward checks run (project quality gates)
  3. If ward passes:
     - Stage modified files: git add <specific files>
     - Write commit message to tmp file (sanitized)
     - Commit: git commit -F <message-file>
     - Update plan checkboxes
     - Continue to next task
  4. If ward fails:
     - Do NOT commit
     - Flag task for review
     - Continue to next task (other tasks may be independent)
```

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

### Plan Checkbox Updates

After each successful commit:
1. Read original plan file
2. Find matching task line (fuzzy match on task subject)
3. Update `- [ ]` to `- [x]`
4. Write updated plan file
