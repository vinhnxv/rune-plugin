# Orchestration Phases — Parameterized Roundtable Circle

> Shared phase orchestration for both `/rune:appraise` and `/rune:audit`. Each command sets parameters in its preamble, then delegates to these shared phases. Skills cannot call each other — this shared reference file pattern is the integration point.

## Parameter Contract

Both appraise and audit set these parameters before invoking shared phases:

### Required Parameters (18 total)

| # | Parameter | Type | Source: appraise | Source: audit |
|---|-----------|------|-----------------|---------------|
| 1 | `scope` | `"diff" \| "full"` | `"diff"` | `"full"` |
| 2 | `depth` | `"standard" \| "deep"` | `"standard"` (or `"deep"` with `--deep`) | `"deep"` (default) or `"standard"` with `--standard` |
| 3 | `teamPrefix` | string | `"rune-review"` | `"rune-audit"` |
| 4 | `outputDir` | string | `"tmp/reviews/{id}/"` | `"tmp/audit/{id}/"` |
| 5 | `stateFilePrefix` | string | `"tmp/.rune-review"` | `"tmp/.rune-audit"` |
| 6 | `identifier` | string | `"{gitHash}-{shortSession}"` | `"{YYYYMMDD-HHMMSS}"` |
| 7 | `selectedAsh` | string[] | From Rune Gaze (file extensions) | From Rune Gaze (file extensions) |
| 8 | `fileList` | string[] | `changed_files` from git diff | `all_files` from find |
| 9 | `timeoutMs` | number | 600,000 (10 min) | 900,000 (15 min) |
| 10 | `label` | string | `"Review"` | `"Audit"` |
| 11 | `configDir` | string | Resolved `CLAUDE_CONFIG_DIR` | Resolved `CLAUDE_CONFIG_DIR` |
| 12 | `ownerPid` | string | `$PPID` (Claude Code PID) | `$PPID` (Claude Code PID) |
| 13 | `sessionId` | string | `${CLAUDE_SESSION_ID}` | `${CLAUDE_SESSION_ID}` |
| 14 | `maxAgents` | number | From `--max-agents` or all | From `--max-agents` or all |
| 15 | `workflow` | string | `"rune-review"` | `"rune-audit"` |
| 16 | `focusArea` | string | `"full"` (appraise has no focus flag) | From `--focus` or `"full"` |
| 17 | `flags` | object | Parsed CLI flags | Parsed CLI flags |
| 18 | `talisman` | object | Parsed talisman.yml config | Parsed talisman.yml config |
| 19 | `sessionNonce` | string | `crypto.randomUUID().slice(0,8)` | `crypto.randomUUID().slice(0,8)` |

> **Note on `sessionNonce`**: Generated once at orchestrator startup. Written as `session_nonce` (snake_case) in inscription.json and ash prompts. Referenced as `sessionNonce` (camelCase) in orchestrator pseudocode. Both forms refer to the same value.

### Session Isolation (Parameters 11-13)

Parameters 11-13 (`configDir`, `ownerPid`, `sessionId`) are CRITICAL for session isolation. They MUST be included in:
- State files (`tmp/.rune-{type}-{id}.json`)
- Signal directories
- Arc checkpoints
- Any file that identifies workflow ownership

```javascript
// Canonical resolution — run once at orchestrator startup
const configDir = Bash(`cd "\${CLAUDE_CONFIG_DIR:-$HOME/.claude}" 2>/dev/null && pwd -P`).trim()
const ownerPid = Bash(`echo $PPID`).trim()
const sessionId = "${CLAUDE_SESSION_ID}"
```

## Phase 1: Setup

Write state file and create output directory.

```javascript
// 1. Check for concurrent workflow
// If {stateFilePrefix}-{identifier}.json exists, < 30 min old, AND same config_dir → abort
// If different config_dir or dead ownerPid → clean up stale state

// Validate depth parameter (defense-in-depth)
if (!["standard", "deep"].includes(depth)) {
  warn(`Unknown depth "${depth}", defaulting to "standard"`)
  depth = "standard"
}

// 2. Create output directory
Bash(`mkdir -p "${outputDir}"`)

// 3. Write state file with session isolation fields
Write(`${stateFilePrefix}-${identifier}.json`, {
  team_name: `${teamPrefix}-${identifier}`,
  started: timestamp,
  status: "active",
  scope,
  depth,
  config_dir: configDir,
  owner_pid: ownerPid,
  session_id: sessionId,
  expected_files: selectedAsh.map(r => `${outputDir}${r}.md`)
})
```

