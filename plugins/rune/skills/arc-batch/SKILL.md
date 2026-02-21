---
name: arc-batch
description: |
  Batch execution of /rune:arc across multiple plan files.
  Runs each plan sequentially with auto-merge, crash recovery, and progress tracking.
  Use when you have multiple plans to implement overnight or in batch.

  <example>
  Context: User has multiple plans to implement
  user: "/rune:arc-batch plans/*.md"
  assistant: "The Tarnished begins the batch arc pipeline..."
  </example>

  <example>
  Context: User has a queue file
  user: "/rune:arc-batch batch-queue.txt"
  assistant: "Reading plan queue from batch-queue.txt..."
  </example>
user-invocable: true
disable-model-invocation: true
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, AskUserQuestion
argument-hint: "[plans/*.md | queue-file.txt] [--resume] [--dry-run] [--no-merge]"
---

# /rune:arc-batch — Sequential Batch Arc Execution

Executes `/rune:arc` across multiple plan files sequentially. Each arc run completes the full 17-phase pipeline (forge through merge) before the next plan starts.

**Core loop**: For each plan -> run arc (forge through merge) -> checkout main -> pull latest -> clean state -> next plan.

## Usage

```
/rune:arc-batch plans/*.md                    # All plans matching glob
/rune:arc-batch batch-queue.txt               # Queue file (one plan path per line)
/rune:arc-batch plans/*.md --dry-run          # Preview queue without running
/rune:arc-batch plans/*.md --no-merge         # Skip auto-merge (individual PRs remain open)
/rune:arc-batch --resume                      # Resume interrupted batch from progress file
```

## Flags

| Flag | Description | Default |
|------|-------------|---------|
| `--dry-run` | List plans and exit without running | Off |
| `--no-merge` | Pass `--no-merge` to each arc run | Off (auto-merge enabled) |
| `--resume` | Resume from `batch-progress.json` | Off |

## Algorithm

See [batch-algorithm.md](references/batch-algorithm.md) for full pseudocode.

## Known Limitations (V1)

1. **Sequential only**: No parallel arc execution (SDK one-team-per-session constraint).
2. **No version bump coordination**: Multiple arcs bumping plugin.json will conflict.
3. **No dependency ordering**: Plans processed in given order.
4. **Headless security tradeoff**: `--dangerously-skip-permissions` bypasses all permission prompts and hook-based enforcement. Ensure all plans are trusted.

## Orchestration

The skill orchestrates via `$ARGUMENTS` parsing and invokes `scripts/arc-batch.sh` for the batch loop:

```
Phase 0: Parse arguments (glob expand or queue file read)
Phase 1: Pre-flight validation (arc-batch-preflight.sh)
Phase 2: Dry run (if --dry-run)
Phase 3: Initialize batch-progress.json
Phase 4: Confirm batch with user
Phase 5: Run batch (arc-batch.sh)
Phase 6: Present summary
```

### Phase 0: Parse Arguments

```javascript
const args = "$ARGUMENTS".trim()
let planPaths = []
let resumeMode = args.includes('--resume')
let dryRun = args.includes('--dry-run')
let noMerge = args.includes('--no-merge')

if (resumeMode) {
  const progress = JSON.parse(Read("tmp/arc-batch/batch-progress.json"))
  planPaths = progress.plans.map(p => p.path)
  log(`Resuming batch: ${progress.plans.filter(p => p.status === "completed").length}/${planPaths.length} completed`)
} else {
  const inputArg = args.replace(/--\S+/g, '').trim()
  if (inputArg.endsWith('.txt')) {
    planPaths = Read(inputArg).split('\n').filter(l => l.trim() && !l.startsWith('#'))
  } else {
    planPaths = Glob(inputArg)
  }
}

if (planPaths.length === 0) {
  error("No plan files found. Usage: /rune:arc-batch plans/*.md")
  return
}
```

### Phase 1: Pre-flight Validation

```javascript
// SEC-007 FIX: Write paths to temp file first to avoid shell injection via echo interpolation.
// Queue file paths (untrusted input) could contain shell metacharacters.
Write("tmp/arc-batch/preflight-input.txt", planPaths.join('\n'))
const validated = Bash(`"${CLAUDE_PLUGIN_ROOT}/scripts/arc-batch-preflight.sh" < "tmp/arc-batch/preflight-input.txt"`)
if (validated.exitCode !== 0) {
  error("Pre-flight validation failed. Fix errors above and retry.")
  return
}
planPaths = validated.stdout.trim().split('\n')

// Check auto-merge setting (unless --no-merge)
if (!noMerge) {
  // readTalisman: SDK Read() with project→global fallback. See references/read-talisman.md
  const talisman = readTalisman()
  if (talisman?.arc?.ship?.auto_merge === false) {
    warn("talisman.yml has arc.ship.auto_merge: false")
    AskUserQuestion({
      questions: [{
        question: "Auto-merge is disabled in talisman.yml. How to proceed?",
        header: "Merge",
        options: [
          { label: "Enable auto-merge for this batch", description: "Temporarily set auto_merge: true" },
          { label: "Run with --no-merge", description: "PRs created but not merged" },
          { label: "Abort", description: "Fix talisman config first" }
        ],
        multiSelect: false
      }]
    })
  }
}
```

