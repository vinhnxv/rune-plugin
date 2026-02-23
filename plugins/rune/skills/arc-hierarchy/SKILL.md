---
name: arc-hierarchy
description: |
  Hierarchical plan execution — orchestrates parent/child plan decomposition with
  dependency DAGs, requires/provides contracts, and feature branch strategy.
  Use when a plan has been decomposed into child plans via /rune:devise Phase 2.5
  (Hierarchical option) and frontmatter shows `hierarchical: true` with a `children_dir`.
  Handles: topological sequencing, contract verification, partial failure recovery,
  and per-child feature branch management.
  Keywords: hierarchical, parent plan, child plan, decomposition, DAG, dependency,
  shatter, children_dir, requires, provides, contract matrix, arc-hierarchy.

  <example>
  Context: User has a parent plan with child plans decomposed
  user: "/rune:arc-hierarchy plans/2026-02-23-feature-auth-plan.md"
  assistant: "The Tarnished reads the execution table and begins executing child plans in topological order..."
  </example>

  <example>
  Context: User wants to resume after a child plan failure
  user: "/rune:arc-hierarchy plans/parent.md --resume"
  assistant: "Resuming hierarchy execution. Found 2/5 children completed. Next executable: 03-permissions..."
  </example>
user-invocable: true
disable-model-invocation: true
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
  - Task
  - TeamCreate
  - TeamDelete
  - SendMessage
  - AskUserQuestion
  - TodoWrite
argument-hint: "<parent-plan-path> [--resume] [--dry-run] [--no-merge]"
---

# /rune:arc-hierarchy — Hierarchical Plan Execution

Orchestrates sequential execution of child plans (produced by `/rune:devise` with `--shatter`) in dependency order. Each child is executed via a full `/rune:arc` pipeline. The parent plan serves as the execution manifest.

**Load skills**: `rune-orchestration`, `chome-pattern`, `zsh-compat`, `polling-guard`

> **FC-1**: Detection of hierarchical plans belongs HERE — not in arc-preflight.md. Standard `/rune:arc` runs NEVER see hierarchical logic. Users invoke this skill explicitly when they have a shattered parent plan.

## Usage

```
/rune:arc-hierarchy plans/2026-02-23-feature-auth-plan.md
/rune:arc-hierarchy plans/parent.md --resume       # Resume after interruption
/rune:arc-hierarchy plans/parent.md --dry-run      # Preview execution order only
/rune:arc-hierarchy plans/parent.md --no-merge     # Skip auto-merge on children
```

## Flags

| Flag | Description | Default |
|------|-------------|---------|
| `--resume` | Resume from current execution table state | Off |
| `--dry-run` | Show execution order and contracts, exit without running | Off |
| `--no-merge` | Pass `--no-merge` to each child arc run | Off |

## Parent Plan Detection

A plan is hierarchical if its YAML frontmatter contains both:
```yaml
hierarchical: true
children_dir: plans/children/
```

Parse with `extractYamlFrontmatter(content)`. If frontmatter is missing either field, this skill exits with guidance to run `/rune:devise --shatter` first.

## Reference Files

- [hierarchy-parser.md](references/hierarchy-parser.md) — `parseExecutionTable`, `updateExecutionTable`, `findNextExecutable`, `parseDependencyContractMatrix`, artifact verification
- [branch-strategy.md](references/branch-strategy.md) — feature branch creation, child branch management, merge, cleanup
- [prerequisite-verification.md](references/prerequisite-verification.md) — `verifyPrerequisites`, `verifyProvides`, resolution strategies
- [coherence-check.md](references/coherence-check.md) — pre-execution contract coherence validation

---

## Orchestration Loop

### Phase 0: Parse Arguments

```javascript
const args = "$ARGUMENTS".trim()
const planPath = args.replace(/--\S+/g, '').trim()
const resumeMode = args.includes('--resume')
const dryRun = args.includes('--dry-run')
const noMerge = args.includes('--no-merge')

// Guard: empty path check BEFORE validation (BACK-001 fix)
if (!planPath) {
  error("Usage: /rune:arc-hierarchy <parent-plan-path>")
  return
}

// SEC-1: validate path before any file operations
const pathValidation = validatePlanPath(planPath)
if (!pathValidation.valid) {
  error(`Invalid plan path: ${pathValidation.reason}`)
  return
}
```