### Extension Point: Incremental Audit (Phase 0.1-0.4)

When `flags['--incremental']` is set in the audit workflow, the following phases run between Phase 0 (find) and Phase 0.5 (Lore Layer):

```
Phase 0:   all_files = find(.)                          # Existing
Phase 0.1: acquireLock + initStateDir                   # NEW
Phase 0.2: manifest = buildManifest(all_files)          # NEW
Phase 0.3: diffManifest + reconcileState                # NEW
Phase 0.3.5: scored = priorityScore(manifest, state)    # NEW
Phase 0.4: batch = selectBatch(scored)                  # NEW
Phase 0.5: Lore Layer (operates on batch, not all)      # Existing (scoped)

Input:  all_files: string[]     (from Phase 0 find)
Output: batch: string[]         (filtered + prioritized subset)
Side effect: state.json updated with manifest diff
```

**Non-incremental early return**: When `--incremental` is NOT set, these phases are skipped with zero overhead. The conditional is checked at the parameter level: `if (!flags['--incremental']) return { batch: allFiles }`.

See `audit/SKILL.md` Phase 0.1-0.4 and `audit/references/incremental-state-schema.md` for full details.

## Phase 2: Forge Team

Create team, inscription, signal directory, and tasks.

```javascript
// 1. Generate inscription.json
Write(`${outputDir}inscription.json`, {
  workflow,
  timestamp,
  scope,
  depth,
  output_dir: outputDir,
  team_name: teamName,
  session_nonce: sessionNonce,
  teammates: selectedAsh.map(r => ({
    name: r,
    output_file: `${r}.md`,
    required_sections: ["P1 (Critical)", "P2 (High)", "P3 (Medium)", "Summary"]
  })),
  verification: { enabled: true }
})

// 2. Pre-create guard: teamTransition protocol (see team-lifecycle-guard.md)
const teamName = `${teamPrefix}-${identifier}`
// Validate → TeamDelete with retry-with-backoff → Filesystem fallback → TeamCreate
// with "Already leading" catch-and-recover → Post-create verification

// 3. Signal directory for event-driven sync
const signalDir = `tmp/.rune-signals/${teamName}`
Bash(`mkdir -p "${signalDir}" && find "${signalDir}" -mindepth 1 -delete`)
Write(`${signalDir}/.expected`, String(selectedAsh.length))
Write(`${signalDir}/inscription.json`, JSON.stringify({
  workflow,
  timestamp,
  output_dir: outputDir,
  team_name: teamName,
  teammates: selectedAsh.map(name => ({ name, output_file: `${name}.md` }))
}))

// 4. SEC-001: Write readonly marker for review/audit teams
Write(`${signalDir}/.readonly-active`, "active")

// 5. Create tasks (one per Ash)
for (const ash of selectedAsh) {
  TaskCreate({
    subject: `${label} as ${ash}`,
    description: `Files: [...], Output: ${outputDir}${ash}.md`,
    activeForm: `${ash} ${label.toLowerCase()}ing...`
  })
}
```

## Phase 3: Summon

Summon Ashes — single wave for standard depth, multi-wave loop for deep depth.

### Standard Depth (Single Pass)

```javascript
// Summon ALL selected Ash in a single message (parallel execution)
for (const ash of selectedAsh) {
  Task({
    team_name: teamName,
    name: ash,  // slug name, no wave suffix
    subagent_type: "general-purpose",
    prompt: loadAshPrompt(ash, { scope, outputDir, fileList }),
    run_in_background: true
  })
}
```

### Deep Depth (Wave Loop)

