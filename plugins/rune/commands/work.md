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
Phase 0: Parse Plan → Extract tasks, clarify ambiguities
    ↓
Phase 0.5: Environment Setup → Branch check, stash dirty files
    ↓
Phase 1: Forge Team → TeamCreate + TaskCreate pool
    ↓
Phase 2: Summon Workers → Self-organizing swarm
    ↓ (workers claim → implement → complete → repeat)
Phase 3: Monitor → TaskList polling, stale detection
    ↓
Phase 3.5: Commit Broker → Apply patches, commit (orchestrator-only)
    ↓
Phase 4: Ward Check → Quality gates + verification checklist
    ↓
Phase 5: Echo Persist → Save learnings
    ↓
Phase 6: Cleanup → Shutdown workers, TeamDelete
    ↓
Phase 6.5: Ship → Push + PR creation (optional)
    ↓
Output: Feature branch with commits + PR (optional)
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

### Identify Ambiguities

After extracting tasks, scan for potential issues before asking the user to confirm:

1. **Vague task descriptions**: Tasks with no file references, no acceptance criteria, or generic verbs ("improve", "update", "handle")
2. **Missing dependencies**: Tasks that reference components not covered by other tasks
3. **Unclear scope**: Tasks where the plan says "etc." or "and similar"
4. **Conflicting instructions**: Tasks where the plan gives contradictory guidance

If ambiguities found (>= 1):

```javascript
AskUserQuestion({
  questions: [{
    question: `Found ${count} ambiguities in the plan:\n${ambiguityList}\n\nClarify now or proceed as-is?`,
    header: "Clarify",
    options: [
      { label: "Clarify now (Recommended)", description: "Answer questions before workers start" },
      { label: "Proceed as-is", description: "Workers will interpret ambiguities on their own" }
    ],
    multiSelect: false
  }]
})
```

If user chooses to clarify: ask specific questions one at a time (max 3), then append clarifications to the task descriptions before creating the task pool. Default on timeout: "Proceed as-is" (fail-safe).

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

## Phase 0.5: Environment Setup

Before forging the team, verify the git environment is safe for work.

**Skip condition**: When invoked via `/rune:arc`, skip Phase 0.5 entirely — arc handles branch creation in its Pre-flight phase (COMMIT-1). Detection: check for active arc checkpoint at `.claude/arc/*/checkpoint.json` with any phase status `"in_progress"`.

**Talisman override**: `work.skip_branch_check: true` disables this phase for experienced users who manage branches manually.

### Branch Check

```javascript
// 1. Detect current branch and default branch
const currentBranch = Bash("git branch --show-current").trim()
const defaultBranch = Bash("git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@'").trim()
  || (Bash("git rev-parse --verify origin/main 2>/dev/null").exitCode === 0 ? "main" : "master")
// SECURITY: Validate branch names before display or shell interpolation
const BRANCH_RE = /^[a-zA-Z0-9][a-zA-Z0-9._\/-]*$/
if (!BRANCH_RE.test(defaultBranch)) throw new Error(`Unexpected default branch name: ${defaultBranch}`)

if (currentBranch === defaultBranch) {
  // On default branch — must create feature branch
  AskUserQuestion({
    questions: [{
      question: `You're on \`${defaultBranch}\`. Workers will commit here. Create a feature branch?`,
      header: "Branch",
      options: [
        { label: "Create branch (Recommended)", description: "Create a feature branch from current HEAD" },
        { label: "Continue on " + defaultBranch, description: "Workers commit directly to " + defaultBranch }
      ],
      multiSelect: false
    }]
  })
  // If create branch:
  //   Read talisman prefix and validate BEFORE concatenation (defense-in-depth):
  //   const branchPrefix = talisman?.work?.branch_prefix ?? "rune/work"
  //   SECURITY: Validate prefix early — block shell metacharacters at input, not just at final name
  //   if (!/^[a-zA-Z0-9][a-zA-Z0-9_\/-]*$/.test(branchPrefix)) {
  //     throw new Error(`Invalid branch_prefix in talisman.yml: ${branchPrefix}`)
  //   }
  //   Derive slug and timestamp:
  //   const planSlug = basename(planFile, ".md").replace(/[^a-zA-Z0-9]/g, "-") || "unnamed"
  //   const timestamp = Bash("date +%Y%m%d-%H%M%S").trim()  // Local time, consistent with arc.md
  //   const branchName = `${branchPrefix}-${planSlug}-${timestamp}`
  //   SECURITY: Validate final branch name (catches interactions between prefix + slug)
  //   if (!/^[a-zA-Z0-9][a-zA-Z0-9._\/-]*$/.test(branchName) || branchName.includes('//')) {
  //     throw new Error("Invalid branch name derived from plan file")
  //   }
  //   Bash(`git checkout -b -- "${branchName}"`)
  // If continue on default:
  //   Require explicit "yes" confirmation (fail-closed)
}
```

### Dirty Working Tree Check

```javascript
// 2. Check for uncommitted changes
const status = Bash("git status --porcelain").trim()
if (status !== "") {
  AskUserQuestion({
    questions: [{
      question: "Uncommitted changes found. How to proceed?",
      header: "Git state",
      options: [
        { label: "Stash changes (Recommended)", description: "git stash — restore after work completes" },
        { label: "Continue anyway", description: "Workers may conflict with uncommitted changes" }
      ],
      multiSelect: false
    }]
  })
  // If stash: Bash("git stash push -m 'rune-work-pre-flight'")
  // Default on timeout: stash (fail-safe)
}
```

**Branch name derivation**: `rune/work-{slugified-plan-name}-{YYYYMMDD-HHMMSS}` matching arc.md's COMMIT-1 convention. Timestamp uses local time (consistent with arc.md `$(date +%Y%m%d-%H%M%S)`).

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

### Post-Ward Verification Checklist

After ward commands pass, run a deterministic verification pass at zero LLM cost:

```javascript
const checks = []