### Phase 1: Detect Hierarchical Plan

```javascript
const planContent = Read(planPath)
if (!planContent) {
  error(`Cannot read parent plan: ${planPath}`)
  return
}

const frontmatter = extractYamlFrontmatter(planContent)
if (!frontmatter?.hierarchical || !frontmatter?.children_dir) {
  error("This plan is not hierarchical.")
  error("Expected frontmatter: `hierarchical: true` and `children_dir: plans/children/`")
  error("Run /rune:devise --shatter to decompose a plan into child plans first.")
  return
}

const childrenDir = frontmatter.children_dir
```

### Phase 2: Parse Execution State

```javascript
// See hierarchy-parser.md for full pseudocode
const executionTable = parseExecutionTable(planContent)
const contractMatrix = parseDependencyContractMatrix(planContent)

if (executionTable.length === 0) {
  error("No execution table found in parent plan. Expected a | Seq | Child Plan | Status | ... table.")
  return
}

const totalChildren = executionTable.length
const completedChildren = executionTable.filter(e => e.status === "completed").length
const pendingChildren = executionTable.filter(e => e.status === "pending").length

log(`Execution table: ${totalChildren} children, ${completedChildren} completed, ${pendingChildren} pending`)
```

### Phase 3: Dry Run (if --dry-run)

```javascript
if (dryRun) {
  log("Dry run — execution order (topological):")
  let remaining = [...executionTable]
  let order = 0
  let simulatedCompleted = new Set(
    executionTable.filter(e => e.status === "completed").map(e => e.seq)
  )

  while (true) {
    const next = findNextExecutable(remaining.map(e =>
      simulatedCompleted.has(e.seq) ? { ...e, status: "completed" } : e
    ))
    if (!next) break
    order++
    log(`  ${order}. [${next.seq}] ${next.path}`)
    simulatedCompleted.add(next.seq)
    remaining = remaining.filter(e => e.seq !== next.seq)
  }

  if (contractMatrix.length > 0) {
    log("\nContract Matrix:")
    for (const entry of contractMatrix) {
      const requires = entry.requires.length > 0 ? entry.requires.map(a => `${a.type}:${a.name}`).join(", ") : "—"
      const provides = entry.provides.length > 0 ? entry.provides.map(a => `${a.type}:${a.name}`).join(", ") : "—"
      log(`  ${entry.child}: requires=[${requires}] provides=[${provides}]`)
    }
  }

  return
}
```

### Phase 4: Pre-Execution Coherence Check

```javascript
// See coherence-check.md for full pseudocode
const coherenceResult = runCoherenceCheck(planContent, executionTable, contractMatrix)
if (coherenceResult.errors.length > 0) {
  warn("Coherence check found issues:")
  for (const err of coherenceResult.errors) {
    warn(`  [${err.severity}] ${err.message}`)
  }

  const hasBlockingErrors = coherenceResult.errors.some(e => e.severity === "error")
  if (hasBlockingErrors) {
    const userChoice = AskUserQuestion({
      questions: [{
        question: "Coherence check found blocking errors. How to proceed?",
        header: "Coherence",
        options: [
          { label: "Abort — fix parent plan first", description: "Review coherence-check.md output" },
          { label: "Continue anyway (risky)", description: "Proceed despite errors" }
        ],
        multiSelect: false
      }]
    })

    // BACK-002 FIX: Handle user response — abort if user chooses to fix first
    if (userChoice !== "Continue anyway (risky)") {
      error("Aborting due to coherence check blocking errors. Fix parent plan and re-run.")
      return
    }
    warn("User chose to continue despite blocking errors.")
  }
}
```

### Phase 5: Session Identity + State File