```javascript
// Import wave scheduling (from wave-scheduling.md)
const waves = selectWaves(circleEntries, depth, new Set(selectedAsh))

for (const wave of waves) {
  // Skip team re-creation for Wave 1 (already created in Phase 2)
  if (wave.waveNumber > 1) {
    // Inter-wave team reset
    TeamCreate({ team_name: `${teamName}-w${wave.waveNumber}` })

    // Create per-wave signal directory (matches hook TEAM_NAME for Wave 2+ agents)
    const waveSignalDir = `tmp/.rune-signals/${teamName}-w${wave.waveNumber}`
    Bash(`mkdir -p "${waveSignalDir}" && find "${waveSignalDir}" -mindepth 1 -delete`)
    Write(`${waveSignalDir}/.expected`, String(wave.agents.length))
    Write(`${waveSignalDir}/.readonly-active`, "active")
    Write(`${waveSignalDir}/inscription.json`, JSON.stringify({
      workflow, timestamp, output_dir: outputDir,
      team_name: `${teamName}-w${wave.waveNumber}`,
      teammates: wave.agents.map(ash => ({ name: ash.slug, output_file: `${ash.slug}.md` }))
    }))

    // Create tasks for this wave's agents
    for (const ash of wave.agents) {
      TaskCreate({
        subject: `${label} as ${ash.name} (Wave ${wave.waveNumber})`,
        description: `Files: [...], Output: ${outputDir}${ash.name}.md`,
        activeForm: `${ash.name} (wave ${wave.waveNumber})...`
      })
    }
  }

  // Summon this wave's Ashes
  for (const ash of wave.agents) {
    const priorFindings = wave.waveNumber > 1
      ? collectWaveFindings(outputDir, wave.waveNumber - 1)  // file:line + severity only
      : null
    Task({
      team_name: wave.waveNumber === 1 ? teamName : `${teamName}-w${wave.waveNumber}`,
      name: ash.slug,  // NO -w1 suffix — preserves hook compatibility
      subagent_type: "general-purpose",
      prompt: loadAshPrompt(ash.name, { scope, outputDir, fileList, priorFindings }),
      run_in_background: true
    })
  }

  // Phase 4: Monitor this wave
  const waveResult = waitForCompletion(
    wave.waveNumber === 1 ? teamName : `${teamName}-w${wave.waveNumber}`,
    wave.agents.length,
    {
      timeoutMs: wave.timeoutMs,
      staleWarnMs: 300_000,
      pollIntervalMs: 30_000,
      label: `${label} Wave ${wave.waveNumber}`
    }
  )

  // Inter-wave cleanup (skip after last wave — Phase 7 handles final cleanup)
  if (wave.waveNumber < waves.length) {
    // Shutdown all teammates in this wave
    for (const ash of wave.agents) {
      SendMessage({ type: "shutdown_request", recipient: ash.slug })
    }
    // Force-delete remaining tasks to prevent zombie contamination
    const remaining = TaskList().filter(t => t.status !== "completed")
    for (const task of remaining) {
      TaskUpdate({ taskId: task.id, status: "deleted" })
    }
    // Inter-wave TeamDelete with retry-with-backoff (3 attempts: 0s, 3s, 8s)
    const WAVE_CLEANUP_DELAYS = [0, 3000, 8000]
    let waveCleanupOk = false
    for (let attempt = 0; attempt < WAVE_CLEANUP_DELAYS.length; attempt++) {
      if (attempt > 0) Bash(`sleep ${WAVE_CLEANUP_DELAYS[attempt] / 1000}`)
      try { TeamDelete(); waveCleanupOk = true; break } catch (e) {
        if (attempt === WAVE_CLEANUP_DELAYS.length - 1) warn(`inter-wave cleanup: TeamDelete failed after ${WAVE_CLEANUP_DELAYS.length} attempts`)
      }
    }
    if (!waveCleanupOk) {
      const cleanupTeamName = wave.waveNumber === 1 ? teamName : `${teamName}-w${wave.waveNumber}`
      Bash(`CHOME="\${CLAUDE_CONFIG_DIR:-$HOME/.claude}" && rm -rf "$CHOME/teams/${cleanupTeamName}/" "$CHOME/tasks/${cleanupTeamName}/" 2>/dev/null`)
    }

    // Collect findings for next wave context (file:line + severity ONLY)
    if (waveResult.timedOut) {
      warn(`Wave ${wave.waveNumber} timed out — passing partial flag to Wave ${wave.waveNumber + 1}`)
    }
  }
}
```

**CRITICAL constraints:**
- Concurrent wave execution is NOT supported — waves run sequentially
- Teammate naming uses `ash.slug` (no `-w1` suffix) to preserve hook compatibility
- Max 8 concurrent teammates per wave (SDK limit)
- Cross-wave context limited to finding locations (file:line + severity), not interpretations

## Phase 4: Monitor

Uses `waitForCompletion` from [monitor-utility.md](monitor-utility.md). Per-command configuration:

| Caller | `timeoutMs` | `label` |
|--------|-------------|---------|
| appraise (standard) | 600,000 (10 min) | `"Review"` |
| appraise (deep, per wave) | Allocated by `distributeTimeouts` | `"Review Wave N"` |
| audit (per wave) | Allocated by `distributeTimeouts` from 900,000 | `"Audit Wave N"` |

## Phase 4.5: Doubt Seer

Conditional phase — runs after each wave's monitor completes. See roundtable-circle SKILL.md for the full Doubt Seer protocol.

## Phase 5: Aggregate

Summon Runebinder to aggregate findings from all waves.

```javascript
// For standard depth: single Runebinder pass (TOME.md)
// For deep depth: per-wave TOME files (TOME-w1.md, TOME-w2.md) then merge into final TOME.md
Task({
  team_name: teamName,  // May need to re-create team for final aggregation
  name: "runebinder",
  subagent_type: "general-purpose",
  prompt: `Read all findings from ${outputDir}.
    Deduplicate using hierarchy from dedup-runes.md.
    ${depth === "deep"
      ? "Merge cross-wave findings. Later wave findings supersede earlier (deeper analysis wins)."
      : "Write unified summary."}
    Write ${outputDir}TOME.md.
    Every finding MUST be wrapped in <!-- RUNE:FINDING nonce="{session_nonce}" ... --> markers.`
})
```

**TOME output format is identical for both scopes** — header differs only in `Scope:` field and `Files scanned:` vs `Files changed:`.

## Phase 5.4: Todo Generation from TOME (Conditional)

Generate per-finding todo files from scope-tagged TOME. Runs AFTER Phase 5.3 (diff-scope tagging) so scope attributes are available.

**Skip conditions**: `talisman.file_todos.enabled !== true` OR `talisman.file_todos.auto_generate.{workflow_type} !== true` OR `--todos=false` flag.

**Activation**: `talisman.file_todos.auto_generate.review === true` (for appraise) or `talisman.file_todos.auto_generate.audit === true` (for audit), or `--todos` flag override.

```javascript
// Phase 5.4: Todo Generation from TOME findings
const fileTodosEnabled = talisman?.file_todos?.enabled === true  // opt-in (NOT !== false)
const workflowType = workflow === "rune-review" ? "review" : "audit"
const autoGenerate = talisman?.file_todos?.auto_generate?.[workflowType] === true
const todosFlag = flags['--todos']

// Skip if not enabled: master toggle + per-workflow toggle + flag override
const generateTodos = fileTodosEnabled && (todosFlag === true || (autoGenerate && todosFlag !== false))

if (generateTodos) {
  // 1. Read scope-tagged TOME.md
  const tomeContent = Read(`${outputDir}TOME.md`)
  const tomePath = `${outputDir}TOME.md`

  // 2. Extract findings via RUNE:FINDING markers (6-step pipeline)
  //    nonce validation → marker parsing → attribute extraction →
  //    path normalization → Q/N filtering → scope classification
  const allFindings = extractFindings(tomeContent, sessionNonce)

  // 3. Filter out non-actionable findings
  const todoableFindings = allFindings.filter(f =>
    f.interaction !== 'question' &&         // Q findings are non-actionable
    f.interaction !== 'nit' &&              // N findings are non-actionable
    f.status !== 'FALSE_POSITIVE' &&        // Already dismissed
    !(f.scope === 'pre-existing' && f.severity !== 'P1')  // Skip pre-existing P2/P3
    // Pre-existing P1 findings ARE kept (critical regardless of scope)
  )

  // 4. Resolve source-qualified directory (per-source subdirectory convention)
  // Uses resolveTodosDir() from integration-guide.md — inline implementation
  // Priority: --todos-dir flag > talisman.file_todos.dir > "todos/"
  const todosDir = resolveTodosDir($ARGUMENTS, talisman, workflowType)
  //   standalone appraise: "todos/review/"
  //   standalone audit:    "todos/audit/"
  //   arc appraise:        "tmp/arc/{id}/todos/review/"  (via --todos-dir)
  Bash(`mkdir -p "${todosDir}"`)

  // 5. Get next sequential ID — scoped to source subdirectory (independent per source)
  const existingFiles = Glob(`${todosDir}[0-9][0-9][0-9]-*.md`)
  let nextId = 1
  if (existingFiles.length > 0) {
    const maxId = existingFiles
      .map(f => parseInt(f.split('/').pop().match(/^(\d+)-/)?.[1] || '0', 10))
      .reduce((a, b) => Math.max(a, b), 0)
    nextId = maxId + 1
  }

  // 6. Idempotency check + write todo files
  let createdCount = 0
  for (const finding of todoableFindings) {
    // Dedup: check if todo already exists for this finding (scoped to source subdirectory)
    const existingTodos = Glob(`${todosDir}[0-9][0-9][0-9]-*.md`)
    const isDuplicate = existingTodos.some(f => {
      const fm = parseFrontmatter(Read(f))
      return fm.finding_id === finding.id && fm.source_ref === tomePath
    })
    if (isDuplicate) continue

    const priority = finding.severity.toLowerCase()  // P1→p1, P2→p2, P3→p3
    const slug = finding.title.toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '')
      .slice(0, 40)
    const paddedId = String(nextId).padStart(3, '0')
    const filename = `${paddedId}-pending-${priority}-${slug}.md`

    // Write from template (sole-orchestrator pattern — only orchestrator creates)
    Write(`${todosDir}${filename}`, generateTodoFromFinding(finding, {
      schema_version: 1,
      status: "pending",
      priority,
      issue_id: paddedId,
      source: workflowType,
      source_ref: tomePath,
      finding_id: finding.id,
      finding_severity: finding.severity,
      tags: finding.tags || [],
      files: finding.files || [],
      created: new Date().toISOString().slice(0, 10),
      updated: new Date().toISOString().slice(0, 10)
    }))

    nextId++
    createdCount++
  }

  log(`Phase 5.4: Generated ${createdCount} todo files from ${todoableFindings.length} actionable findings (${allFindings.length - todoableFindings.length} filtered out)`)
}
```

