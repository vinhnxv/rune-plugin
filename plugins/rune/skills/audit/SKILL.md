---
name: audit
description: |
  Full codebase audit using Agent Teams. Sets scope=full and depth=deep (by default),
  then delegates to the shared Roundtable Circle orchestration phases.
  Summons up to 7 built-in Ashes (plus custom from talisman.yml). Optional `--deep`
  runs multi-wave investigation with deep Ashes. Supports `--focus` for targeted audits.
  Supports `--incremental` for stateful, prioritized batch auditing with 3-tier coverage
  tracking (file, workflow, API) and session-persistent audit history.

  <example>
  user: "/rune:audit"
  assistant: "The Tarnished convenes the Roundtable Circle for audit..."
  </example>

  <example>
  user: "/rune:audit --incremental"
  assistant: "The Tarnished initiates incremental audit — scanning manifest, scoring priorities..."
  </example>

  <example>
  user: "/rune:audit --incremental --status"
  assistant: "Incremental Audit Coverage Report: 55.3% file coverage..."
  </example>
user-invocable: true
disable-model-invocation: false
argument-hint: "[--deep] [--focus <area>] [--max-agents <N>] [--dry-run] [--no-lore] [--deep-lore] [--standard] [--todos-dir <path>] [--incremental] [--resume] [--status] [--reset] [--tier <file|workflow|api|all>] [--force-files <glob>]"
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
  - Bash
  - Glob
  - Grep
  - AskUserQuestion
---

**Runtime context** (preprocessor snapshot):
- Active workflows: !`ls tmp/.rune-*-*.json 2>/dev/null | grep -c '"active"' || echo 0`
- Current branch: !`git branch --show-current 2>/dev/null || echo "n/a"`

# /rune:audit — Full Codebase Audit

Thin wrapper that sets audit-specific parameters, then delegates to the shared Roundtable Circle orchestration. Unlike `/rune:appraise` (which reviews changed files via git diff), `/rune:audit` scans the entire project.

**Load skills**: `roundtable-circle`, `context-weaving`, `rune-echoes`, `rune-orchestration`, `codex-cli`, `polling-guard`, `zsh-compat`

## Flags

| Flag | Description | Default |
|------|-------------|---------|
| `--focus <area>` | Limit audit to specific area: `security`, `performance`, `quality`, `frontend`, `docs`, `backend`, `full` | `full` |
| `--max-agents <N>` | Cap maximum Ash summoned (1-8, including custom) | All selected |
| `--dry-run` | Show scope selection and Ash plan without summoning agents | Off |
| `--no-lore` | Disable Phase 0.5 Lore Layer (git history risk scoring) | Off |
| `--deep-lore` | Run Lore Layer on ALL files (default: Tier 1 only) | Off |
| `--deep` | Run multi-wave deep audit with deep investigation Ashes | On (default for audit) |
| `--standard` | Override default deep mode — run single-wave standard audit | Off |
| `--todos-dir <path>` | Override base todos directory (used by arc to scope todos to `tmp/arc/{id}/todos/`). Threaded to roundtable-circle Phase 5.4 | None |
| `--incremental` | Enable incremental stateful audit — prioritized batch selection with persistent audit history | Off |
| `--resume` | Resume interrupted incremental audit from checkpoint | Off |
| `--status` | Show coverage report only (no audit performed) | Off |
| `--reset` | Reset incremental audit history and start fresh | Off |
| `--tier <tier>` | Limit incremental audit to specific tier: `file`, `workflow`, `api`, `all` | `all` |
| `--force-files <glob>` | Force specific files into incremental batch regardless of priority score | None |

**Note:** Unlike `/rune:appraise`, there is no `--partial` flag. Audit always scans the full project.

**Flag interactions**: `--incremental` and `--deep` are orthogonal. `--incremental --deep` runs incremental file selection (batch) followed by deep investigation Ashes on the selected batch. `--incremental --focus` applies focus filtering BEFORE priority scoring (reduces candidate set, then scores within that set).

**Focus mode** selects only the relevant Ash (see [circle-registry.md](../roundtable-circle/references/circle-registry.md) for the mapping).