```javascript
// CHOME pattern: SDK Read() resolves CLAUDE_CONFIG_DIR automatically
// Bash rm/find must use explicit CHOME. See chome-pattern skill.
const configDir = Bash(`CHOME="${CLAUDE_CONFIG_DIR:-$HOME/.claude}" && cd "$CHOME" 2>/dev/null && pwd -P`).trim()
const ownerPid = Bash(`echo $PPID`).trim()

const stateFile = ".claude/arc-hierarchy-loop.local.md"

// Check for existing session
const existingState = Read(stateFile)  // null if not found — SDK Read() is safe
if (existingState && /^active:\s*true$/m.test(existingState)) {
  const existingPid = existingState.match(/owner_pid:\s*(\d+)/)?.[1]
  const existingCfg = existingState.match(/config_dir:\s*(.+)/)?.[1]?.trim()

  let ownedByOther = false
  if (existingCfg && existingCfg !== configDir) {
    ownedByOther = true
  } else if (existingPid && /^\d+$/.test(existingPid) && existingPid !== ownerPid) {
    const alive = Bash(`kill -0 ${existingPid} 2>/dev/null && echo "alive" || echo "dead"`).trim()
    if (alive === "alive") ownedByOther = true
  }

  if (ownedByOther && !resumeMode) {
    error("Another session is already executing arc-hierarchy on this repo.")
    error("Cancel it with /rune:cancel-arc-hierarchy, or use --resume to continue your own session.")
    return
  }
  if (!ownedByOther) {
    warn("Found existing state file from this session. Overwriting (use --resume to continue from current table state).")
  }
}

// Write state file with session isolation (all three fields required per CLAUDE.md §11)
// BACK-007 FIX: Include `status: active` for stop hook Guard 7 compatibility
// BACK-008 FIX: Include current_child, feature_branch, execution_table_path for stop hook
// These fields are updated as the loop progresses (current_child set before each child arc)
Write(stateFile, `---
active: true
status: active
parent_plan: ${planPath}
children_dir: ${childrenDir}
current_child: ""
feature_branch: ""
execution_table_path: ""
no_merge: ${noMerge}
config_dir: ${configDir}
owner_pid: ${ownerPid}
session_id: ${CLAUDE_SESSION_ID}
started_at: "${new Date().toISOString()}"
---

Arc hierarchy loop state. Do not edit manually.
Use /rune:cancel-arc-hierarchy to stop execution.
`)
```

### Phase 6: Feature Branch Setup

```javascript
// See branch-strategy.md for full pseudocode
const featureBranch = createFeatureBranch(frontmatter.title || planPath)
log(`Feature branch created: ${featureBranch}`)
```

### Phase 7: Main Execution Loop