**generateTodoFromFinding()** writes a markdown file using the template from `skills/file-todos/references/todo-template.md`, filling in the `source: review` (or `audit`) conditional sections with finding data from TOME.

**Filtering summary**:

| Filter | Rationale |
|--------|-----------|
| `interaction="question"` | Non-actionable (questions for the author) |
| `interaction="nit"` | Non-actionable (style nits) |
| `FALSE_POSITIVE` | Already dismissed in prior mend |
| Pre-existing P2/P3 | Noise reduction (pre-existing debt) |
| Pre-existing P1 | KEPT (critical regardless of scope) |

## Phase 6: Verify (Truthsight)

Layer 0 inline checks + Layer 2 verifier. See roundtable-circle SKILL.md for the protocol.

### Phase 6.2: Codex Diff Verification (Layer 3)

Cross-model verification of P1/P2 findings against actual diff hunks. Runs after Layer 2 (Smart Verifier).

- **Gate**: 4-condition canonical pattern — `codexAvailable && !codexDisabled && diffVerifyEnabled && workflowIncluded("review" OR "audit")`
- **Input**: Up to 3 P1/P2 findings from `truthsight-report.md` (fallback: TOME.md if Layer 2 skipped)
- **Output**: `{outputDir}codex-diff-verification.md` (CDX-VERIFY prefix)
- **Verdicts**: CONFIRMED (+0.15 confidence), WEAKENED (no change), REFUTED (demote to P3)
- **Config**: `codex.diff_verification.enabled` (default: true), timeout 300s, reasoning "high"

See roundtable-circle SKILL.md Phase 6.2 for full pseudocode.

### Phase 6.3: Codex Architecture Review (Audit Mode Only)

Cross-model analysis of TOME findings for cross-cutting architectural patterns. Only runs when `scope=full` (audit mode).

- **Gate**: 5-condition — canonical 4-condition + `scope === "full"` (audit only, NOT appraise)
- **Input**: TOME.md aggregate (truncated to 20K chars)
- **Output**: `{outputDir}architecture-review.md` (CDX-ARCH prefix)
- **Focus**: Naming drift, layering violations, error handling inconsistency
- **Config**: `codex.architecture_review.enabled` (default: false — opt-in), timeout 600s, reasoning "xhigh"

See roundtable-circle SKILL.md Phase 6.3 for full pseudocode.

## Phase 7: Cleanup

