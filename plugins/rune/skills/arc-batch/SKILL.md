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

Executes `/rune:arc` across multiple plan files sequentially. Each arc run completes the full 20-phase pipeline (forge through merge) before the next plan starts.

**Core loop**: Stop hook pattern (ralph-wiggum). Each arc runs as a native Claude Code turn. Between arcs, the Stop hook intercepts session end, reads batch state from `.claude/arc-batch-loop.local.md`, determines the next plan, cleans git state, and re-injects the arc prompt.

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
| `--no-shard-sort` | Process plans in raw order (disable shard auto-sorting) | Off |

## Algorithm

See [batch-algorithm.md](references/batch-algorithm.md) for full pseudocode.

## Inter-Iteration Summaries (v1.72.0)

Between arc iterations, the Stop hook writes a structured summary file capturing metadata from the just-completed arc. These summaries improve compact recovery context and provide a record of what each arc accomplished.

**Location**: `tmp/arc-batch/summaries/iteration-{N}.md` (flat path — no PID subdirectory; session isolation is handled by Guard 5.7 in the Stop hook).

**Contents**: Plan path, status, branch name, PR URL, git log (last 5 commits), and a `## Context Note` section where Claude adds a brief qualitative summary during the next turn.

**Behavior**:
- Summaries are written BEFORE marking the plan as completed (crash-safe ordering)
- Write failures are non-blocking — the batch continues without a summary
- ARC_PROMPT step 4.5 is conditional: only injected when a summary was successfully written
- `arc.batch.summaries.enabled: false` in talisman.yml disables all summary behavior
- Max summary content is hardcoded to 30 lines for v1 (not talisman-configurable)

**Compact recovery**: The `pre-compact-checkpoint.sh` hook captures `arc_batch_state` (current iteration, total plans, latest summary path) in the compact checkpoint. On recovery, the session-compact-recovery hook includes batch iteration context in the injected message.

## Known Limitations (V2 — Stop Hook Pattern)

1. **Sequential only**: No parallel arc execution (SDK one-team-per-session constraint).
2. **No version bump coordination**: Multiple arcs bumping plugin.json will conflict.
3. **Shard ordering is sequential**: Shards are auto-sorted by number within groups but execute sequentially (no parallel shards). Use `--no-shard-sort` to disable auto-sorting.
4. **Context growth**: Each arc runs as a native turn. Auto-compaction handles context window growth across multiple arcs. State is tracked in files, not context.
5. **Compact recovery during arc-batch**: Teams are created/destroyed per phase. Compaction may hit when no team is active. Summary files persist independently — the compact checkpoint captures batch state even without an active team (C6 accepted limitation).

## Orchestration

The skill orchestrates via `$ARGUMENTS` parsing. Phase 5 writes a state file and invokes the first arc natively. The Stop hook (`scripts/arc-batch-stop-hook.sh`) handles all subsequent plans via self-invoking loop:

