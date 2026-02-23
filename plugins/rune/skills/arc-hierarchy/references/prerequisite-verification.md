# Prerequisite Verification Reference

Pseudocode for verifying requires/provides contracts in the `arc-hierarchy` skill. Covers pre-execution prerequisite checks, post-execution provides verification, and resolution strategies.

---

## verifyPrerequisites(child, contractMatrix)

Check that all required artifacts for a child plan exist before executing it.

**Inputs**:
- `child` — execution table entry `{ seq, path, status, dependencies, ... }`
- `contractMatrix` — output of `parseDependencyContractMatrix()` from hierarchy-parser.md

**Outputs**: `{ passed: boolean, failures: Array<{ artifact: Artifact, reason: string }> }`
**Error handling**: Returns `{ passed: true }` if no contract entry for this child (no requirements).

```javascript
function verifyPrerequisites(child, contractMatrix) {
  // Find contract entry for this child — match on seq prefix or child name
  const childId = extractChildId(child.path)
  const contract = contractMatrix.find(c => c.child === childId || c.child.startsWith(child.seq))

  if (!contract || contract.requires.length === 0) {
    return { passed: true, failures: [] }
  }

  const failures = []

  for (const artifact of contract.requires) {
    // Optional artifacts — warn but do not block
    if (artifact.optional) {
      const result = verifyArtifact(artifact)
      if (!result.verified) {
        warn(`Optional prerequisite missing (non-blocking): ${artifact.type}:${artifact.name}`)
      }
      continue
    }

    const result = verifyArtifact(artifact)
    if (!result.verified) {
      failures.push({ artifact, reason: result.reason || "Verification failed" })
    }
  }

  return {
    passed: failures.length === 0,
    failures
  }
}

// Extract child ID from plan path: "plans/children/01-data-layer-plan.md" → "01-data-layer"
function extractChildId(path) {
  const basename = path.split("/").pop().replace(".md", "")
  return basename.replace(/-plan$/, "")
}
```

---

## verifyProvides(child, contractMatrix)

Verify that a child plan produced all promised artifacts after arc execution completes.

**Inputs**:
- `child` — execution table entry
- `contractMatrix` — output of `parseDependencyContractMatrix()`

**Outputs**: `{ passed: boolean, failures: Array<{ artifact: Artifact, reason: string }> }`
**Error handling**: Returns `{ passed: true }` if no provides contract for this child.

```javascript
function verifyProvides(child, contractMatrix) {
  const childId = extractChildId(child.path)
  const contract = contractMatrix.find(c => c.child === childId || c.child.startsWith(child.seq))

  if (!contract || contract.provides.length === 0) {
    return { passed: true, failures: [] }
  }

  const failures = []

  for (const artifact of contract.provides) {
    const result = verifyArtifact(artifact)
    if (!result.verified) {
      // Optional provides are warnings only
      if (artifact.optional) {
        warn(`Optional provides artifact missing: ${artifact.type}:${artifact.name} — ${result.reason}`)
        continue
      }
      failures.push({ artifact, reason: result.reason || "Artifact not found after completion" })
    }
  }

  return {
    passed: failures.length === 0,
    failures
  }
}
```

---

## Resolution Strategies

When `verifyPrerequisites` returns `passed: false`, the orchestrator invokes `handlePrerequisiteFailure`.

**Resolution options:**
- `pause` — ask user with 4 options (default strategy)
- `self-heal` — inject missing work into the predecessor child plan and re-run
- `backtrack` — reset predecessor to pending, inject `[BACKTRACK]` tasks, max 1 per child
- `skip` — skip this child and continue to next executable

```javascript
async function handlePrerequisiteFailure(child, prereqResult, contractMatrix) {
  log(`Prerequisite verification failed for child [${child.seq}]: ${child.path}`)
  for (const f of prereqResult.failures) {
    log(`  MISSING: ${f.artifact.type}:${f.artifact.name} — ${f.reason}`)
  }

  // Default strategy: pause and ask user
  const userChoice = AskUserQuestion({
    questions: [{
      question: `Child [${child.seq}] is missing ${prereqResult.failures.length} prerequisite(s). How to proceed?`,
      header: "Prerequisite Verification Failed",
      options: [
        {
          label: "Pause — I'll fix prerequisites manually",
          description: "Execution pauses here. Re-run /rune:arc-hierarchy --resume when ready."
        },
        {
          label: "Self-heal — inject missing work into predecessor",
          description: "Appends [SELF-HEAL] tasks to predecessor child plan and re-runs it."
        },
        {
          label: "Backtrack — reset predecessor and re-run",
          description: "Resets predecessor status to pending. Appends [BACKTRACK] tasks. Max 1 per child."
        },
        {
          label: "Skip this child",
          description: "Mark as skipped. Dependent children will also be blocked."
        }
      ],
      multiSelect: false
    }]
  })

  switch (userChoice) {
    case "Self-heal — inject missing work into predecessor":
      return await selfHeal(child, prereqResult, contractMatrix)
    case "Backtrack — reset predecessor and re-run":
      return await backtrack(child, prereqResult, contractMatrix)
    case "Skip this child":
      return "skip"
    default: // Pause
      error("Execution paused. Fix prerequisites and run /rune:arc-hierarchy --resume to continue.")
      return "abort"
  }
}
```

### Self-Heal Strategy

Inject missing artifact generation tasks into the predecessor plan that was supposed to provide them.