### Phase 2: Dry Run

```javascript
if (dryRun) {
  log("Dry run — plans that would be processed:")
  for (const [i, plan] of planPaths.entries()) {
    log(`  ${i + 1}. ${plan}`)
  }
  log(`\nTotal: ${planPaths.length} plans`)
  log(`Estimated time: ${planPaths.length * 45}-${planPaths.length * 240} minutes`)
  return
}
```

### Phase 3: Initialize Progress File

```javascript
const progressFile = "tmp/arc-batch/batch-progress.json"
if (!resumeMode) {
  Bash("mkdir -p tmp/arc-batch")
  Write(progressFile, JSON.stringify({
    schema_version: 1,
    status: "running",
    started_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    total_plans: planPaths.length,
    plans: planPaths.map(p => ({ path: p, status: "pending", error: null, completed_at: null }))
  }, null, 2))
}
```

### Phase 4: Confirm Batch

```javascript
AskUserQuestion({
  questions: [{
    question: `Start batch arc for ${planPaths.length} plans? Estimated ${planPaths.length * 45}-${planPaths.length * 240} minutes.`,
    header: "Confirm",
    options: [
      { label: "Start batch", description: `Process ${planPaths.length} plans sequentially with auto-merge` },
      { label: "Dry run first", description: "Preview the queue and estimates" },
      { label: "Cancel", description: "Abort batch" }
    ],
    multiSelect: false
  }]
})
```

### Phase 5: Run Batch

```javascript
const pluginDir = Bash(`echo "${CLAUDE_PLUGIN_ROOT}"`).trim()
const planListFile = "tmp/arc-batch/plan-list.txt"
Write(planListFile, planPaths.join('\n'))

// Emit state file for workflow discovery
const batchTimestamp = Date.now().toString()
Write(`tmp/.rune-batch-${batchTimestamp}.json`, JSON.stringify({
  team_name: null,
  plans_file: planListFile,
  started: new Date().toISOString(),
  status: "active"
}))

// Read talisman config for batch overrides (3-layer: hardcoded → talisman → future CLI)
const talisman = readTalisman()
const batchConfig = talisman?.arc?.batch || {}

// Validate and clamp config values to safe ranges
const maxRetries = Math.max(1, Math.min(10, batchConfig.max_retries ?? 3))
const maxBudget = Math.max(1.0, Math.min(100.0, batchConfig.max_budget ?? 15.0))
const maxTurns = Math.max(50, Math.min(1000, batchConfig.max_turns ?? 200))
const totalBudget = batchConfig.total_budget != null
  ? Math.max(1.0, Math.min(500.0, batchConfig.total_budget))
  : null
const totalTimeout = batchConfig.total_timeout ?? null
const stopOnDivergence = batchConfig.stop_on_divergence ?? false
const perPlanTimeout = batchConfig.per_plan_timeout != null
  ? Math.max(300, Math.min(14400, batchConfig.per_plan_timeout))
  : 7200

// Merge resolution: CLI --no-merge (highest) → talisman auto_merge → default (true)
// noMerge from Phase 0 is true only when --no-merge CLI flag is present
const autoMerge = noMerge ? false : (batchConfig.auto_merge ?? true)

// Write config file for bash script
Write("tmp/arc-batch/batch-config.json", JSON.stringify({
  plans_file: planListFile,
  plugin_dir: pluginDir,
  progress_file: progressFile,
  no_merge: !autoMerge,
  max_retries: maxRetries,
  max_budget: maxBudget,
  max_turns: maxTurns,
  total_budget: totalBudget,
  total_timeout: totalTimeout,
  stop_on_divergence: stopOnDivergence,
  per_plan_timeout: perPlanTimeout
}, null, 2))

const result = Bash(`"${pluginDir}/scripts/arc-batch.sh" "tmp/arc-batch/batch-config.json"`)

// Update state file
Write(`tmp/.rune-batch-${batchTimestamp}.json`, JSON.stringify({
  team_name: null,
  plans_file: planListFile,
  started: new Date().toISOString(),
  status: "completed",
  completed: new Date().toISOString()
}))
```

### Phase 6: Present Summary

```javascript
const progress = JSON.parse(Read(progressFile))
const completed = progress.plans.filter(p => p.status === "completed")
const failed = progress.plans.filter(p => p.status === "failed")

log("\n--- Batch Summary ---")
log(`Plans: ${completed.length} completed, ${failed.length} failed`)
log(`Duration: ${Math.round(progress.total_duration_s / 60)} minutes`)
log("")

for (const plan of progress.plans) {
  const icon = plan.status === "completed" ? "OK" : plan.status === "failed" ? "FAIL" : "SKIP"
  const err = plan.error && plan.error !== "null" ? ` -- ${plan.error}` : ""
  log(`  [${icon}] ${plan.path}${err}`)
}

if (failed.length > 0) {
  log(`\nFailed plans need manual attention.`)
  log(`Re-run with: /rune:arc-batch --resume`)
}
log(`\nFull progress: ${progressFile}`)
log(`Run logs: tmp/arc-batch/`)
```