// 1. All tasks completed
const tasks = TaskList()
const incomplete = tasks.filter(t => t.status !== "completed")
if (incomplete.length > 0) {
  checks.push(`WARN: ${incomplete.length} tasks not completed: ${incomplete.map(t => t.subject).join(", ")}`)
}

// 2. Plan checkboxes all checked
const planContent = Read(planPath)
const unchecked = (planContent.match(/- \[ \]/g) || []).length
if (unchecked > 0) {
  checks.push(`WARN: ${unchecked} unchecked items remain in plan`)
}

// 3. No BLOCKED tasks
const blocked = tasks.filter(t => t.status === "pending" && t.blockedBy?.length > 0)
if (blocked.length > 0) {
  checks.push(`WARN: ${blocked.length} tasks still blocked`)
}

// 4. No uncommitted patches
// Helper: extract task ID from patch filename (e.g., "tmp/.../patches/task-42.patch" → "task-42")
function extractTaskId(patchPath) {
  return patchPath.match(/([a-zA-Z0-9_-]+)\.patch$/)?.[1] ?? null
}
// committedTaskIds: Set<string> — accumulated during Phase 3.5 Commit Broker loop (see commitBroker function)
const unapplied = Glob("tmp/work/{timestamp}/patches/*.patch")
  .filter(p => !committedTaskIds.has(extractTaskId(p)))
if (unapplied.length > 0) {
  checks.push(`WARN: ${unapplied.length} patches not committed`)
}

// 5. No merge conflict markers in tracked files
const conflictMarkers = Bash("git diff --check HEAD 2>&1 || true").trim()
if (conflictMarkers !== "") {
  checks.push(`WARN: Merge conflict markers detected in working tree`)
}

// 6. No uncommitted changes in tracked files (clean state for PR)
// Use git diff for tracked files only — avoids false positives from tmp/, logs, or .gitignore'd artifacts
const dirtyTracked = (Bash("git diff --name-only HEAD").trim() + "\n" +
                      Bash("git diff --cached --name-only").trim()).trim()
if (dirtyTracked !== "") {
  const fileCount = dirtyTracked.split('\n').filter(Boolean).length
  checks.push(`WARN: Uncommitted changes in tracked files (${fileCount} files)`)
}

// Report — non-blocking, report to user but don't halt
if (checks.length > 0) {
  warn("Verification warnings:\n" + checks.join("\n"))
}
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

// 5. Report to user (see Completion Report below)
```

## Phase 6.5: Ship (Optional)

After cleanup, offer to push and create a PR. This phase completes the developer workflow from "parse plan" to "ship feature."

### Pre-check: gh CLI Availability

```javascript
const ghAvailable = Bash("command -v gh >/dev/null 2>&1 && gh auth status 2>&1 | grep -q 'Logged in' && echo 'ok'").trim() === "ok"
if (!ghAvailable) {
  warn("GitHub CLI (gh) not available or not authenticated. PR creation will be skipped.")
  warn("Install: https://cli.github.com/ — then run: gh auth login")
  // Fall back to manual push instructions
}
```

### Ship Decision

```javascript
// Only offer if on a feature branch (not default branch)
const currentBranch = Bash("git branch --show-current").trim()
const defaultBranch = Bash("git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@'").trim()
  || (Bash("git rev-parse --verify origin/main 2>/dev/null").exitCode === 0 ? "main" : "master")