**Max agents** reduces team size when context or cost is a concern. Priority order: Ward Sentinel > Forge Warden > Veil Piercer > Pattern Weaver > Glyph Scribe > Knowledge Keeper > Codex Oracle.

## Preamble: Set Parameters

```javascript
// Parse depth: audit defaults to deep (unlike appraise which defaults to standard)
const depth = flags['--standard']
  ? "standard"
  : (flags['--deep'] !== false && (talisman?.audit?.always_deep !== false))
    ? "deep"
    : "standard"

const audit_id = Bash(`date +%Y%m%d-%H%M%S`).trim()
const isIncremental = flags['--incremental'] === true
  && (talisman?.audit?.incremental?.enabled !== false)
```

## Phase 0: Pre-flight

<!-- DELEGATION-CONTRACT: Changes to Phase 0 steps must be reflected in skills/arc/references/arc-delegation-checklist.md -->

```bash
# Scan all project files (excluding non-project directories)
all_files=$(find . -type f \
  ! -path '*/.git/*' \
  ! -path '*/node_modules/*' \
  ! -path '*/__pycache__/*' \
  ! -path '*/tmp/*' \
  ! -path '*/dist/*' \
  ! -path '*/build/*' \
  ! -path '*/.next/*' \
  ! -path '*/.venv/*' \
  ! -path '*/venv/*' \
  ! -path '*/target/*' \
  ! -path '*/.tox/*' \
  ! -path '*/vendor/*' \
  ! -path '*/.cache/*' \
  | sort)

# Optional: get branch name for metadata (not required — audit works without git)
branch=$(git branch --show-current 2>/dev/null || echo "n/a")
```

**Abort conditions:**
- No files found -> "No files to audit in current directory."
- Only non-reviewable files -> "No auditable code found."

**Note:** Unlike `/rune:appraise`, audit does NOT require a git repository.

## Phase 0.1-0.4: Incremental Layer (conditional)

**Gate**: Only runs when `isIncremental === true`. When `--incremental` is NOT set, these phases are skipped entirely with zero overhead — the full `all_files` list passes directly to Phase 0.5.

```javascript
// ── NON-INCREMENTAL EARLY RETURN (Concern 1: regression safety) ──
if (!isIncremental) {
  // Zero-overhead pass-through — all_files unchanged
  // This ensures default /rune:audit behavior is IDENTICAL to pre-incremental
  goto "Load Custom Ashes"
}
```

### Phase 0.0: Status-Only Exit

```javascript
if (flags['--status']) {
  // Report-only mode — no audit, no teams, no state changes
  // Read state files + generate coverage report
  // See coverage-report.md for template
  const state = Read(".claude/audit-state/state.json")
  if (!state) {
    log("No incremental audit state found. Run /rune:audit --incremental first.")
    return
  }
  // Generate and display coverage report
  // See references/coverage-report.md
  return
}
```

### Phase 0.0.5: Reset (conditional)

```javascript
if (flags['--reset']) {
  // Remove all state files, preserve history/archive
  Bash(`rm -f .claude/audit-state/state.json .claude/audit-state/manifest.json \
    .claude/audit-state/workflows.json .claude/audit-state/apis.json \
    .claude/audit-state/checkpoint.json .claude/audit-state/coverage-report.md`)
  Bash(`rm -rf .claude/audit-state/.lock`)
  log("Incremental audit state reset. Starting fresh.")
}
```

### Phase 0.1: Acquire Lock & Init State Directory