```javascript
let iteration = 0
const MAX_ITERATIONS = executionTable.length + 10  // Safety cap
// BACK-016 FIX: Track per-child prerequisite failure counts for cycle detection
const prereqFailureCounts = {}

while (true) {
  iteration++
  if (iteration > MAX_ITERATIONS) {
    error(`Safety cap reached (${MAX_ITERATIONS} iterations). Possible infinite loop. Aborting.`)
    break
  }

  // Re-read plan to get fresh execution table state
  const freshContent = Read(planPath)
  const freshTable = parseExecutionTable(freshContent)

  const next = findNextExecutable(freshTable)
  if (!next) {
    const allDone = freshTable.every(e => ["completed", "failed", "skipped"].includes(e.status))
    if (allDone) {
      log("All children have terminal status. Execution complete.")
    } else {
      const blocked = freshTable.filter(e => e.status === "pending")
      warn(`No executable children found. ${blocked.length} children remain blocked (circular dependency or failed predecessor).`)
      for (const b of blocked) {
        warn(`  Blocked: [${b.seq}] ${b.path} (deps: ${b.dependencies.join(", ")})`)
      }
    }
    break
  }

  log(`\n── Executing child [${next.seq}]: ${next.path} ──`)

  // Phase 7a: Verify prerequisites (requires contracts)
  // See prerequisite-verification.md for full pseudocode
  const prereqResult = verifyPrerequisites(next, contractMatrix)
  if (!prereqResult.passed) {
    // BACK-016 FIX: Track per-child failure counts for cycle detection
    prereqFailureCounts[next.seq] = (prereqFailureCounts[next.seq] || 0) + 1
    if (prereqFailureCounts[next.seq] > 2) {
      warn(`Child [${next.seq}] has failed prerequisites ${prereqFailureCounts[next.seq]} times. Automated recovery exhausted.`)
      error("Execution paused. Fix prerequisites manually and run /rune:arc-hierarchy --resume")
      break
    }

    const resolution = await handlePrerequisiteFailure(next, prereqResult, contractMatrix, planPath)
    if (resolution === "abort") break
    if (resolution === "skip") {
      const updated = updateExecutionTable(Read(planPath), next.seq, { status: "skipped" })
      Write(planPath, updated)
      continue
    }
    // resolution === "retry" — loop continues (BACK-005/006: child reset to pending by handler)
    continue
  }

  // Phase 7b: Create child branch
  const childBranch = createChildBranch(featureBranch, next.seq, next.path.split("/").pop().replace(".md", ""))

  // Phase 7c: Update table to in_progress (QUAL-004 FIX: underscore, not hyphen)
  let updatedContent = updateExecutionTable(Read(planPath), next.seq, {
    status: "in_progress",
    started: new Date().toISOString()
  })
  Write(planPath, updatedContent)

  // Phase 7c.1: Update state file with current child info for stop hook (BACK-008 FIX)
  const childFilename = next.path.split("/").pop()
  const stateContent = Read(stateFile)
  const updatedState = stateContent
    .replace(/^current_child:.*$/m, `current_child: ${childFilename}`)
    .replace(/^feature_branch:.*$/m, `feature_branch: ${featureBranch}`)
    .replace(/^execution_table_path:.*$/m, `execution_table_path: ${planPath}`)
  Write(stateFile, updatedState)

  // Phase 7c.2: Write JSON sidecar for stop hook execution table parsing (BACK-009 FIX)
  // The stop hook uses jq for topological sort — it needs JSON, not the Markdown table.
  // This sidecar is the machine-readable version; the Markdown table in the plan is human-readable.
  const jsonTable = {
    updated_at: new Date().toISOString(),
    children: parseExecutionTable(Read(planPath)).map(e => ({
      seq: e.seq,
      plan: e.path.split("/").pop(),
      status: e.status,
      depends_on: e.dependencies,
      started_at: e.started,
      completed_at: e.completed,
      provides: (contractMatrix.find(c => c.child === extractChildId(e.path))?.provides || [])
        .map(a => `${a.name}`)
    }))
  }
  Write(".claude/arc-hierarchy-exec-table.json", JSON.stringify(jsonTable, null, 2))

  // Phase 7d: Invoke arc for child plan
  const mergeFlag = noMerge ? " --no-merge" : ""
  Skill("arc", `${next.path}${mergeFlag}`)

  // Phase 7e: Verify provides contracts
  const providesResult = verifyProvides(next, contractMatrix)
  if (!providesResult.passed) {
    warn(`Child [${next.seq}] completed but provides verification failed:`)
    for (const failure of providesResult.failures) {
      warn(`  MISSING: ${failure.type}:${failure.name} — ${failure.reason}`)
    }

    // Mark as partial — does not unblock dependents (BUG-1)
    updatedContent = updateExecutionTable(Read(planPath), next.seq, {
      status: "partial",
      completed: new Date().toISOString()
    })
    Write(planPath, updatedContent)

    // BACK-003 FIX: Capture response and implement all 4 branches
    const providesChoice = AskUserQuestion({
      questions: [{
        question: `Child [${next.seq}] has ${providesResult.failures.length} missing provides. How to proceed?`,
        header: "Provides Verification Failed",
        options: [
          { label: "Mark as completed anyway", description: "Unblocks dependent children (risky)" },
          { label: "Re-run child arc", description: "Try to fix the missing artifacts" },
          { label: "Skip dependents", description: "Mark dependent children as skipped" },
          { label: "Abort hierarchy", description: "Stop execution here" }
        ],
        multiSelect: false
      }]
    })

    if (providesChoice === "Mark as completed anyway") {
      updatedContent = updateExecutionTable(Read(planPath), next.seq, {
        status: "completed",
        completed: new Date().toISOString()
      })
      Write(planPath, updatedContent)
      warn(`Child [${next.seq}] force-marked as completed despite missing provides.`)
      continue
    } else if (providesChoice === "Re-run child arc") {
      // Reset to pending so it gets picked up again
      updatedContent = updateExecutionTable(Read(planPath), next.seq, {
        status: "pending",
        started: "—",
        completed: "—"
      })
      Write(planPath, updatedContent)
      continue
    } else if (providesChoice === "Skip dependents") {
      // Find all children that depend on this child and mark them skipped
      const freshTable = parseExecutionTable(Read(planPath))
      for (const entry of freshTable) {
        if (entry.dependencies.some(d => normalizeSeq(d) === normalizeSeq(next.seq))) {
          const skipUpdate = updateExecutionTable(Read(planPath), entry.seq, { status: "skipped" })
          Write(planPath, skipUpdate)
          warn(`Skipped dependent child [${entry.seq}]: ${entry.path}`)
        }
      }
      continue
    } else {
      // "Abort hierarchy" or any other response
      error("Hierarchy execution aborted by user due to provides verification failure.")
      break
    }
  }

  // Phase 7f: Merge child branch to feature branch
  mergeChildToFeature(childBranch, featureBranch)

  // Phase 7g: Mark completed in execution table
  updatedContent = updateExecutionTable(Read(planPath), next.seq, {
    status: "completed",
    completed: new Date().toISOString()
  })
  Write(planPath, updatedContent)

  log(`Child [${next.seq}] completed successfully.`)
}
```

