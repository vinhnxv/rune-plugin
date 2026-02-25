# Phase 4.5: TASK DECOMPOSITION — Full Algorithm

Cross-model validation of plan task structure using Codex. Checks granularity, dependencies, file ownership conflicts, and missing tasks. Gated by 5-condition detection.

**Team**: None (orchestrator-only Codex invocation)
**Tools**: Read, Write, Bash (codex-exec.sh)
**Timeout**: 5 min (resolveCodexConfig default: 300s)
**Inputs**: id (string), enriched plan (`tmp/arc/{id}/enriched-plan.md`), talisman config
**Outputs**: `tmp/arc/{id}/task-validation.md`
**Error handling**: Non-blocking — skip path always writes output MD. Cascade circuit breaker prevents repeated Codex failures from stalling the pipeline.
**Consumers**: SKILL.md (Phase 4.5 stub)

> **Note**: `sha256()`, `updateCheckpoint()`, `exists()`, `warn()`, `detectCodex()`, `resolveCodexConfig()`, `classifyCodexError()`, `updateCascadeTracker()`, `sanitizePlanContent()`, and `formatReport()` are dispatcher-provided utilities available in the arc orchestrator context. Phase reference files call these without import.

## Entry Gate (5-Condition Detection)

```javascript
// Phase 4.5: TASK DECOMPOSITION
// 4-condition detection gate (canonical pattern)
const codexAvailable = detectCodex()
const codexDisabled = talisman?.codex?.disabled === true
const taskDecompEnabled = talisman?.codex?.task_decomposition?.enabled !== false
const workflowIncluded = (talisman?.codex?.workflows ?? []).includes("arc")

// 5th condition: cascade circuit breaker (check before the 4-condition pattern)
if (checkpoint.codex_cascade?.cascade_warning === true) {
  Write(`tmp/arc/${id}/task-validation.md`, "# Task Decomposition Validation (Codex)\n\nSkipped: Codex cascade circuit breaker active")
  updateCheckpoint({ phase: "task_decomposition", status: "skipped" })
  // Proceed to Phase 5 (WORK)
  return
}
```

**Gate conditions** (ALL must be true for execution):
1. `detectCodex()` — Codex CLI is installed and reachable
2. `codex.disabled !== true` — Not globally disabled in talisman
3. `codex.task_decomposition.enabled !== false` — Feature-level toggle (default: enabled)
4. `codex.workflows` includes `"arc"` — Arc is in the allowed workflow list
5. `codex_cascade.cascade_warning !== true` — No active cascade circuit breaker

## STEP 1: Prepare Codex Prompt

```javascript
if (codexAvailable && !codexDisabled && taskDecompEnabled && workflowIncluded) {
  const { timeout, reasoning, model: codexModel } = resolveCodexConfig(talisman, "task_decomposition", {
    timeout: 300, reasoning: "high"
  })

  // Read enriched plan for task structure
  const planContent = Read(`tmp/arc/${id}/enriched-plan.md`)
  const todosBase = checkpoint.todos_base ?? `tmp/arc/${id}/todos/`

  // SEC-003: Prompt via temp file (NEVER inline string interpolation)
  const promptTmpFile = `tmp/arc/${id}/.codex-prompt-task-decomp.tmp`
```

**Security note**: The plan content is written to a temp file and passed via `-g` flag to `codex-exec.sh`. This avoids shell injection via inline string interpolation (SEC-003).

## STEP 2: Execute Codex Validation

```javascript
  try {
    const sanitizedPlan = sanitizePlanContent(planContent.substring(0, 10000))
    const promptContent = `SYSTEM: You are a cross-model task decomposition validator.

Analyze this plan's task structure for decomposition quality:

=== PLAN ===
${sanitizedPlan}
=== END PLAN ===

For each finding, provide:
- CDX-TASK-NNN: [CRITICAL|HIGH|MEDIUM] - description
- Category: Granularity / Dependency / File Conflict / Missing Task
- Suggested fix (brief)

Check for:
1. Tasks too large (>3 files or >200 lines estimated) — recommend splitting
2. Missing inter-task dependencies (task B reads output of task A but no blockedBy)
3. File ownership conflicts (multiple tasks modifying the same file)
4. Missing tasks (plan sections with no corresponding task)

Base findings on actual plan content, not assumptions.`

    Write(promptTmpFile, promptContent)
    const result = Bash(`"${CLAUDE_PLUGIN_ROOT}/scripts/codex-exec.sh" -m "${codexModel}" -r "${reasoning}" -t ${timeout} -j -g "${promptTmpFile}"`)
    const classified = classifyCodexError(result)

    // Update cascade tracker
    updateCascadeTracker(checkpoint, classified)

    // Write output (even on error — CDX-TASK prefix)
    Write(`tmp/arc/${id}/task-validation.md`, formatReport(classified, result, "Task Decomposition Validation"))
    updateCheckpoint({ phase: "task_decomposition", status: "completed", artifact: `tmp/arc/${id}/task-validation.md` })
  } finally {
    Bash(`rm -f "${promptTmpFile}"`)  // Guaranteed cleanup
  }
```

### Finding Categories

| Category | Trigger | Example |
|----------|---------|---------|
| Granularity | Task touches >3 files or >200 estimated lines | "Split auth-setup into auth-middleware + auth-routes" |
| Dependency | Task B reads output of task A without `blockedBy` | "auth-tests should depend on auth-middleware" |
| File Conflict | Multiple tasks modify the same file | "Both user-model and user-api modify models/user.ts" |
| Missing Task | Plan section has no corresponding task | "Database migration section has no task" |

### Cascade Circuit Breaker

The cascade tracker (shared across all Codex phases) prevents repeated Codex failures from stalling the pipeline. If prior Codex phases (semantic verification, gap analysis) have accumulated failures, `cascade_warning` is set to `true` and task decomposition is skipped.

See [arc-codex-phases.md](arc-codex-phases.md) for the cascade tracker algorithm and threshold configuration.

## STEP 3: Skip Path

```javascript
} else {
  // Skip-path: MUST write output MD (depth-seer critical finding)
  const skipReason = !codexAvailable ? "codex not available"
    : codexDisabled ? "codex.disabled=true"
    : !taskDecompEnabled ? "codex.task_decomposition.enabled=false"
    : "arc not in codex.workflows"
  Write(`tmp/arc/${id}/task-validation.md`, `# Task Decomposition Validation (Codex)\n\nSkipped: ${skipReason}`)
  updateCheckpoint({ phase: "task_decomposition", status: "skipped" })
}
// Proceed to Phase 5 (WORK)
```

**Critical**: The skip path MUST always write `task-validation.md`. Downstream phases and gap analysis may reference this file. An empty skip produces a clear audit trail.

**Output**: `tmp/arc/{id}/task-validation.md` with CDX-TASK-prefixed findings (or skip reason)

**Failure policy**: Non-blocking. Codex errors are classified and recorded but never halt the pipeline. The cascade tracker ensures repeated failures trigger early skip in subsequent Codex phases.