```
Phase 0: Parse arguments (glob expand or queue file read)
Phase 1: Pre-flight validation (arc-batch-preflight.sh)
Phase 2: Dry run (if --dry-run)
Phase 3: Initialize batch-progress.json
Phase 4: Confirm batch with user
Phase 5: Write state file + invoke first arc (Stop hook handles rest)
(Stop hook handles all subsequent plans + final summary)
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
  // P1-FIX: Filter to pending plans only — don't re-execute completed plans
  const allPlans = progress.plans
  const pendingPlans = allPlans.filter(p => p.status === "pending")
  planPaths = pendingPlans.map(p => p.path)
  log(`Resuming batch: ${allPlans.filter(p => p.status === "completed").length}/${allPlans.length} completed, ${planPaths.length} remaining`)
  if (planPaths.length === 0) {
    log("All plans already completed. Nothing to resume.")
    return
  }
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

// ── SHARD GROUP DETECTION (v1.66.0+, after initial plan list construction) ──
const noShardSort = args.includes('--no-shard-sort')
// readTalisman: SDK Read() with project→global fallback. See references/read-talisman.md
const talisman = readTalisman()
const shardConfig = talisman?.arc?.sharding ?? {}
const shardEnabled = shardConfig.enabled !== false  // default: true (PS-007 FIX: honor master enabled flag)
const autoSort = shardConfig.auto_sort !== false  // default: true
const excludeParent = shardConfig.exclude_parent !== false  // default: true

if (!noShardSort && shardEnabled && autoSort && !resumeMode && planPaths.length > 1) {
  // Separate shard plans from regular plans
  const shardPlans = []
  const regularPlans = []
  const parentPlansToExclude = []

  for (const path of planPaths) {
    const shardMatch = path.match(/-shard-(\d+)-/)
    if (shardMatch) {
      shardPlans.push({
        path,
        shardNum: parseInt(shardMatch[1]),
        // Extract feature prefix: everything before "-shard-N-{phase}-plan.md"
        // Consistent regex with Task 1.1 and parse-plan.md
        featurePrefix: path.replace(/-shard-\d+-[^-]+-plan\.md$/, '')
      })
    } else {
      regularPlans.push(path)
    }
  }

  // F-004 FIX: Declare shardGroups in outer scope to avoid block-scoping fragility
  let shardGroups = new Map()

  if (shardPlans.length > 0) {
    // Check for parent plans in regularPlans (auto-exclude if shattered: true)
    const filteredRegular = []
    if (excludeParent) {
      for (const path of regularPlans) {
        try {
          const content = Read(path)
          const frontmatter = extractYamlFrontmatter(content)
          if (frontmatter?.shattered === true) {
            parentPlansToExclude.push(path)
            continue
          }
        } catch (e) {
          // Can't read — keep it
        }
        filteredRegular.push(path)
      }
    } else {
      filteredRegular.push(...regularPlans)
    }

    if (parentPlansToExclude.length > 0) {
      warn(`Auto-excluded ${parentPlansToExclude.length} parent plan(s) (shattered: true):`)
      for (const p of parentPlansToExclude) {
        warn(`  - ${p}`)
      }
    }

    // Group shards by feature prefix
    shardGroups = new Map()  // reset (outer-scope let)
    for (const shard of shardPlans) {
      if (!shardGroups.has(shard.featurePrefix)) {
        shardGroups.set(shard.featurePrefix, [])
      }
      shardGroups.get(shard.featurePrefix).push(shard)
    }

    // Sort each group by shard number
    for (const [prefix, shards] of shardGroups) {
      shards.sort((a, b) => a.shardNum - b.shardNum)
    }

    // Detect missing shards within groups
    for (const [prefix, shards] of shardGroups) {
      const nums = shards.map(s => s.shardNum)
      if (nums.length === 0) continue  // F-002 FIX: guard against Math.max() = -Infinity
      const maxNum = Math.max(...nums)
      const missing = []
      for (let i = 1; i <= maxNum; i++) {
        if (!nums.includes(i)) missing.push(i)
      }
      if (missing.length > 0) {
        warn(`Shard group "${prefix.replace(/.*\//, '')}" has gaps: missing shard(s) ${missing.join(', ')}`)
      }
    }

    // Rebuild plan paths: regular plans first, then shard groups in order
    planPaths = [
      ...filteredRegular,
      ...Array.from(shardGroups.values()).flat().map(s => s.path)
    ]

    log(`Shard-aware ordering: ${filteredRegular.length} regular + ${shardPlans.length} shard plans across ${shardGroups.size} group(s)`)
    if (parentPlansToExclude.length > 0) {
      log(`Excluded ${parentPlansToExclude.length} parent plan(s)`)
    }
  }
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
    schema_version: 2,  // v2: shard metadata (v1.66.0+)
    status: "running",
    started_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    total_plans: planPaths.length,
    // NEW (v1.66.0): shard group summary for progress display
    shard_groups: (shardGroups.size > 0)  // F-004: outer-scope Map, always defined
      ? Array.from(shardGroups.entries()).map(([prefix, shards]) => ({
          feature: prefix.replace(/.*\//, ''),  // basename of prefix
          shards: shards.map(s => s.shardNum),
          total: shards.length
        }))
      : [],
    plans: planPaths.map(p => {
      const shardMatch = p.match(/-shard-(\d+)-/)
      return {
        path: p,
        status: "pending",
        error: null,
        completed_at: null,
        arc_session_id: null,
        // NEW (v1.66.0): shard metadata (null for non-shard plans)
        shard_group: shardMatch ? p.replace(/-shard-\d+-[^/]*$/, '').replace(/.*\//, '') : null,
        shard_num: shardMatch ? parseInt(shardMatch[1]) : null
      }
    })
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

### Phase 5: Start Batch Loop (Stop Hook Pattern)

Write state file for the Stop hook, mark the first plan as in_progress, and invoke `/rune:arc` natively. The Stop hook (`scripts/arc-batch-stop-hook.sh`) handles all subsequent plans and the final summary.

```javascript
const pluginDir = Bash(`echo "${CLAUDE_PLUGIN_ROOT}"`).trim()
const planListFile = "tmp/arc-batch/plan-list.txt"
Write(planListFile, planPaths.join('\n'))

// Merge resolution: CLI --no-merge (highest) → talisman auto_merge → default (true)
// readTalisman: SDK Read() with project→global fallback. See references/read-talisman.md
const talisman = readTalisman()
const batchConfig = talisman?.arc?.batch || {}
const autoMerge = noMerge ? false : (batchConfig.auto_merge ?? true)
const summaryEnabled = batchConfig?.summaries?.enabled !== false  // default: true