```javascript
// Create state directory if needed
Bash(`mkdir -p .claude/audit-state/history/archive`)

// Clean up leftover temp files from previous crashes
Bash(`for f in .claude/audit-state/*.tmp; do [ -f "$f" ] && rm -f "$f"; done`)

// Acquire advisory lock (mkdir-based TOCTOU-hardened)
// See references/incremental-state-schema.md "Locking Protocol"
const lockDir = ".claude/audit-state/.lock"
const lockAcquired = Bash(`mkdir "${lockDir}" 2>/dev/null && echo "ACQUIRED" || echo "EXISTS"`)
if (lockAcquired === "EXISTS") {
  // Check if lock is stale (dead PID, different config_dir)
  const lockMeta = Read(`${lockDir}/meta.json`)
  if (lockMeta?.config_dir !== configDir) {
    log("Lock held by different installation — skipping incremental")
    goto "Load Custom Ashes"  // Fall back to full audit
  }
  // PID liveness check (Concern 3: check for "node" not "claude")
  const pidAlive = Bash(`kill -0 ${lockMeta.pid} 2>/dev/null && ps -p ${lockMeta.pid} -o comm= | grep -q node && echo "alive" || echo "dead"`)
  if (pidAlive === "alive") {
    log("Another audit session (PID ${lockMeta.pid}) is active — skipping incremental update")
    goto "Load Custom Ashes"  // Fall back to full audit
  }
  // Stale lock — clean up and retry
  Bash(`rm -rf "${lockDir}"`)
  Bash(`mkdir "${lockDir}" 2>/dev/null || true`)
}
// Write lock metadata
Write(`${lockDir}/meta.json`, {
  pid: ownerPid, config_dir: configDir,
  started_at: new Date().toISOString(), session_id: sessionId,
  heartbeat_at: new Date().toISOString()
})
```

### Phase 0.1.5: Resume Check

```javascript
if (flags['--resume']) {
  const checkpoint = Read(".claude/audit-state/checkpoint.json")
  if (checkpoint?.status === "active") {
    // Validate session ownership
    const cpPidAlive = Bash(`kill -0 ${checkpoint.owner_pid} 2>/dev/null && echo "alive" || echo "dead"`)
    if (checkpoint.config_dir === configDir && cpPidAlive === "dead") {
      // Stale checkpoint from dead session — resume
      log(`Resuming from checkpoint: ${checkpoint.completed.length}/${checkpoint.batch.length} completed`)
      const remainingBatch = checkpoint.batch.filter(f => !checkpoint.completed.includes(f))
      all_files = remainingBatch
      goto "Load Custom Ashes"  // Skip re-scoring, use checkpoint batch
    }
    if (checkpoint.config_dir !== configDir) {
      log("Checkpoint belongs to different installation — starting fresh")
    }
  } else {
    log("No active checkpoint found — starting fresh incremental audit")
  }
}
```

### Phase 0.2: Build Manifest (Codebase Mapper)

See [codebase-mapper.md](references/codebase-mapper.md) for the full protocol.

```javascript
// Load previous manifest for warm-run optimization
const prevManifest = Read(".claude/audit-state/manifest.json")
const isGitRepo = Bash(`git rev-parse --is-inside-work-tree 2>/dev/null || echo "false"`).trim()

let manifest
if (isGitRepo === "true") {
  // Check for warm-run (no new commits since last scan)
  if (prevManifest?.last_commit_hash) {
    const newCommits = Bash(`git rev-list --count ${prevManifest.last_commit_hash}..HEAD 2>/dev/null || echo "-1"`)
    if (newCommits === "0") {
      log("Warm run: no new commits — reusing cached manifest")
      manifest = prevManifest
      goto "Phase 0.3"
    }
  }

  // Batch git metadata extraction (4 commands, not per-file)
  // 1. Current hash per tracked file
  const lsFiles = Bash(`git ls-files -s`)
  // 2. Last modification per file (--since="1 year" ceiling — Concern 2)
  const gitLog = Bash(`git log --all --format="%H %aI" --name-only --since="1 year"`)
  // 3. Contributors + churn (90-day window)
  const gitStats = Bash(`git log --since="90 days ago" --format="%H %aN" --numstat`)
  // 4. File creation dates
  const gitCreation = Bash(`git log --all --diff-filter=A --format="%aI %H" --name-only --since="1 year"`)

  // Build manifest entries from parsed git data
  manifest = buildManifestFromGit(all_files, lsFiles, gitLog, gitStats, gitCreation)
} else {
  // Non-git fallback: mtime-based metadata
  manifest = buildManifestFromFilesystem(all_files)
}

manifest.last_commit_hash = isGitRepo === "true"
  ? Bash(`git rev-parse HEAD`).trim() : null
manifest.updated_at = new Date().toISOString()

// Apply extra_skip_patterns from talisman
const skipPatterns = talisman?.audit?.incremental?.extra_skip_patterns || []
for (const pattern of skipPatterns) {
  // Mark matching files as "excluded"
  manifest = applySkipPattern(manifest, pattern)
}

// Atomic write manifest
Write(".claude/audit-state/manifest.json", manifest)
```

### Phase 0.3: Manifest Diff & State Reconciliation

```javascript
const state = Read(".claude/audit-state/state.json") || initFreshState()

// Compute diff between current and previous manifest
if (prevManifest) {
  const diff = diffManifest(manifest, prevManifest)
  log(`Manifest diff: +${diff.added.length} added, ~${diff.modified.length} modified, -${diff.deleted.length} deleted`)

  // Mark modified files as "stale" in state
  for (const path of diff.modified) {
    if (state.files[path]) {
      state.files[path].changed_since_audit = true
      state.files[path].status = "stale"
    }
  }

  // Add new files to state as "never_audited"
  for (const path of diff.added) {
    state.files[path] = {
      status: "never_audited", audit_count: 0, coverage_gap_streak: 0,
      consecutive_error_count: 0, previous_paths: [], findings: { P1: 0, P2: 0, P3: 0, total: 0 }
    }
  }

  // Mark deleted files
  for (const path of diff.deleted) {
    if (state.files[path]) {
      state.files[path].status = "deleted"
    }
  }
}

// Reconcile: paths in manifest not in state → add as never_audited
// See references/incremental-state-schema.md "Manifest-State Reconciliation"
for (const path in manifest.files) {
  if (manifest.files[path].status !== "excluded" && !state.files[path]) {
    state.files[path] = {
      status: "never_audited", audit_count: 0, coverage_gap_streak: 0,
      consecutive_error_count: 0, previous_paths: [], findings: { P1: 0, P2: 0, P3: 0, total: 0 }
    }
  }
}
```

### Phase 0.3.5: Priority Scoring

See [priority-scoring.md](references/priority-scoring.md) for the full algorithm.

```javascript
// Read and validate weights from talisman (normalize if needed)
const defaultWeights = { staleness: 0.30, recency: 0.25, risk: 0.20, complexity: 0.10, novelty: 0.10, role: 0.05 }
let weights = talisman?.audit?.incremental?.weights || defaultWeights
const weightSum = Object.values(weights).reduce((a, b) => a + b, 0)
if (Math.abs(weightSum - 1.0) > 0.001) {
  log(`Warning: weights sum to ${weightSum}, normalizing to 1.0`)
  for (const key of Object.keys(weights)) weights[key] /= weightSum
}

// Load Lore Layer risk map (if available)
const riskMap = Read("tmp/lore/risk-map.json")  // May be null — default MEDIUM

// Score each auditable file
const scored = []
for (const [path, entry] of Object.entries(manifest.files)) {
  if (entry.status === "excluded") continue
  const stateEntry = state.files[path]
  if (stateEntry?.status === "deleted" || stateEntry?.status === "error_permanent") continue

  const score = (
    weights.staleness  * computeStalenessScore(stateEntry) +
    weights.recency    * computeRecencyScore(entry) +
    weights.risk       * computeRiskScore(path, riskMap) +
    weights.complexity * computeComplexityScore(entry) +
    weights.novelty    * computeNoveltyScore(entry) +
    weights.role       * computeRoleScore(path)
  )

  // Apply error penalty (consecutive_error_count 1-2: -count * 3.0)
  const errorPenalty = (stateEntry?.consecutive_error_count || 0) * 3.0
  scored.push({ path, score: Math.max(0, score - errorPenalty), entry, stateEntry })
}
```

### Phase 0.4: Batch Selection

See [priority-scoring.md](references/priority-scoring.md) "Batch Selection" section.

```javascript
// Apply --focus filter BEFORE scoring (reduces candidate set)
let candidates = scored
if (flags['--focus']) {
  candidates = candidates.filter(f => matchesFocusArea(f.path, flags['--focus']))
}

// Apply --force-files (always include matching files)
const forceFiles = flags['--force-files']
  ? candidates.filter(f => matchGlob(f.path, flags['--force-files']))
  : []

// Apply --tier filter
const tier = flags['--tier'] || 'all'

// Batch selection with composition rules
const batchSize = talisman?.audit?.incremental?.batch_size || 30
const minBatch = talisman?.audit?.incremental?.min_batch_size || 10
const alwaysAudit = talisman?.audit?.incremental?.always_audit || []

const batch = selectBatch(candidates, {
  batchSize, minBatch, alwaysAudit, forceFiles,
  neverAuditedFloor: 5, gapCarryForwardPct: 0.10
})

log(`Incremental batch: ${batch.length} files selected from ${candidates.length} candidates`)

// Write checkpoint for crash resume
Write(".claude/audit-state/checkpoint.json", {
  audit_id, started_at: new Date().toISOString(),
  batch: batch.map(f => f.path), completed: [], current_file: null,
  team_name: `rune-audit-${audit_id}`, status: "active",
  config_dir: configDir, owner_pid: ownerPid, session_id: sessionId
})

// Override all_files with the incremental batch
all_files = batch.map(f => f.path)
```

### Load Custom Ashes

After scanning files, check for custom Ash config:

```
1. Read .claude/talisman.yml (project) or ~/.claude/talisman.yml (global)
2. If ashes.custom[] exists:
   a. Validate: unique prefixes, unique names, resolvable agents, count <= max
   b. Filter by workflows: keep only entries with "audit" in workflows[]
   c. Match triggers against all_files (extension + path match)
   d. Skip entries with fewer matching files than trigger.min_files
3. Merge validated custom Ash with built-in selections
4. Apply defaults.disable_ashes to remove any disabled built-ins
```

See [custom-ashes.md](../roundtable-circle/references/custom-ashes.md) for full schema and validation rules.

### Detect Codex Oracle

See [codex-detection.md](../roundtable-circle/references/codex-detection.md) for the canonical detection algorithm.

## Phase 0.5: Lore Layer (Risk Intelligence)

See [deep-mode.md](references/deep-mode.md) for the full Lore Layer implementation.

**Skip conditions**: non-git repo, `--no-lore`, `talisman.goldmask.layers.lore.enabled === false`, fewer than 5 commits in lookback window (G5 guard).

## Phase 1: Rune Gaze (Scope Selection)

Classify ALL project files by extension. See [rune-gaze.md](../roundtable-circle/references/rune-gaze.md).

**Apply `--focus` filter:** If `--focus <area>` is set, only summon Ash matching that area.
**Apply `--max-agents` cap:** If `--max-agents N` is set, limit selected Ash to N.

**Large codebase warning:** If total reviewable files > 150, log a coverage note.

### Dry-Run Exit Point

If `--dry-run` flag is set, display the plan and stop. No teams, tasks, state files, or agents are created.

## Delegate to Shared Orchestration

Set parameters and execute shared phases from [orchestration-phases.md](../roundtable-circle/references/orchestration-phases.md).

```javascript
// ── Resolve session identity ──
const configDir = Bash(`cd "\${CLAUDE_CONFIG_DIR:-$HOME/.claude}" 2>/dev/null && pwd -P`).trim()
const ownerPid = Bash(`echo $PPID`).trim()

const params = {
  scope: "full",
  depth,
  teamPrefix: "rune-audit",
  outputDir: `tmp/audit/${audit_id}/`,
  stateFilePrefix: "tmp/.rune-audit",
  identifier: audit_id,
  selectedAsh,
  fileList: all_files,
  timeoutMs: 900_000,   // 15 min (audits cover more files than reviews)
  label: "Audit",
  configDir, ownerPid,
  sessionId: "${CLAUDE_SESSION_ID}",
  maxAgents: flags['--max-agents'],
  workflow: "rune-audit",
  focusArea: flags['--focus'] || "full",
  flags, talisman
}

// Execute Phases 1-7 from orchestration-phases.md
// Phase 1: Setup (state file, output dir)
// Phase 2: Forge Team (inscription, signals, tasks)
// Phase 3: Summon (single wave or multi-wave based on depth)
// Phase 4: Monitor (waitForCompletion with audit timeouts)
// Phase 4.5: Doubt Seer (conditional)
// Phase 5: Aggregate (Runebinder → TOME.md)
// Phase 6: Verify (Truthsight)
// Phase 7: Cleanup (shutdown, TeamDelete, state update, Echo persist)
```

### Audit-Specific Post-Orchestration

After orchestration completes:

```javascript
// 1. Truthseer Validator (for high file counts)
if (reviewableFileCount > 100) {
  // Summon Truthseer Validator — see roundtable-circle SKILL.md Phase 5.5
  // Cross-references finding density against file importance
}

// ── Incremental Result Write-Back (Phase 7.5) ──
if (isIncremental) {
  // Read current state
  const state = Read(".claude/audit-state/state.json")
  const checkpoint = Read(".claude/audit-state/checkpoint.json")

  // Parse TOME for findings per file
  const tome = Read(`${outputDir}/TOME.md`)
  const findingsPerFile = parseTomeFindings(tome)

  // Update state.json for each audited file
  for (const filePath of checkpoint.batch) {
    const findings = findingsPerFile[filePath] || { P1: 0, P2: 0, P3: 0, total: 0 }
    const fileManifest = Read(".claude/audit-state/manifest.json")?.files?.[filePath]

    state.files[filePath] = {
      ...state.files[filePath],
      last_audited: new Date().toISOString(),
      last_audit_id: audit_id,
      last_git_hash: fileManifest?.git?.current_hash || null,
      changed_since_audit: false,
      audit_count: (state.files[filePath]?.audit_count || 0) + 1,
      audited_by: [...new Set([...(state.files[filePath]?.audited_by || []), ...selectedAsh])],
      findings,
      status: "audited",
      consecutive_error_count: 0
    }

    // Remove from coverage_gaps if present
    delete state.coverage_gaps?.[filePath]
  }

  // Recompute stats
  const auditable = Object.values(state.files).filter(f => !["excluded","deleted"].includes(f.status))
  const audited = auditable.filter(f => f.status === "audited")
  state.stats = {
    total_auditable: auditable.length,
    total_audited: audited.length,
    total_never_audited: auditable.filter(f => f.status === "never_audited").length,
    coverage_pct: auditable.length > 0 ? Math.round(audited.length / auditable.length * 1000) / 10 : 0,
    freshness_pct: 0, // Computed from staleness window
    avg_findings_per_file: audited.length > 0
      ? Math.round(audited.reduce((s, f) => s + (f.findings?.total || 0), 0) / audited.length * 10) / 10 : 0,
    avg_ashes_per_file: 0
  }
  state.total_sessions = (state.total_sessions || 0) + 1
  state.updated_at = new Date().toISOString()

  // Atomic write state
  Write(".claude/audit-state/state.json", state)

  // Write session history
  const coverageBefore = checkpoint.coverage_before || 0
  Write(`.claude/audit-state/history/audit-${audit_id}.json`, {
    audit_id, timestamp: new Date().toISOString(),
    mode: "incremental", depth,
    batch_size: checkpoint.batch.length,
    files_planned: checkpoint.batch,
    files_completed: checkpoint.batch, // All completed at this point
    files_failed: [],
    total_findings: Object.values(findingsPerFile).reduce((s, f) => s + f.total, 0),
    findings_by_severity: {
      P1: Object.values(findingsPerFile).reduce((s, f) => s + f.P1, 0),
      P2: Object.values(findingsPerFile).reduce((s, f) => s + f.P2, 0),
      P3: Object.values(findingsPerFile).reduce((s, f) => s + f.P3, 0)
    },
    coverage_before: coverageBefore,
    coverage_after: state.stats.coverage_pct,
    config_dir: configDir, owner_pid: ownerPid, session_id: sessionId
  })

  // Complete checkpoint
  Write(".claude/audit-state/checkpoint.json", {
    ...checkpoint, status: "completed",
    completed: checkpoint.batch, current_file: null
  })

  // Release advisory lock
  Bash(`rm -rf .claude/audit-state/.lock`)

  // Generate coverage report
  // See references/coverage-report.md
  log(`Incremental audit complete: ${checkpoint.batch.length} files audited`)
  log(`Coverage: ${state.stats.coverage_pct}% (${state.stats.total_audited}/${state.stats.total_auditable})`)

  // Persist echo
  // Write coverage summary to .claude/echoes/auditor/MEMORY.md
}

// 2. Auto-mend or interactive prompt (same as appraise)
if (totalFindings > 0) {
  AskUserQuestion({
    options: ["/rune:mend (Recommended)", "Review TOME manually", "/rune:rest"]
  })
}
```

## Error Handling

| Error | Recovery |
|-------|----------|
| Ash timeout (>5 min) | Proceed with partial results |
| Total timeout (>15 min) | Final sweep, collect partial results, report incomplete |
| Ash crash | Report gap in TOME.md |
| ALL Ash fail | Abort, notify user |
| Concurrent audit running | Warn, offer to cancel previous |
| File count exceeds 150 | Warn about partial coverage, proceed with capped budgets |
| Not a git repo | Works fine — audit uses `find`, not `git diff`. Incremental degrades to mtime-based scoring. |
| Codex CLI not installed | Skip Codex Oracle |
| Codex not authenticated | Skip Codex Oracle |
| Codex disabled in talisman.yml | Skip Codex Oracle |
| State file corrupted | Rebuild from `history/` snapshots (see incremental-state-schema.md) |
| State file locked (dead PID) | Detect dead PID via `kill -0`, remove stale lock, proceed |
| Concurrent incremental sessions | Second session warns, falls back to full audit |
| Manifest too large (>10k files) | Still functional; consider sharding for performance |
| Checkpoint from dead session | Clean up, start fresh batch |
| Disk full during state write | Pre-flight check: skip incremental if <10MB available |
| Error file infinite re-queue | 1st error re-queue, 2nd skip-one-batch, 3rd+ mark `error_permanent` |

## Migration Guide (Concern 6)

**Upgrading from non-incremental to incremental audit:**

1. No migration needed — `--incremental` is opt-in and does not affect default behavior
2. First `--incremental` run creates `.claude/audit-state/` and runs a fresh scan
3. All files start as `never_audited` and are prioritized by the scoring algorithm
4. State accumulates across sessions — coverage improves with each run
5. Use `--reset` to clear state and start fresh at any time

**Recovery from state corruption:**

1. `--reset` clears all state files but preserves history
2. If `state.json` is corrupted, it auto-rebuilds from `history/` snapshots
3. If `manifest.json` is corrupted, next run regenerates it from the filesystem
4. Manual recovery: delete `.claude/audit-state/` entirely and start fresh

## References

- [Deep Mode](references/deep-mode.md) — Lore Layer, deep pass, TOME merge
- [Orchestration Phases](../roundtable-circle/references/orchestration-phases.md) — Shared parameterized orchestration
- [Circle Registry](../roundtable-circle/references/circle-registry.md) — Ash-to-scope mapping, focus mode
- [Smart Selection](../roundtable-circle/references/smart-selection.md) — File assignment, budget enforcement
- [Wave Scheduling](../roundtable-circle/references/wave-scheduling.md) — Multi-wave deep scheduling
- [Incremental State Schema](references/incremental-state-schema.md) — State files, locking, atomic writes, schema migration
- [Codebase Mapper](references/codebase-mapper.md) — File inventory, git metadata, manifest diff
- [Priority Scoring](references/priority-scoring.md) — 6-factor composite algorithm, batch selection
- [Workflow Discovery](references/workflow-discovery.md) — Tier 2 cross-file flow detection
- [Workflow Audit](references/workflow-audit.md) — Tier 2 cross-file review protocol
- [API Discovery](references/api-discovery.md) — Tier 3 endpoint contract detection
- [API Audit](references/api-audit.md) — Tier 3 endpoint contract review, OWASP checks
- [Coverage Report](references/coverage-report.md) — Human-readable dashboard, freshness tiers