**Constraint (SEC-4)**: If the predecessor plan has no `## Acceptance Criteria` section, use Write-append fallback to create one rather than failing.

```javascript
async function selfHeal(child, prereqResult, contractMatrix) {
  // Find which predecessor was supposed to provide the missing artifacts
  const missingArtifacts = prereqResult.failures.map(f => f.artifact)

  // Find predecessor(s) that should provide these artifacts
  const predecessorChildren = contractMatrix.filter(c =>
    c.provides.some(p =>
      missingArtifacts.some(m => m.type === p.type && m.name === p.name)
    )
  )

  if (predecessorChildren.length === 0) {
    warn("Self-heal: Cannot determine which predecessor should provide missing artifacts.")
    warn("Falling back to pause strategy.")
    return "abort"
  }

  for (const predecessor of predecessorChildren) {
    // Find the plan path for this predecessor
    const executionTable = parseExecutionTable(Read(/* current parent plan path */))
    const predEntry = executionTable.find(e => extractChildId(e.path) === predecessor.child)
    if (!predEntry) continue

    const predContent = Read(predEntry.path)
    if (!predContent) {
      warn(`Self-heal: Cannot read predecessor plan: ${predEntry.path}`)
      continue
    }

    // Build [SELF-HEAL] task entries for missing artifacts
    const healTasks = missingArtifacts
      .filter(a => predecessor.provides.some(p => p.type === a.type && p.name === a.name))
      .map(a => `- [SELF-HEAL] Produce missing artifact: ${a.type}:${a.name}`)
      .join("\n")

    if (!healTasks) continue

    // SEC-4: Append to ## Acceptance Criteria if exists, else create the section
    if (predContent.includes("## Acceptance Criteria")) {
      const updated = predContent.replace(
        /(## Acceptance Criteria[\s\S]*?)(\n## |\Z)/,
        `$1\n\n**[SELF-HEAL] Missing Artifact Tasks:**\n${healTasks}\n$2`
      )
      Write(predEntry.path, updated)
    } else {
      // Write-append fallback (SEC-4): create the section at end of file
      const appendContent = `\n\n## Acceptance Criteria\n\n**[SELF-HEAL] Missing Artifact Tasks (auto-injected):**\n${healTasks}\n`
      // Use Write with full content + appended section
      Write(predEntry.path, predContent + appendContent)
      warn(`Self-heal: Created "## Acceptance Criteria" section in ${predEntry.path} (section was absent)`)
    }

    // Reset predecessor status to pending so it re-runs
    const parentContent = Read(/* parent plan path */)
    const updated = updateExecutionTable(parentContent, predEntry.seq, {
      status: "pending",
      started: "—",
      completed: "—"
    })
    Write(/* parent plan path */, updated)

    log(`Self-heal: Injected ${healTasks.split("\n").length} task(s) into ${predEntry.path}`)
    log(`Self-heal: Reset predecessor [${predEntry.seq}] to pending.`)
  }

  return "retry"  // Loop will pick up predecessor next
}
```

### Backtrack Strategy

Reset the predecessor to `pending`, append `[BACKTRACK]` repair tasks. Max one backtrack per child to prevent infinite loops.

```javascript
// Track backtrack counts per child seq to enforce max 1
const backtrackCounts = {}

async function backtrack(child, prereqResult, contractMatrix) {
  // Enforce max 1 backtrack per child
  const childKey = child.seq
  backtrackCounts[childKey] = (backtrackCounts[childKey] || 0) + 1

  if (backtrackCounts[childKey] > 1) {
    warn(`Backtrack: Child [${child.seq}] has already been backtracked once. Max 1 per child.`)
    warn("Falling back to pause strategy.")
    return "abort"
  }

  // Find the immediate predecessor in the dependency chain
  const deps = child.dependencies
  if (deps.length === 0) {
    warn("Backtrack: No predecessors found. Cannot backtrack.")
    return "abort"
  }

  const parentContent = Read(/* parent plan path */)
  const executionTable = parseExecutionTable(parentContent)

  for (const depSeq of deps) {
    const predEntry = executionTable.find(e => normalizeSeq(e.seq) === normalizeSeq(depSeq))
    if (!predEntry) continue

    const predContent = Read(predEntry.path)
    if (!predContent) continue

    // Build [BACKTRACK] task entries
    const backtrackTasks = prereqResult.failures
      .map(f => `- [BACKTRACK] Repair missing: ${f.artifact.type}:${f.artifact.name}`)
      .join("\n")

    // Append to plan
    if (predContent.includes("## Acceptance Criteria")) {
      const updated = predContent.replace(
        /(## Acceptance Criteria[\s\S]*?)(\n## |\Z)/,
        `$1\n\n**[BACKTRACK] Repair Tasks:**\n${backtrackTasks}\n$2`
      )
      Write(predEntry.path, updated)
    } else {
      // SEC-4: Write-append fallback
      Write(predEntry.path, predContent + `\n\n## Acceptance Criteria\n\n**[BACKTRACK] Repair Tasks (auto-injected):**\n${backtrackTasks}\n`)
    }

    // Reset predecessor to pending
    const updated = updateExecutionTable(parentContent, predEntry.seq, {
      status: "pending",
      started: "—",
      completed: "—"
    })
    Write(/* parent plan path */, updated)

    log(`Backtrack: Injected repair tasks into [${predEntry.seq}]. Reset to pending.`)
  }

  return "retry"
}
```