// ── Resolve session identity for cross-session isolation ──
// Two isolation layers prevent cross-session interference:
//   Layer 1: config_dir — isolates different Claude Code installations
//   Layer 2: owner_pid — isolates different sessions with same config dir
// $PPID in Bash = Claude Code process PID (Bash runs as child of Claude Code)
const configDir = Bash(`cd "${CLAUDE_CONFIG_DIR:-$HOME/.claude}" 2>/dev/null && pwd -P`).trim()
const ownerPid = Bash(`echo $PPID`).trim()

// ── Pre-creation guard: check for existing batch from another session ──
const existingState = Read(".claude/arc-batch-loop.local.md") // returns null/error if not found
if (existingState && existingState.includes("active: true")) {
  const existingPid = existingState.match(/owner_pid:\s*(\d+)/)?.[1]
  const existingCfg = existingState.match(/config_dir:\s*(.+)/)?.[1]?.trim()

  let ownedByOther = false
  if (existingCfg && existingCfg !== configDir) {
    ownedByOther = true
  }
  if (!ownedByOther && existingPid && /^\d+$/.test(existingPid) && existingPid !== ownerPid) {
    // Check if other session is alive (SEC-1: numeric guard before shell interpolation)
    const alive = Bash(`kill -0 ${existingPid} 2>/dev/null && echo "alive" || echo "dead"`).trim()
    if (alive === "alive") {
      ownedByOther = true
    }
  }

  if (ownedByOther) {
    error("Another session is already running arc-batch on this repo.")
    error("Cancel it first with /rune:cancel-arc-batch, or wait for it to finish.")
    return
  }
  // Owner is dead → orphaned state file. Safe to overwrite.
  warn("Found orphaned batch state file (previous session crashed). Overwriting.")
}

// ── Write state file for Stop hook ──
// Format matches ralph-wiggum's .local.md convention (YAML frontmatter)
Write(".claude/arc-batch-loop.local.md", `---
active: true
iteration: 1
max_iterations: 0
total_plans: ${planPaths.length}
no_merge: ${!autoMerge}
plugin_dir: ${pluginDir}
config_dir: ${configDir}
owner_pid: ${ownerPid}
session_id: ${CLAUDE_SESSION_ID}
plans_file: ${planListFile}
progress_file: ${progressFile}
summary_enabled: ${summaryEnabled}
summary_dir: tmp/arc-batch/summaries
started_at: "${new Date().toISOString()}"
---

Arc batch loop state. Do not edit manually.
Use /rune:cancel-arc-batch to stop the batch loop.
`)
// NOTE: summary_enabled and summary_dir are read by the Stop hook via get_field().
// summary_enabled defaults to true when missing (backward compat with old state files).
// summary_dir is always "tmp/arc-batch/summaries" (flat path per C2 — no PID subdirectory).
// Phase 6 synthetic resume summaries are NOT implemented (C11 — YAGNI).
// On --resume, step 4.5 handles missing summaries via conditional injection.

// ── Mark first pending plan as in_progress ──
// P1-FIX: Find the correct plan entry in progress file by matching path,
// not by index — planPaths[0] is the first *pending* plan (filtered in resume mode).
const firstPlan = planPaths[0]
const progress = JSON.parse(Read(progressFile))
const planEntry = progress.plans.find(p => p.path === firstPlan && p.status === "pending")
if (planEntry) {
  planEntry.status = "in_progress"
  planEntry.started_at = new Date().toISOString()
  progress.updated_at = new Date().toISOString()
  Write(progressFile, JSON.stringify(progress, null, 2))
}

// ── Invoke arc for first plan ──
// Native skill invocation — no subprocess, no timeout limit.
// Each arc runs as a full Claude Code turn with complete tool access.
const mergeFlag = !autoMerge ? " --no-merge" : ""
Skill("arc", `${firstPlan} --skip-freshness${mergeFlag}`)

// After the first arc completes, Claude's response ends.
// The Stop hook fires, reads the state file, marks plan 1 as completed,
// finds plan 2, and re-injects the arc prompt for the next plan.
// This continues until all plans are processed.
```

**How the loop works:**
1. Phase 5 invokes `/rune:arc` for the first plan (native turn)
2. When arc completes, Claude's response ends → Stop event fires
3. `arc-batch-stop-hook.sh` reads `.claude/arc-batch-loop.local.md`
4. Marks current plan as completed in `batch-progress.json`
5. Finds next pending plan
6. Re-injects arc prompt via `{"decision":"block","reason":"<prompt>"}`
7. Claude receives the re-injected prompt → runs next arc
8. Repeat until all plans done
9. On final iteration: removes state file, injects summary prompt
10. Summary turn completes → Stop hook finds no state file → allows session end