### Phase 8: Finalize

```javascript
const finalContent = Read(planPath)
const finalTable = parseExecutionTable(finalContent)
const completedCount = finalTable.filter(e => e.status === "completed").length
const failedCount = finalTable.filter(e => e.status === "failed").length
const partialCount = finalTable.filter(e => e.status === "partial").length
const skippedCount = finalTable.filter(e => e.status === "skipped").length

log(`\n── Hierarchy Execution Complete ──`)
log(`  Completed: ${completedCount}/${totalChildren}`)
if (failedCount > 0) log(`  Failed: ${failedCount}`)
if (partialCount > 0) log(`  Partial: ${partialCount}`)
if (skippedCount > 0) log(`  Skipped: ${skippedCount}`)

if (completedCount === totalChildren) {
  // All children succeeded — finalize feature branch
  finalizeFeatureBranch(featureBranch)
  log("The Tarnished has claimed the Elden Throne for the full feature.")
} else {
  warn("Not all children completed. Feature branch left in place for manual review.")
  log(`Feature branch: ${featureBranch}`)
}

// Clean up state file and JSON sidecar
Bash(`rm -f "${stateFile}" ".claude/arc-hierarchy-exec-table.json"`)
```

---

## State File Format

`.claude/arc-hierarchy-loop.local.md` — YAML frontmatter:

```yaml
---
active: true
status: active
parent_plan: plans/2026-02-23-feature-auth-plan.md
children_dir: plans/children/
current_child: 02-api-plan.md
feature_branch: feat/hierarchical-auth
execution_table_path: plans/2026-02-23-feature-auth-plan.md
no_merge: false
config_dir: /Users/user/.claude
owner_pid: 12345
session_id: abc-123-def-456
started_at: "2026-02-23T00:00:00Z"
---

Arc hierarchy loop state. Do not edit manually.
Use /rune:cancel-arc-hierarchy to stop execution.
```

**JSON Sidecar**: `.claude/arc-hierarchy-exec-table.json` — machine-readable execution table for the stop hook (jq-based parsing). Updated by the orchestrator at Phase 7c before each child arc. The Markdown table in the parent plan remains the human-readable source of truth.

**Session isolation fields** (CLAUDE.md §11 — CRITICAL):
- `config_dir` — resolved CLAUDE_CONFIG_DIR. Isolates different Claude Code installations.
- `owner_pid` — `$PPID` in Bash (Claude Code process PID). Isolates parallel sessions.
- `session_id` — `CLAUDE_SESSION_ID`. Diagnostic only — not verifiable in bash.

---

## Error Handling

| Scenario | Behavior |
|----------|----------|
| Path traversal in planPath | Abort immediately (SEC-1) |
| Not a hierarchical plan | Abort with guidance to `/rune:devise --shatter` |
| Another session active | Abort unless `--resume` |
| Coherence check errors | AskUserQuestion — user chooses abort or continue |
| Prerequisites missing | Resolution strategies: pause/self-heal/backtrack/skip (see prerequisite-verification.md) |
| Provides verification fails | Mark as `partial`, AskUserQuestion for resolution |
| Circular dependency detected | Warn, list blocked children, abort loop |
| Failed predecessor | Warn, list blocked children, offer to skip dependents |
| Safety cap hit | Abort with diagnostic output |