if (currentBranch !== defaultBranch) {
  const options = [
    { label: "Skip", description: "Don't push — review locally first" }
  ]
  if (ghAvailable) {
    // "Create PR" includes push — no separate "Push only" needed (user can push manually via "Other")
    options.unshift(
      { label: "Create PR (Recommended)", description: "Push branch and open a pull request" }
    )
  } else {
    options.unshift(
      { label: "Push only", description: "Push to remote (gh CLI not available for PR)" }
    )
  }
  AskUserQuestion({
    questions: [{
      question: `Work complete on \`${currentBranch}\`. Ship it?`,
      header: "Ship",
      options: options,
      multiSelect: false
    }]
  })
  // Default on timeout: Skip (fail-safe — don't push without explicit consent)
}
```

### PR Template

When user selects "Create PR":

```javascript
// 1. Push branch
// SECURITY: Validate branch name before shell interpolation
if (!/^[a-zA-Z0-9][a-zA-Z0-9._\/-]*$/.test(currentBranch)) {
  throw new Error(`Invalid branch name for push: ${currentBranch}`)
}
Bash(`git push -u origin -- "${currentBranch}"`)

// 2. Generate PR title from plan
// Extract title: try frontmatter `title:` field, fallback to plan filename
const planContent = Read(planPath)
const titleMatch = planContent.match(/^---\n[\s\S]*?^title:\s*(.+?)$/m)
const planTitle = titleMatch ? titleMatch[1].trim() : basename(planPath, '.md').replace(/^\d{4}-\d{2}-\d{2}-/, '')
// Extract type: try frontmatter `type:` field, fallback to filename prefix pattern ({type}-{name})
const typeMatch = planContent.match(/^type:\s*(\w+)/m) || planPath.match(/\/(\w+)-/)
const planType = typeMatch ? typeMatch[1] : 'feat'  // feat | fix | refactor
const prTitle = `${planType}: ${planTitle}`
// Sanitize: allow only safe chars (matches commit message pattern), limit to 70 chars
const safePrTitle = prTitle.replace(/[^a-zA-Z0-9 ._\-:()]/g, '').slice(0, 70) || "Work completed"

// 3. Build file change summary
// SECURITY: Validate defaultBranch before shell interpolation (currentBranch validated above)
if (!/^[a-zA-Z0-9][a-zA-Z0-9._\/-]*$/.test(defaultBranch)) {
  throw new Error(`Invalid default branch name: ${defaultBranch}`)
}
const diffStat = Bash(`git diff --stat -- "${defaultBranch}"..."${currentBranch}"`).trim()

// 4. Read talisman for PR overrides (defaults documented here)
// readTalisman(): Read .claude/talisman.yml (project) or ~/.claude/talisman.yml (user), parse YAML.
// Returns null if neither exists. Same lookup used in arc.md and plan.md.
const talisman = readTalisman()
const monitoringRequired = talisman?.work?.pr_monitoring ?? false    // Default: false
const autoPush = talisman?.work?.auto_push ?? false                  // Default: false
const coAuthors = talisman?.work?.co_authors ?? []                   // Default: [] (no co-authors)
// Note: pr_template config key reserved for v1.13.0 (minimal template variant)

// 5. Build co-author lines
// SECURITY: Validate "Name <email>" format — reject entries with newlines or missing angle brackets
const validCoAuthors = coAuthors.filter(a => /^[^<>\n]+\s+<[^@\n]+@[^>\n]+>$/.test(a))
const coAuthorLines = validCoAuthors.map(a => `Co-Authored-By: ${a}`).join('\n')

// 6. Capture variables from earlier phases for PR body
// wardResults: Array<{name, exitCode}> — accumulated during Phase 4 Ward Check
// commitCount: number — from committedTaskIds.size (Phase 3.5 Commit Broker)
// verificationWarnings: Array<string> — from checks[] in Post-Ward Verification Checklist
const commitCount = committedTaskIds.size
const verificationWarnings = checks  // From Post-Ward Verification Checklist above