```javascript
const CHOME = Bash(`echo "\${CLAUDE_CONFIG_DIR:-$HOME/.claude}"`).trim()

// 1. Dynamic member discovery
let allMembers = []
try {
  const teamConfig = Read(`${CHOME}/teams/${teamName}/config.json`)
  allMembers = teamConfig.members.map(m => m.name).filter(Boolean)
} catch (e) {
  allMembers = [...selectedAsh, "runebinder"]
}

// 2. Shutdown all teammates
for (const member of allMembers) {
  SendMessage({ type: "shutdown_request", recipient: member, content: `${label} complete` })
}

// 3. Grace period — let teammates deregister before TeamDelete
if (allMembers.length > 0) {
  Bash(`sleep 15`)
}

// 4. TeamDelete with retry-with-backoff (0s, 5s, 10s — 15s retry budget after 15s grace)
const CLEANUP_DELAYS = [0, 5000, 10000]
let cleanupSucceeded = false
for (let attempt = 0; attempt < CLEANUP_DELAYS.length; attempt++) {
  if (attempt > 0) Bash(`sleep ${CLEANUP_DELAYS[attempt] / 1000}`)
  try { TeamDelete(); cleanupSucceeded = true; break } catch (e) {}
}
if (!cleanupSucceeded) {
  Bash(`CHOME="\${CLAUDE_CONFIG_DIR:-$HOME/.claude}" && rm -rf "$CHOME/teams/${teamName}/" "$CHOME/tasks/${teamName}/" 2>/dev/null`)
  // Deep mode: also clean wave-suffixed teams (v1.67.0+)
  Bash(`CHOME="\${CLAUDE_CONFIG_DIR:-$HOME/.claude}" && for n in 2 3 4; do rm -rf "$CHOME/teams/${teamName}-w${n}/" "$CHOME/tasks/${teamName}-w${n}/" 2>/dev/null; done`)
}

// 4. Update state file
Write(`${stateFilePrefix}-${identifier}.json`, {
  team_name: `${teamPrefix}-${identifier}`,
  started: timestamp,
  status: "completed",
  completed: new Date().toISOString(),
  config_dir: configDir,
  owner_pid: ownerPid,
  session_id: sessionId
})

// 5. Persist learnings to Rune Echoes
// 6. Read and present TOME.md to user
```

## Caller Integration

### appraise/SKILL.md (Preamble)

```javascript
// Set parameters
const params = {
  scope: "diff",
  depth: flags['--deep'] ? "deep" : "standard",
  teamPrefix: "rune-review",
  outputDir: `tmp/reviews/${identifier}/`,
  stateFilePrefix: "tmp/.rune-review",
  identifier,
  selectedAsh,
  fileList: changed_files,
  timeoutMs: 600_000,
  label: "Review",
  configDir, ownerPid, sessionId,
  maxAgents: flags['--max-agents'],
  workflow: "rune-review",
  focusArea: "full",
  flags, talisman
}
// Then execute Phases 1-7 from orchestration-phases.md
```

### audit/SKILL.md (Preamble)

```javascript
// Set parameters
const params = {
  scope: "full",
  depth: flags['--standard'] ? "standard" : (flags['--deep'] !== false && (talisman?.audit?.always_deep !== false)) ? "deep" : "standard",
  teamPrefix: "rune-audit",
  outputDir: `tmp/audit/${audit_id}/`,
  stateFilePrefix: "tmp/.rune-audit",
  identifier: audit_id,
  selectedAsh,
  fileList: all_files,
  timeoutMs: 900_000,
  label: "Audit",
  configDir, ownerPid, sessionId,
  maxAgents: flags['--max-agents'],
  workflow: "rune-audit",
  focusArea: flags['--focus'] || "full",
  flags, talisman
}
// Then execute Phases 1-7 from orchestration-phases.md
```

## References

- [Wave Scheduling](wave-scheduling.md) — selectWaves, mergeSmallWaves, distributeTimeouts
- [Monitor Utility](monitor-utility.md) — waitForCompletion, per-command configuration
- [Circle Registry](circle-registry.md) — Ash wave assignments, deepOnly flags
- [Smart Selection](smart-selection.md) — File-to-Ash assignment, wave integration
- [Dedup Runes](dedup-runes.md) — Cross-wave dedup hierarchy
- [Team Lifecycle Guard](../../rune-orchestration/references/team-lifecycle-guard.md) — Pre-create guard pattern
- [Inscription Schema](inscription-schema.md) — inscription.json format
- [File-Todos Integration](../../file-todos/references/integration-guide.md) — Phase 5.4 todo generation from TOME