// 7. Write PR body to file (avoid shell injection via -m flag)
// SECURITY: Sanitize planPath for markdown rendering (escape backticks and $)
const safePlanPath = planPath.replace(/[`$]/g, '\\$&')
const prBody = `## Summary

Implemented from plan: \`${safePlanPath}\`

### Changes
${diffStat}

### Tasks Completed
${completedTasks.map(t => `- [x] ${t.subject}`).join("\n")}
${blockedTasks.length > 0 ? `\n### Blocked Tasks\n${blockedTasks.map(t => `- [ ] ${t.subject}`).join("\n")}` : ""}

## Testing
- Ward checks passed: ${wardResults.map(w => w.name).join(", ")}
- ${commitCount} incremental commits, each ward-checked

## Quality
- All plan checkboxes checked
- ${verificationWarnings.length === 0 ? "No verification warnings" : `${verificationWarnings.length} warnings`}
${monitoringRequired ? `
## Post-Deploy Monitoring
<!-- Fill in before merging -->
- **What to monitor**:
- **Expected healthy behavior**:
- **Failure signals / rollback trigger**:
- **Validation window**:
` : ""}
---
Generated with [Claude Code](https://claude.ai/code) via Rune Plugin
${coAuthorLines}`

// SECURITY: Re-validate timestamp for file path (defense-in-depth — validated at Phase 1 line 232)
if (!/^\d+$/.test(timestamp)) throw new Error("Invalid work timestamp")
Write(`tmp/work/${timestamp}/pr-body.md`, prBody)
Bash(`gh pr create --title "${safePrTitle}" --body-file "tmp/work/${timestamp}/pr-body.md"`)
```

### Completion Report

```
⚔ The Tarnished has claimed the Elden Throne.

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

### Smart Next Steps

After the completion report, present interactive next steps.
**NOTE**: Compute `changedFiles` once before the Completion Report (e.g., after Phase 6 Cleanup) and reuse in both the report and Smart Next Steps to avoid redundant git diff calls.

```javascript
// Compute review recommendation based on changeset analysis
// NOTE: defaultBranch and currentBranch already validated in Phase 6.5 PR Template (SEC-1, SEC-2)
// Reuse changedFiles if already computed for Completion Report; otherwise compute here:
const changedFiles = changedFiles ?? Bash(`git diff --name-only -- "${defaultBranch}"..."${currentBranch}"`).trim().split('\n').filter(Boolean)
const filesChanged = changedFiles.length
const hasSecurityFiles = changedFiles.some(f => /auth|secret|token|crypt|password|session|\.env/i.test(f))
const hasConfigFiles = changedFiles.some(f => /\.claude\/|talisman|CLAUDE\.md/i.test(f))
const taskCount = completedTasks.length

let reviewRecommendation
if (hasSecurityFiles) {
  reviewRecommendation = "/rune:review (Recommended) — security-sensitive files changed"
} else if (filesChanged >= 10 || taskCount >= 8) {
  reviewRecommendation = "/rune:review (Recommended) — large changeset"
} else if (hasConfigFiles) {
  reviewRecommendation = "/rune:review (Suggested) — configuration files changed"
} else {
  reviewRecommendation = "/rune:review (Optional) — small, focused changeset"
}

AskUserQuestion({
  questions: [{
    question: `Work complete. What next?`,
    header: "Next",
    options: [
      { label: reviewRecommendation.split(" — ")[0], description: reviewRecommendation.split(" — ")[1] || "Review the implementation" },
      { label: "Create PR", description: "Push and open a pull request" },
      { label: "/rune:rest", description: "Clean up tmp/ artifacts" }
    ],
    multiSelect: false
  }]
})
// AskUserQuestion auto-provides "Other" free-text option.
// "Other" handlers: "arc --resume" → continue arc; "push" → git push; "diff" → git diff
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

When used via `/rune:arc --approve`, the flag applies **only to Phase 5 (WORK)**, not to Phase 7 (MEND).

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

When invoked via `/rune:arc` (Phase 5), the work sub-orchestrator (team lead of the work team) handles checkbox updates — not the arc-level orchestrator.

## Key Principles

### For the Tarnished (Orchestrator)

- **Ship complete features**: Don't stop at "tasks done" — verify wards pass, plan checkboxes are checked, and offer to create a PR.
- **Fail fast on ambiguity**: Ask clarifying questions in Phase 0, not after workers have started implementing.
- **Branch safety first**: Never let workers commit to `main` without explicit user confirmation.
- **Serialize git operations**: All commits go through the commit broker. Never let workers run `git add` or `git commit` directly.

### For Workers (Rune Smiths & Trial Forgers)

- **Match existing patterns**: Read similar code before writing new code. The plan references exist for a reason.
- **Test as you go**: Run wards after each task, not just at the end. Fix failures immediately.
- **One task, one patch**: Each task produces exactly one patch. Don't bundle unrelated changes.
- **Don't over-engineer**: Implement what the task says. No extra features, no speculative abstractions.
- **Exit cleanly**: No tasks after 3 retries → idle notification → exit. Approve shutdown requests immediately.

## Common Pitfalls

| Pitfall | Prevention |
|---------|------------|
| Committing to `main` | Phase 0.5 branch check (fail-closed) |
| Building wrong thing from ambiguous plan | Phase 0 clarification sub-step |
| 80% done syndrome — work "completes" but PR never created | Phase 6.5 ship phase |
| Over-reviewing simple changes | Review guidance heuristic in completion report |
| Workers editing same files | Task extraction classifies dependencies; commit broker handles conflicts |
| Stale worker blocking pipeline | Stale detection (5 min warn, 10 min auto-release) |
| Ward failure cascade | Auto-create fix task, summon fresh worker |
| Dirty working tree conflicts | Phase 0.5 stash check |
| `gh` CLI not installed | Pre-check with fallback to manual instructions |
