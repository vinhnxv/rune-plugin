---
name: rune:arc
description: |
  End-to-end orchestration pipeline. Chains forge, plan review, plan refinement,
  verification, work, gap analysis, code review, mend, verify mend (convergence gate), and audit
  into a single automated pipeline with checkpoint-based resume, per-phase teams, circuit breakers,
  convergence gate with regression detection, and artifact-based handoff.

  <example>
  user: "/rune:arc plans/feat-user-auth-plan.md"
  assistant: "The Tarnished begins the arc — 10 phases of forge, review, mend, and convergence..."
  </example>

  <example>
  user: "/rune:arc --resume"
  assistant: "Resuming arc from Phase 5 (WORK) — validating checkpoint integrity..."
  </example>
user-invocable: true
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
  - Task
  - TaskCreate
  - TaskUpdate
  - TaskGet
  - TaskList
  - TeamCreate
  - TeamDelete
  - SendMessage
  - AskUserQuestion
  - EnterPlanMode
  - ExitPlanMode
---

# /rune:arc — End-to-End Orchestration Pipeline

Chains ten phases into a single automated pipeline: forge, plan review, plan refinement, verification, work, gap analysis, code review, mend, verify mend (convergence gate), and audit. Each phase summons its own team with fresh context (except orchestrator-only phases 2.5, 2.7, 5.5, and 7.5). Artifact-based handoff connects phases. Checkpoint state enables resume after failure.

**Load skills**: `roundtable-circle`, `context-weaving`, `rune-echoes`, `rune-orchestration`, `elicitation`, `codex-cli`

## Usage

```
/rune:arc <plan_file.md>              # Full pipeline
/rune:arc <plan_file.md> --no-forge   # Skip research enrichment
/rune:arc <plan_file.md> --approve    # Require human approval for work tasks
/rune:arc --resume                    # Resume from last checkpoint
/rune:arc --resume --no-forge         # Resume, skipping forge on retry
/rune:arc <plan_file.md> --skip-freshness   # Skip freshness validation
```

## Flags

| Flag | Description | Default |
|------|-------------|---------|
| `--no-forge` | Skip Phase 1 (research enrichment), use plan as-is | Off |
| `--approve` | Require human approval for each work task (Phase 5 only) | Off |
| `--resume` | Resume from last checkpoint. Plan path auto-detected from checkpoint | Off |
| `--skip-freshness` | Skip plan freshness check (bypass stale-plan detection) | Off |

## Pipeline Overview

```
Phase 1:   FORGE → Research-enrich plan sections
    ↓ (enriched-plan.md)
Phase 2:   PLAN REVIEW → 3 parallel reviewers + circuit breaker
    ↓ (plan-review.md) — HALT on BLOCK
Phase 2.5: PLAN REFINEMENT → Extract CONCERNs, write concern context (conditional)
    ↓ (concern-context.md) — HALT on all-CONCERN escalation (user choice)
Phase 2.7: VERIFICATION GATE → Deterministic plan checks (zero LLM)
    ↓ (verification-report.md)
Phase 5:   WORK → Swarm implementation + incremental commits
    ↓ (work-summary.md + committed code)
Phase 5.5: GAP ANALYSIS → Check plan criteria vs committed code (zero LLM)
    ↓ (gap-analysis.md) — WARN only, never halts
Phase 6:   CODE REVIEW → Roundtable Circle review
    ↓ (tome.md)
Phase 7:   MEND → Parallel finding resolution
    ↓ (resolution-report.md) — HALT on >3 FAILED
Phase 7.5: VERIFY MEND → Convergence gate (spot-check + retry loop)
    ↓ converged → proceed | retry → loop to Phase 7 (max 2 retries) | halted → warn + proceed
Phase 8:   AUDIT → Final quality gate (informational)
    ↓ (audit-report.md)
Output: Implemented, reviewed, and fixed feature
```

**Phase numbering note**: Phase numbers (1, 2, 2.5, 2.7, 5, 5.5, 6, 7, 7.5, 8) match the legacy pipeline phases from plan.md and review.md for cross-command consistency. Phases 3 and 4 are reserved. The `PHASE_ORDER` array uses names (not numbers) for validation logic.

## Arc Orchestrator Design (ARC-1)

The arc orchestrator is a **lightweight dispatcher**, not a monolithic agent. Each phase summons a **new team with fresh context** (except Phases 2.5, 2.7, 5.5, and 7.5 which are orchestrator-only). Phase artifacts serve as the handoff mechanism.

Dispatcher loop:
```
1. Read/create checkpoint state
2. Determine current phase (first incomplete in PHASE_ORDER)
3. Invoke phase (delegates to existing commands with their own teams)
4. Read phase output artifact (SUMMARY HEADER ONLY — Glyph Budget)
5. Update checkpoint state + artifact hash
6. Check total pipeline timeout
7. Proceed to next phase or halt on failure
```

The dispatcher reads only structured summary headers from artifacts, not full content. Full artifacts are passed by file path to the next phase.

### Phase Constants

```javascript
const PHASE_ORDER = ['forge', 'plan_review', 'plan_refine', 'verification', 'work', 'gap_analysis', 'code_review', 'mend', 'verify_mend', 'audit']

// SETUP_BUDGET: time for team creation, task creation, agent spawning, report, cleanup.
// MEND_EXTRA_BUDGET: additional time for ward check, cross-file mend, doc-consistency.
// Phase outer timeout = inner polling timeout + setup budget (+ mend extra for mend).
// IMPORTANT: checkArcTimeout() runs BETWEEN phases, not during. A phase that exceeds
// its budget will only be detected after it finishes/times out internally.
const SETUP_BUDGET = 300_000          //  5 min — team creation, parsing, report, cleanup
const MEND_EXTRA_BUDGET = 180_000     //  3 min — ward check, cross-file, doc-consistency

const PHASE_TIMEOUTS = {
  forge:         900_000,    // 15 min (inner 10m + 5m setup)
  plan_review:   900_000,    // 15 min (inner 10m + 5m setup)
  plan_refine:   180_000,    //  3 min (orchestrator-only, no team)
  verification:   30_000,    // 30 sec (orchestrator-only, no team)
  work:        2_100_000,    // 35 min (inner 30m + 5m setup)
  gap_analysis:    60_000,    //  1 min (orchestrator-only, no team)
  code_review:   900_000,    // 15 min (inner 10m + 5m setup)
  mend:        1_380_000,    // 23 min (inner 15m + 5m setup + 3m ward/cross-file)
  verify_mend:   240_000,    //  4 min (orchestrator-only, no team)
  audit:       1_200_000,    // 20 min (inner 15m + 5m setup)
}
const ARC_TOTAL_TIMEOUT = 7_200_000  // 120 min (honest budget — old 90 min was routinely exceeded)
const STALE_THRESHOLD = 300_000      // 5 min
const CONVERGENCE_MAX_ROUNDS = 2     // Max mend retries (3 total passes)
const MEND_RETRY_TIMEOUT = 780_000   // 13 min (inner 5m polling + 5m setup + 3m ward)
```

See [phase-tool-matrix.md](../skills/rune-orchestration/references/phase-tool-matrix.md) for per-phase tool restrictions and time budget details.

## Pre-flight

### Branch Strategy (COMMIT-1)

Before Phase 5 (WORK), create a feature branch if on main:

```bash
current_branch=$(git branch --show-current)
if [ "$current_branch" = "main" ] || [ "$current_branch" = "master" ]; then
  plan_name=$(basename "$plan_file" .md | sed 's/[^a-zA-Z0-9]/-/g')
  plan_name=${plan_name:-unnamed}
  branch_name="rune/arc-${plan_name}-$(date +%Y%m%d-%H%M%S)"

  # SEC-006: Validate constructed branch name using git's own ref validation
  if ! git check-ref-format --branch "$branch_name" 2>/dev/null; then
    echo "ERROR: Invalid branch name: $branch_name"
    exit 1
  fi
  if echo "$branch_name" | grep -qE '(HEAD|FETCH_HEAD|ORIG_HEAD|MERGE_HEAD)'; then
    echo "ERROR: Branch name collides with Git special ref"
    exit 1
  fi

  git checkout -b -- "$branch_name"
fi
```

If already on a feature branch, use the current branch.

### Concurrent Arc Prevention

```bash
# SEC-007: Use find instead of ls glob to avoid ARG_MAX issues
# SEC-007 (P2): This checks for concurrent arc sessions only. Cross-command concurrency
# (e.g., arc + review + work + mend running simultaneously) is not checked here.
# LIMITATION: Multiple /rune:* commands can run concurrently on the same codebase,
# potentially causing git index contention, file edit conflicts, and team name collisions.
# TODO: Implement shared lock file check across all /rune:* commands. Proposed approach:
#   1. Each /rune:* command creates a lock file: tmp/.rune-lock-{command}-{timestamp}.json
#   2. Before team creation, scan tmp/.rune-lock-*.json for active sessions (< 30 min old)
#   3. If active session found, warn user and offer: proceed (risk conflicts) or abort
#   4. Lock file cleanup in each command's Phase 6/7 cleanup step
if command -v jq >/dev/null 2>&1; then
  active=$(find .claude/arc -name checkpoint.json -maxdepth 2 2>/dev/null | while read f; do
    jq -r 'select(.phases | to_entries | map(.value.status) | any(. == "in_progress")) | .id' "$f" 2>/dev/null
  done)
else
  active=$(find .claude/arc -name checkpoint.json -maxdepth 2 2>/dev/null | while read f; do
    if grep -q '"status"[[:space:]]*:[[:space:]]*"in_progress"' "$f" 2>/dev/null; then basename "$(dirname "$f")"; fi
  done)
fi

if [ -n "$active" ]; then
  echo "Active arc session detected: $active"
  echo "Cancel with /rune:cancel-arc or wait for completion"
  exit 1
fi
```

### Validate Plan Path

```javascript
if (!/^[a-zA-Z0-9._\/-]+$/.test(planFile)) {
  error(`Invalid plan path: ${planFile}. Only alphanumeric, dot, slash, hyphen, and underscore allowed.`)
  return
}
// CDX-005 MITIGATION (P2): Explicit .. rejection — defense-in-depth with regex above.
// The regex allows . and / which enables ../../../etc/passwd style traversal paths.
if (planFile.includes('..')) {
  error(`Path traversal detected in plan path: ${planFile}`)
  return
}
// CDX-009 MITIGATION: Reject leading-hyphen paths (option injection in cp, ls, etc.)
if (planFile.startsWith('-')) {
  error(`Plan path starts with hyphen (option injection risk): ${planFile}`)
  return
}
// Reject absolute paths — plan files must be relative to project root
if (planFile.startsWith('/')) {
  error(`Absolute paths not allowed: ${planFile}. Use a relative path from project root.`)
  return
}
```

### Plan Freshness Check (FRESH-1)

Detect when a plan was written against a significantly different codebase state. Zero-LLM-cost, orchestrator-only. Runs after "Validate Plan Path" and before "Total Pipeline Timeout Check".

**Inputs**: `planFile` (validated path), talisman config (optional `plan.freshness.*`)
**Outputs**: `freshnessResult` object stored in checkpoint
**Error handling**: Plan without `git_sha` → skip check (backward compat). Invalid SHA → skip with warning. SHA unreachable → max commit distance.

```javascript
// Security pattern: SAFE_SHA_PATTERN — see security-patterns.md
const SAFE_SHA_PATTERN = /^[0-9a-f]{7,40}$/

const planContent = Read(planFile)
const frontmatter = extractYamlFrontmatter(planContent)
// extractYamlFrontmatter: parses YAML between --- delimiters. Returns object or null on parse error.
const planSha = frontmatter?.git_sha
const planBranch = frontmatter?.branch
const planDate = frontmatter?.date
let freshnessResult = null  // FLAW-001 FIX: declare at outer scope for all code paths

// G1: Backward compatibility — plans without git_sha skip the check
if (!planSha) {
  log("Plan predates freshness gate — skipping check")
  // freshnessResult = null — proceed to Initialize Checkpoint
}

// E8: Validate SHA format before any git command
if (planSha && !SAFE_SHA_PATTERN.test(planSha)) {
  warn(`Invalid git_sha format in plan: ${planSha.slice(0, 20)}`)
  // Treat as missing — skip freshness check
}

if (planSha && SAFE_SHA_PATTERN.test(planSha)) {
  // Overall 10-second deadline for entire freshness check
  const freshnessDeadline = Date.now() + 10_000
  const checkBudget = () => Date.now() > freshnessDeadline
  // clamp: returns value bounded to [min, max]. If NaN, returns min.
  const clamp = (v, min, max) => !Number.isFinite(v) ? min : Math.min(Math.max(v, min), max)

  // Read talisman thresholds (G8: with validation and defaults)
  // readTalisman: reads .claude/talisman.yml. Returns parsed YAML or {} on error.
  const talisman = readTalisman()
  const config = {
    warn_threshold:       clamp(talisman?.plan?.freshness?.warn_threshold ?? 0.7, 0.01, 1.0),
    block_threshold:      clamp(talisman?.plan?.freshness?.block_threshold ?? 0.4, 0.0, 0.99),
    max_commit_distance:  Math.min(Math.max(talisman?.plan?.freshness?.max_commit_distance ?? 100, 1), 10000),
    enabled:              talisman?.plan?.freshness?.enabled ?? true
  }
  // G8: Ensure block < warn (swap if inverted)
  if (config.block_threshold >= config.warn_threshold) {
    warn("Talisman: block_threshold >= warn_threshold — swapping")
    ;[config.warn_threshold, config.block_threshold] = [config.block_threshold, config.warn_threshold]
    // LOGIC-5 FIX: Ensure WARN band exists after swap
    if (config.block_threshold === config.warn_threshold) {
      config.warn_threshold = Math.min(config.block_threshold + 0.1, 1.0)
    }
  }

  // --skip-freshness flag check (E9) — LOGIC-1: early exit when disabled
  if (!config.enabled || skipFreshnessFlag) {
    log("Freshness check disabled — skipping")
    freshnessResult = null
    // Skip all signal computation — proceed to Initialize Checkpoint
  } else {

  // G2: Verify SHA exists in git history
  const shaExists = Bash(`git cat-file -t "${planSha}" 2>/dev/null`)
  const shaReachable = shaExists.stdout.trim() === "commit"

  // ── Signal 1: Commit Distance (weight 0.25) ──
  let commitDistance = 0
  if (checkBudget()) { /* budget exhausted — use defaults */ }
  else if (shaReachable) {
    const timeoutMs = Math.max(100, freshnessDeadline - Date.now())
    const countResult = Bash(`git rev-list --count "${planSha}..HEAD" 2>/dev/null`, { timeout: Math.min(5000, timeoutMs) })
    commitDistance = countResult.exitCode === 0
      ? parseInt(countResult.stdout.trim(), 10) || 0
      : config.max_commit_distance  // E3: shallow clone fallback
  } else {
    commitDistance = config.max_commit_distance  // G2: unreachable SHA
    warn(`Plan source commit ${planSha.slice(0,8)} not found in git history`)
  }
  const commitSignal = clamp(commitDistance / config.max_commit_distance, 0, 1)

  // ── Signal 2: File Drift Ratio (weight 0.35) ──
  // Security pattern: SAFE_FILE_PATH — see security-patterns.md
  const SAFE_FILE_PATH = /^[a-zA-Z0-9._\-\/]+$/
  // extractFileReferences: extracts file paths from markdown (backtick paths, links). Returns string[].
  const referencedFiles = extractFileReferences(planContent)
    .filter(fp => SAFE_FILE_PATH.test(fp) && !fp.includes('..') && !fp.startsWith('/'))
  let fileDriftSignal = 0
  let driftCount = 0
  if (!checkBudget() && referencedFiles.length > 0 && shaReachable) {
    const diffResult = Bash(`git diff --name-status "${planSha}..HEAD" 2>/dev/null`)
    const changedFiles = new Set()
    const renameMap = {}
    const diffOutput = diffResult.stdout.trim()
    for (const line of (diffOutput ? diffOutput.split('\n') : [])) {
      const [tstat, ...paths] = line.split('\t')
      if (tstat?.startsWith('R') && paths.length >= 2) {
        // Pure renames (R100) still count as drift — file path changed
        renameMap[paths[0]] = paths[1]
        changedFiles.add(paths[0])
      } else if (tstat === 'M' || tstat === 'A' || tstat === 'D' || tstat === 'T' || tstat?.startsWith('C')) {
        changedFiles.add(paths[0])
      }
    }
    for (const fp of referencedFiles) {
      if (renameMap[fp] || changedFiles.has(fp)) driftCount++
    }
    fileDriftSignal = clamp(driftCount / referencedFiles.length, 0, 1)
  }

  // ── Signal 3: Identifier Loss (weight 0.25) ──
  const identifierRegex = /`([a-zA-Z_][a-zA-Z0-9_.]{2,})`/g
  const STOPWORDS = new Set(['null', 'true', 'false', 'error', 'string', 'number',
    'object', 'function', 'const', 'return', 'import', 'export', 'undefined', 'Promise'])
  const identifiers = [...new Set([...planContent.matchAll(identifierRegex)].map(m => m[1]))]
    .filter(id => !STOPWORDS.has(id) && !id.includes(' ') && id.length <= 100)
    .slice(0, 20)  // Reduced from 30 for 10s budget safety

  let identifierLossSignal = 0
  let lostCount = 0
  const rgAvailable = Bash('command -v rg 2>/dev/null').exitCode === 0
  if (!checkBudget() && identifiers.length > 0 && rgAvailable) {
    const batchSize = 10
    for (let i = 0; i < identifiers.length; i += batchSize) {
      if (checkBudget()) { identifierLossSignal = 0.5; break }
      const batch = identifiers.slice(i, i + batchSize)
      const pattern = batch.map(id => id.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')
      const timeoutMs = Math.max(100, freshnessDeadline - Date.now())
      const grepResult = Bash(`rg -l --max-count 1 "${pattern}" 2>/dev/null | head -1`, { timeout: Math.min(3000, timeoutMs) })
      if (grepResult.timedOut) { identifierLossSignal = 0.5; break }
      if (grepResult.stdout.trim().length === 0) {
        lostCount += batch.length
      } else {
        for (const id of batch) {
          if (checkBudget()) break
          const singleResult = Bash(`rg -l --max-count 1 "${id.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}" 2>/dev/null | head -1`, { timeout: 1000 })
          if (singleResult.timedOut || singleResult.stdout.trim().length === 0) lostCount++
        }
      }
    }
    if (identifierLossSignal !== 0.5) identifierLossSignal = clamp(lostCount / identifiers.length, 0, 1)
  }

  // ── Signal 4: Branch Divergence (weight 0.10) ──
  const currentBranch = Bash('git branch --show-current 2>/dev/null').stdout.trim() || null
  let branchSignal = 0
  if (planBranch && currentBranch && planBranch !== currentBranch) {
    branchSignal = 0.5
  }

  // ── Signal 5: Time Decay (weight 0.05) ──
  let timeSignal = 0
  if (shaReachable) {
    const commitTime = Bash(`git show -s --format=%ct "${planSha}" 2>/dev/null`)
    const commitEpoch = parseInt(commitTime.stdout.trim(), 10) || 0
    if (!isNaN(commitEpoch) && commitEpoch > 0) {
      const daysSince = (Date.now() / 1000 - commitEpoch) / 86400
      if (daysSince > 90) timeSignal = 1.0
      else if (daysSince > 60) timeSignal = 0.6
      else if (daysSince > 30) timeSignal = 0.3
    }
  } else if (planDate) {
    const planEpoch = new Date(planDate).getTime() / 1000
    if (!isNaN(planEpoch)) {
      const daysSince = (Date.now() / 1000 - planEpoch) / 86400
      if (daysSince > 90) timeSignal = 1.0
      else if (daysSince > 60) timeSignal = 0.6
      else if (daysSince > 30) timeSignal = 0.3
    } else {
      timeSignal = 0.5  // Malformed date — neutral fallback
    }
  }

  // ── Composite Score ──
  const weights = { commit_distance: 0.25, file_drift: 0.35, identifier_loss: 0.25, branch_divergence: 0.10, time_decay: 0.05 }
  const weightedSum =
    commitSignal * weights.commit_distance +
    fileDriftSignal * weights.file_drift +
    identifierLossSignal * weights.identifier_loss +
    branchSignal * weights.branch_divergence +
    timeSignal * weights.time_decay

  const freshnessScore = clamp(1 - weightedSum, 0, 1)

  // ── Decision ──
  freshnessResult = {
    score: freshnessScore,
    signals: {
      commit_distance: { raw: commitDistance, normalized: commitSignal },
      file_drift: { files_checked: referencedFiles.length, drifted: driftCount, normalized: fileDriftSignal },
      identifier_loss: { ids_checked: identifiers.length, lost: lostCount, normalized: identifierLossSignal },
      branch_divergence: { plan_branch: planBranch, current_branch: currentBranch, normalized: branchSignal },
      time_decay: { normalized: timeSignal }
    },
    git_sha: planSha, sha_reachable: shaReachable,
    status: "PASS", checked_at: new Date().toISOString()
  }

  if (freshnessScore < config.block_threshold) {
    freshnessResult.status = "STALE"
    const answer = AskUserQuestion({
      questions: [{
        question: `Plan freshness: ${freshnessScore.toFixed(2)}/1.0 (STALE). ${commitDistance} commits, ${fileDriftSignal > 0 ? Math.round(fileDriftSignal * 100) + '% file drift' : 'no file drift'}. Proceed?`,
        header: "Staleness",
        options: [
          { label: "Re-plan (Recommended)", description: "Run /rune:plan to create fresh plan" },
          { label: "Show drift details", description: "Display full signal breakdown" },
          { label: "Override and proceed", description: "Accept stale plan risk — logged to checkpoint" },
          { label: "Abort arc", description: "Cancel the arc pipeline" }
        ], multiSelect: false
      }]
    })
    if (!answer || answer.startsWith("Abort")) { /* exit arc cleanly */ return }
    if (answer.startsWith("Re-plan")) { /* exit arc, suggest /rune:plan */ return }
    if (answer.startsWith("Show drift")) {
      // FLAW-002 FIX: Display signal breakdown, then re-prompt without "Show drift details"
      log(`Signal breakdown:\n` +
        `  Commit Distance: ${commitDistance} commits (normalized: ${commitSignal.toFixed(3)})\n` +
        `  File Drift: ${driftCount}/${referencedFiles.length} files (normalized: ${fileDriftSignal.toFixed(3)})\n` +
        `  Identifier Loss: ${lostCount}/${identifiers.length} ids (normalized: ${identifierLossSignal.toFixed(3)})\n` +
        `  Branch Divergence: ${planBranch || 'n/a'} → ${currentBranch || 'n/a'} (normalized: ${branchSignal.toFixed(3)})\n` +
        `  Time Decay: ${timeSignal.toFixed(3)}`)
      const followUp = AskUserQuestion({
        questions: [{
          question: `Plan freshness: ${freshnessScore.toFixed(2)}/1.0 (STALE). What would you like to do?`,
          header: "Staleness",
          options: [
            { label: "Re-plan (Recommended)", description: "Run /rune:plan to create fresh plan" },
            { label: "Override and proceed", description: "Accept stale plan risk — logged to checkpoint" },
            { label: "Abort arc", description: "Cancel the arc pipeline" }
          ], multiSelect: false
        }]
      })
      if (!followUp || followUp.startsWith("Abort")) { return }
      if (followUp.startsWith("Re-plan")) { return }
      if (followUp.startsWith("Override")) { freshnessResult.status = "STALE-OVERRIDE" }
    }
    if (answer.startsWith("Override")) { freshnessResult.status = "STALE-OVERRIDE" }
  } else if (freshnessScore < config.warn_threshold) {
    freshnessResult.status = "WARN"
    warn(`Plan freshness: ${freshnessScore.toFixed(2)}/1.0 — ${commitDistance} commits since plan creation`)
  }

  // G14: Write freshness report artifact
  const report = `# Plan Freshness Report\n\n` +
    `**Score**: ${freshnessScore.toFixed(3)}/1.0\n` +
    `**Status**: ${freshnessResult.status}\n` +
    `**Plan SHA**: ${planSha}\n` +
    `**Current HEAD**: ${Bash('git rev-parse --short HEAD').stdout.trim()}\n` +
    `**Checked at**: ${freshnessResult.checked_at}\n\n` +
    `## Signal Breakdown\n\n` +
    `| Signal | Weight | Raw | Normalized |\n|--------|--------|-----|------------|\n` +
    `| Commit Distance | 0.25 | ${commitDistance} commits | ${commitSignal.toFixed(3)} |\n` +
    `| File Drift | 0.35 | ${driftCount}/${referencedFiles.length} files | ${fileDriftSignal.toFixed(3)} |\n` +
    `| Identifier Loss | 0.25 | ${lostCount}/${identifiers.length} ids | ${identifierLossSignal.toFixed(3)} |\n` +
    `| Branch Divergence | 0.10 | ${planBranch || 'n/a'} → ${currentBranch || 'n/a'} | ${branchSignal.toFixed(3)} |\n` +
    `| Time Decay | 0.05 | — | ${timeSignal.toFixed(3)} |\n`
  Write(`tmp/arc/${id}/freshness-report.md`, report)
  } // end else — signal computation (LOGIC-1: skip guard)
}
```

### Total Pipeline Timeout Check

**Limitation**: `checkArcTimeout()` runs **between phases**, not during a phase. If a phase is stuck internally, arc cannot interrupt it. A phase that exceeds its budget will only be detected after it finishes or times out on its own inner timeout. This is why inner polling timeouts must be derived from outer phase budgets (minus setup overhead) — the inner timeout is the real enforcement mechanism.

```javascript
const arcStart = Date.now()

function checkArcTimeout() {
  const elapsed = Date.now() - arcStart
  if (elapsed > ARC_TOTAL_TIMEOUT) {
    error(`Arc pipeline exceeded ${ARC_TOTAL_TIMEOUT / 60_000}-minute total timeout (elapsed: ${Math.round(elapsed/60000)}min).`)
    updateCheckpoint({ status: "timeout" })
    return true
  }
  return false
}
```

### Initialize Checkpoint (ARC-2)

```javascript
const id = `arc-${Date.now()}`
if (!/^arc-[a-zA-Z0-9_-]+$/.test(id)) throw new Error("Invalid arc identifier")
const sessionNonce = crypto.randomBytes(6).toString('hex')

Write(`.claude/arc/${id}/checkpoint.json`, {
  id, schema_version: 5, plan_file: planFile,
  flags: { approve: approveFlag, no_forge: noForgeFlag, skip_freshness: skipFreshnessFlag },
  freshness: freshnessResult || null,
  session_nonce: sessionNonce, phase_sequence: 0,
  phases: {
    forge:        { status: noForgeFlag ? "skipped" : "pending", artifact: null, artifact_hash: null, team_name: null },
    plan_review:  { status: "pending", artifact: null, artifact_hash: null, team_name: null },
    plan_refine:  { status: "pending", artifact: null, artifact_hash: null, team_name: null },
    verification: { status: "pending", artifact: null, artifact_hash: null, team_name: null },
    work:         { status: "pending", artifact: null, artifact_hash: null, team_name: null },
    gap_analysis: { status: "pending", artifact: null, artifact_hash: null, team_name: null },
    code_review:  { status: "pending", artifact: null, artifact_hash: null, team_name: null },
    mend:         { status: "pending", artifact: null, artifact_hash: null, team_name: null },
    verify_mend:  { status: "pending", artifact: null, artifact_hash: null, team_name: null },
    audit:        { status: "pending", artifact: null, artifact_hash: null, team_name: null }
  },
  convergence: { round: 0, max_rounds: CONVERGENCE_MAX_ROUNDS, history: [] },
  commits: [],
  started_at: new Date().toISOString(),
  updated_at: new Date().toISOString()
})
```

## --resume Logic

On resume, validate checkpoint integrity before proceeding:

```
1. Find most recent checkpoint: find .claude/arc -name checkpoint.json -maxdepth 2 -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1 | awk '{print $2}'
2. Read .claude/arc/{id}/checkpoint.json — extract plan_file for downstream phases
3. Schema migration (default missing schema_version: `const version = checkpoint.schema_version ?? 1`):
   if version < 2, migrate v1 → v2:
   a. Add plan_refine: { status: "skipped", ... }
   b. Add verification: { status: "skipped", ... }
   c. Set schema_version: 2
3b. If schema_version < 3, migrate v2 → v3:
   a. Add verify_mend: { status: "skipped", ... }
   b. Add convergence: { round: 0, max_rounds: 2, history: [] }
   c. Set schema_version: 3
3c. If schema_version < 4, migrate v3 → v4:
   a. Add gap_analysis: { status: "skipped", ... }
   b. Set schema_version: 4
3d. If schema_version < 5, migrate v4 → v5:
   a. Add freshness: null
   b. Add flags.skip_freshness: false
   c. Set schema_version: 5
3e. Resume freshness re-check:
   a. Read plan file from checkpoint.plan_file
   b. Extract git_sha from plan frontmatter
   c. If plan's git_sha differs from checkpoint.freshness?.git_sha, re-run freshness check
   d. If previous status was STALE-OVERRIDE, skip re-asking (preserve override decision)
   e. Store updated freshnessResult in checkpoint
4. Validate phase ordering using PHASE_ORDER array (by name, not phase_sequence numbers):
   a. For each "completed" phase, verify no later phase has an earlier timestamp
   b. Normalize "timeout" status to "failed" (both are resumable)
5. For each phase marked "completed":
   a. Verify artifact file exists at recorded path
   b. Compute SHA-256 of artifact, compare against stored artifact_hash
   c. If hash mismatch → demote phase to "pending" + warn user
6. Resume from first incomplete/failed/pending phase in PHASE_ORDER
```

Hash mismatch warning:
```
WARNING: Artifact for Phase 2 (plan-review.md) has been modified since checkpoint.
Hash expected: sha256:abc123...
Hash found: sha256:xyz789...
Demoting Phase 2 to "pending" — will re-run plan review.
```

## Phase 1: FORGE (skippable with --no-forge)

Delegate to `/rune:forge` logic for Forge Gaze topic-aware enrichment. Forge manages its own team lifecycle (TeamCreate/TeamDelete). The arc orchestrator wraps with checkpoint management and provides a working copy of the plan.

**Team**: Delegated to `/rune:forge` — manages its own TeamCreate/TeamDelete with guards (see rune-orchestration/references/team-lifecycle-guard.md).
**Tools**: Delegated — forge agents receive read-only tools (Read, Glob, Grep, Write for own output file only)

**Forge Gaze features (via delegation)**:
- Topic-to-agent matching: each plan section gets specialized agents based on keyword overlap scoring
- Codex Oracle: conditional cross-model enrichment (if `codex` CLI available)
- Custom Ashes: talisman.yml `ashes.custom` with `workflows: [forge]`
- Section-level enrichment: Enrichment Output Format (Best Practices, Performance, Edge Cases, etc.)

### Codex Oracle in Forge (conditional)

Run the canonical Codex detection algorithm per `roundtable-circle/references/codex-detection.md`. If detected and `forge` is in `talisman.codex.workflows` (default: yes), include Codex Oracle as an additional forge enrichment agent.

Codex Oracle output: `tmp/arc/{id}/research/codex-oracle.md`

**Inputs**: planFile (string, validated at arc init), id (string, validated at arc init)
**Outputs**: `tmp/arc/{id}/enriched-plan.md` (enriched copy of original plan)
**Preconditions**: planFile exists, noForgeFlag is false
**Error handling**: Forge timeout (10 min) → proceed with original plan copy (warn user, offer `--no-forge`). Team lifecycle failure → delegated to forge pre-create guard. No enrichments → use original plan copy.

```javascript
updateCheckpoint({ phase: "forge", status: "in_progress", phase_sequence: 1, team_name: null })

// Create working copy for forge to enrich
Bash(`mkdir -p "tmp/arc/${id}"`)
Bash(`cp -- "${planFile}" "tmp/arc/${id}/enriched-plan.md"`)
const forgePlanPath = `tmp/arc/${id}/enriched-plan.md`

// Invoke /rune:forge logic on working copy
// Arc context adaptations (detected by forge via path prefix "tmp/arc/"):
//   - Phase 3 (scope confirmation): SKIPPED — arc is automated
//   - Phase 6 (post-enhancement options): SKIPPED — arc continues to Phase 2
//   - Forge Gaze mode: "default"

const forgeTeamName = /* team name created by /rune:forge logic */
updateCheckpoint({ phase: "forge", status: "in_progress", phase_sequence: 1, team_name: forgeTeamName })

// NOTE: Within-phase timeout enforcement is handled by forge's own internal timeout.
// The between-phase checkArcTimeout() (line 222) provides arc-level safety net.

// Verify enriched plan exists and has content
const enrichedPlan = Read(forgePlanPath)
if (!enrichedPlan || enrichedPlan.trim().length === 0) {
  warn("Forge produced empty output. Using original plan.")
  Bash(`cp -- "${planFile}" "${forgePlanPath}"`)
}

const writtenContent = Read(forgePlanPath)
updateCheckpoint({
  phase: "forge", status: "completed",
  artifact: forgePlanPath, artifact_hash: sha256(writtenContent), phase_sequence: 1
})
```

**Output**: `tmp/arc/{id}/enriched-plan.md`

If forge times out or fails: proceed with original plan copy + warn user. Offer `--no-forge` on retry.

## Phase 2: PLAN REVIEW (circuit breaker)

Three parallel reviewers evaluate the enriched plan. Any BLOCK verdict halts the pipeline.

**Team**: `arc-plan-review-{id}`
**Tools (read-only)**: Read, Glob, Grep, Write (own output file only)

```javascript
updateCheckpoint({ phase: "plan_review", status: "in_progress", phase_sequence: 2, team_name: `arc-plan-review-${id}` })

// Pre-create guard (see rune-orchestration/references/team-lifecycle-guard.md)
// SEC-003: Redundant path traversal check — defense-in-depth with line 212 validation
if (id.includes('..')) throw new Error('Path traversal detected in arc id')
try { TeamDelete() } catch (e) {
  Bash(`rm -rf ~/.claude/teams/arc-plan-review-${id}/ ~/.claude/tasks/arc-plan-review-${id}/ 2>/dev/null`)
}
TeamCreate({ team_name: `arc-plan-review-${id}` })

const reviewers = [
  { name: "scroll-reviewer", agent: "agents/utility/scroll-reviewer.md", focus: "Document quality" },
  { name: "decree-arbiter", agent: "agents/utility/decree-arbiter.md", focus: "Technical soundness" },
  { name: "knowledge-keeper", agent: "agents/utility/knowledge-keeper.md", focus: "Documentation coverage" }
]

for (const reviewer of reviewers) {
  Task({
    team_name: `arc-plan-review-${id}`, name: reviewer.name,
    subagent_type: "general-purpose",
    prompt: `Review plan for: ${reviewer.focus}
      Plan: tmp/arc/${id}/enriched-plan.md
      Output: tmp/arc/${id}/reviews/${reviewer.name}-verdict.md
      Include structured verdict marker: <!-- VERDICT:${reviewer.name}:{PASS|CONCERN|BLOCK} -->`,
    run_in_background: true
  })
}

// Parse verdicts using anchored regex
const parseVerdict = (reviewer, output) => {
  const pattern = /^<!-- VERDICT:([a-zA-Z_-]+):(PASS|CONCERN|BLOCK) -->$/m
  const match = output.match(pattern)
  if (!match) { warn(`Reviewer ${reviewer} output lacks verdict marker — defaulting to CONCERN.`); return "CONCERN" }
  if (match[1] !== reviewer) warn(`Verdict marker reviewer mismatch: expected ${reviewer}, found ${match[1]}.`)
  return match[2]
}

// Monitor with timeout — see monitor-utility.md
const result = waitForCompletion(`arc-plan-review-${id}`, reviewers.length, {
  timeoutMs: PHASE_TIMEOUTS.plan_review, staleWarnMs: STALE_THRESHOLD,
  pollIntervalMs: 30_000, label: "Arc: Plan Review"
})

result.completed.forEach(t => { const r = reviewers.find(r => r.name === t.owner); if (r) r.completed = true })

if (result.timedOut) {
  warn("Phase 2 (PLAN REVIEW) timed out.")
  for (const reviewer of reviewers) {
    if (!reviewer.completed) {
      const outputPath = `tmp/arc/${id}/reviews/${reviewer.name}-verdict.md`
      reviewer.verdict = exists(outputPath) ? parseVerdict(reviewer.name, Read(outputPath)) : "CONCERN"
    }
  }
}

// Collect verdicts, merge → tmp/arc/{id}/plan-review.md
// Dynamic member discovery — reads team config to find ALL teammates
// This catches teammates summoned in any phase, not just the initial batch
let allMembers = []
try {
  const teamConfig = Read(`~/.claude/teams/arc-plan-review-${id}/config.json`)
  const members = Array.isArray(teamConfig.members) ? teamConfig.members : []
  allMembers = members.map(m => m.name).filter(Boolean)
  // Defense-in-depth: SDK already excludes team-lead from config.members
} catch (e) {
  // FALLBACK: Phase 2 plan review — these are the 3 reviewers summoned in this specific phase
  allMembers = ["scroll-reviewer", "decree-arbiter", "knowledge-keeper"]
}

// Shutdown all discovered members
for (const member of allMembers) { SendMessage({ type: "shutdown_request", recipient: member, content: "Plan review complete" }) }
// SEC-003: id validated at line 212 (/^arc-[a-zA-Z0-9_-]+$/) + redundant traversal check above
try { TeamDelete() } catch (e) {
  Bash(`rm -rf ~/.claude/teams/arc-plan-review-${id}/ ~/.claude/tasks/arc-plan-review-${id}/ 2>/dev/null`)
}
```

**Circuit breaker**: Parse `<!-- VERDICT:{reviewer}:{verdict} -->` markers.

| Condition | Action |
|-----------|--------|
| Any reviewer returns BLOCK | HALT pipeline, report blocking reviewer + reason |
| All PASS (with optional CONCERNs) | Proceed to Phase 2.5 |

```
updateCheckpoint({
  phase: "plan_review", status: blocked ? "failed" : "completed",
  artifact: `tmp/arc/${id}/plan-review.md`, artifact_hash: sha256(planReview), phase_sequence: 2
})
```

**Output**: `tmp/arc/{id}/plan-review.md`

If blocked: user fixes plan, then `/rune:arc --resume`.

## Phase 2.5: PLAN REFINEMENT (conditional)

Extract CONCERN details from reviewer outputs and propagate as context to the work phase. Orchestrator-only — no team creation, no agents.

**Team**: None (orchestrator-only)
**Tools**: Read, Write, Glob, Grep
**Duration**: Max 3 minutes
**Trigger**: Any CONCERN verdict exists. If all PASS, skip.

```javascript
updateCheckpoint({ phase: "plan_refine", status: "in_progress", phase_sequence: 3, team_name: null })

const concerns = []
for (const reviewer of reviewers) {
  const outputPath = `tmp/arc/${id}/reviews/${reviewer.name}-verdict.md`
  if (!exists(outputPath)) continue
  const output = Read(outputPath)
  const verdict = parseVerdict(reviewer.name, output)
  if (verdict === "CONCERN") {
    const sanitized = output
      .replace(/<!--[\s\S]*?-->/g, '')
      .replace(/```[\s\S]*?```/g, '[code block removed]')
      .slice(0, 2000)
    concerns.push({ reviewer: reviewer.name, verdict: "CONCERN", content: sanitized })
  }
}

if (concerns.length === 0) {
  updateCheckpoint({ phase: "plan_refine", status: "skipped", phase_sequence: 3, team_name: null })
} else {
  // Phase 2.5 is extraction-only. It does not modify the plan.
  const concernContext = concerns.map(c => `## ${c.reviewer} — CONCERN\n\n${c.content}`).join('\n\n---\n\n')
  Write(`tmp/arc/${id}/concern-context.md`, `# Plan Review Concerns\n\n` +
    `Total concerns: ${concerns.length}\n` +
    `Reviewers with concerns: ${concerns.map(c => c.reviewer).join(', ')}\n\n` +
    `Workers should address these concerns during implementation.\n\n` + concernContext)

  // All-CONCERN escalation (3x CONCERN, 0 PASS)
  const allConcern = reviewers.every(r => {
    const verdictPath = `tmp/arc/${id}/reviews/${r.name}-verdict.md`
    if (!exists(verdictPath)) return true
    return parseVerdict(r.name, Read(verdictPath)) === "CONCERN"
  })
  if (allConcern) {
    const forgeNote = checkpoint.flags.no_forge
      ? "\n\nNote: Forge enrichment was skipped (--no-forge). CONCERNs may be more likely on a raw plan."
      : ""
    const escalationResponse = AskUserQuestion({
      question: `All 3 reviewers raised concerns (no PASS verdicts).${forgeNote} Proceed to implementation?`,
      header: "Escalate",
      options: [
        { label: "Proceed with warnings", description: "Implementation will include concern context" },
        { label: "Halt and fix manually", description: "Fix plan, then /rune:arc --resume" },
        { label: "Re-run plan review", description: "Revert to Phase 2 with updated plan" }
      ]
    })

    // CDX-015 MITIGATION (P3): Handle all-CONCERN escalation response branches
    // SEC-2 FIX: Null-guard AskUserQuestion return value
    if (!escalationResponse) {
      updateCheckpoint({ phase: "plan_refine", status: "failed", phase_sequence: 3, team_name: null })
      error("Arc halted — escalation dialog returned null. Fix plan, then /rune:arc --resume")
      return
    }
    if (escalationResponse.includes("Halt")) {
      updateCheckpoint({ phase: "plan_refine", status: "failed", phase_sequence: 3, team_name: null })
      error("Arc halted by user at all-CONCERN escalation. Fix plan, then /rune:arc --resume")
      return
    } else if (escalationResponse.includes("Re-run")) {
      // Demote plan_review to pending so --resume re-runs Phase 2
      updateCheckpoint({
        phase: "plan_review", status: "pending", phase_sequence: 2,
        artifact: null, artifact_hash: null
      })
      updateCheckpoint({ phase: "plan_refine", status: "pending", phase_sequence: 3, team_name: null })
      error("Arc reverted to Phase 2 (PLAN REVIEW). Run /rune:arc --resume to re-review.")
      return
    }
    // "Proceed with warnings" — fall through to normal completion below
  }

  const writtenContent = Read(`tmp/arc/${id}/concern-context.md`)
  updateCheckpoint({
    phase: "plan_refine", status: "completed",
    artifact: `tmp/arc/${id}/concern-context.md`, artifact_hash: sha256(writtenContent),
    phase_sequence: 3, team_name: null
  })
}
```

**Output**: `tmp/arc/{id}/concern-context.md` (or skipped if no CONCERNs)
**Failure policy**: Non-blocking — proceed with unrefined plan + deferred concerns as context.

## Phase 2.7: VERIFICATION GATE (deterministic)

Zero-LLM-cost deterministic checks on the enriched plan. Orchestrator-only — no team, no agents. Runs 8 checks + report: file references, heading links, acceptance criteria, TODO/FIXME markers, talisman verification patterns, pseudocode contract headers, undocumented security pattern declarations, and post-forge freshness re-check.

**Inputs**: enrichedPlanPath (string), talisman config
**Outputs**: `tmp/arc/{id}/verification-report.md`
**Error handling**: Non-blocking — proceed with warnings. Log issues but do not halt.

See [verification-gate.md](../skills/rune-orchestration/references/verification-gate.md) for the full algorithm.

## Phase 5: WORK

Invoke `/rune:work` logic on the enriched plan. Swarm workers implement tasks with incremental commits.

**Team**: `arc-work-{id}`
**Tools (full access)**: Read, Write, Edit, Bash, Glob, Grep
**Team lifecycle**: Delegated to `/rune:work` — manages its own TeamCreate/TeamDelete with guards (see rune-orchestration/references/team-lifecycle-guard.md).

```javascript
createFeatureBranchIfNeeded()

let workContext = ""

// Include reviewer concerns if any
if (exists(`tmp/arc/${id}/concern-context.md`)) {
  workContext += `\n\n## Reviewer Concerns\nSee tmp/arc/${id}/concern-context.md for full details.`
}

// Include verification warnings if any
if (exists(`tmp/arc/${id}/verification-report.md`)) {
  const verReport = Read(`tmp/arc/${id}/verification-report.md`)
  const issueCount = (verReport.match(/^- /gm) || []).length
  if (issueCount > 0) {
    workContext += `\n\n## Verification Warnings (${issueCount} issues)\nSee tmp/arc/${id}/verification-report.md.`
  }
}

// Quality contract for all workers
workContext += `\n\n## Quality Contract\nAll code must include:\n- Type annotations on all function signatures\n- Docstrings on all public functions, classes, and modules\n- Error handling with specific exception types (no bare except)\n- Test coverage target: >=80% for new code`

const workTeamName = /* team name created by /rune:work logic */
updateCheckpoint({ phase: "work", status: "in_progress", phase_sequence: 5, team_name: workTeamName })

// After work completes, produce work summary
Write(`tmp/arc/${id}/work-summary.md`, {
  tasks_completed: completedCount, tasks_failed: failedCount,
  files_committed: committedFiles, uncommitted_changes: uncommittedList, commits: commitSHAs
})

updateCheckpoint({
  phase: "work", status: completedRatio >= 0.5 ? "completed" : "failed",
  artifact: `tmp/arc/${id}/work-summary.md`, artifact_hash: sha256(workSummary),
  phase_sequence: 5, commits: commitSHAs
})
```

**Output**: Implemented code (committed) + `tmp/arc/{id}/work-summary.md`
**Failure policy**: Halt if <50% tasks complete. Partial work is committed via incremental commits (E5).

**--approve routing**: Routes to human user via AskUserQuestion (not to AI leader). Applies only to Phase 5. Do not propagate `--approve` when invoking `/rune:mend` in Phase 7 — mend fixers apply deterministic fixes from TOME findings.

## Phase 5.5: IMPLEMENTATION GAP ANALYSIS

Deterministic, orchestrator-only check that cross-references plan acceptance criteria against committed code changes. Zero LLM cost. Includes doc-consistency cross-checks (STEP 4.5), plan section coverage (STEP 4.7), and evaluator quality metrics (STEP 4.8).

**Inputs**: enriched plan, work summary, git diff
**Outputs**: `tmp/arc/{id}/gap-analysis.md`
**Error handling**: Non-blocking (WARN). Gap analysis is advisory — missing criteria are flagged but do not halt the pipeline. Evaluator quality metrics (docstring coverage, function length, evaluation tests) are informational for Phase 6 reviewers.

See [gap-analysis.md](../skills/rune-orchestration/references/gap-analysis.md) for the full algorithm.

## Phase 6: CODE REVIEW

Invoke `/rune:review` logic on the implemented changes. Summons Ash with Roundtable Circle lifecycle.

**Team**: `arc-review-{id}`
**Tools (read-only)**: Read, Glob, Grep, Write (own output file only)
**Team lifecycle**: Delegated to `/rune:review` — manages its own TeamCreate/TeamDelete with guards (see rune-orchestration/references/team-lifecycle-guard.md).

**Codex Oracle**: Run Codex detection per `roundtable-circle/references/codex-detection.md`. If detected and `review` is in `talisman.codex.workflows`, include Codex Oracle. Findings use `CDX` prefix and participate in dedup and TOME aggregation.

```javascript
// Propagate gap analysis to reviewers as additional context
let reviewContext = ""
if (exists(`tmp/arc/${id}/gap-analysis.md`)) {
  const gapReport = Read(`tmp/arc/${id}/gap-analysis.md`)
  const missingMatch = gapReport.match(/\| MISSING \| (\d+) \|/)
  const missingCount = missingMatch ? parseInt(missingMatch[1], 10) : 0
  const partialMatch = gapReport.match(/\| PARTIAL \| (\d+) \|/)
  const partialCount = partialMatch ? parseInt(partialMatch[1], 10) : 0
  if (missingCount > 0 || partialCount > 0) {
    reviewContext = `\n\nGap Analysis Context: ${missingCount} MISSING, ${partialCount} PARTIAL criteria.\nSee tmp/arc/${id}/gap-analysis.md.`
  }
}

const reviewTeamName = /* team name created by /rune:review logic */
updateCheckpoint({ phase: "code_review", status: "in_progress", phase_sequence: 6, team_name: reviewTeamName })

// Move TOME: tmp/reviews/{review-id}/TOME.md → tmp/arc/{id}/tome.md
updateCheckpoint({
  phase: "code_review", status: "completed",
  artifact: `tmp/arc/${id}/tome.md`, artifact_hash: sha256(tome), phase_sequence: 6
})
```

**Output**: `tmp/arc/{id}/tome.md`

**Docs-only work output**: If Phase 5 produced only documentation files, the review still runs correctly. Rune Gaze's docs-only override ensures Knowledge Keeper is summoned. The TOME will contain `DOC-` and `QUAL-` prefixed findings.

**Failure policy**: Review always produces findings or a clean report. Does not halt.

## Phase 7: MEND

Invoke `/rune:mend` logic on the TOME. Parallel fixers resolve findings.

**Team**: `arc-mend-{id}` (orchestrator team); fixers get restricted tools
**Team lifecycle**: Delegated to `/rune:mend` — manages its own TeamCreate/TeamDelete with guards (see rune-orchestration/references/team-lifecycle-guard.md).

```javascript
const mendRound = checkpoint.convergence?.round || 0
const tomeSource = mendRound === 0
  ? `tmp/arc/${id}/tome.md`
  : `tmp/arc/${id}/tome-round-${mendRound}.md`

const mendTimeout = mendRound === 0 ? PHASE_TIMEOUTS.mend : MEND_RETRY_TIMEOUT

// BUG FIX (v1.24.1): Propagate arc phase budget to mend's inner polling timeout.
// Without --timeout, mend always uses 15 min (standalone default) — which exceeds
// arc's retry budget (13 min) and ignores setup/teardown overhead.
// Inner polling = mendTimeout - SETUP_BUDGET - MEND_EXTRA_BUDGET (min 2 min).
const mendTeamName = /* team name created by /rune:mend logic, invoked with --timeout ${mendTimeout} */
updateCheckpoint({ phase: "mend", status: "in_progress", phase_sequence: 7, team_name: mendTeamName })

const failedCount = countFindings("FAILED", resolutionReport)
updateCheckpoint({
  phase: "mend", status: failedCount > 3 ? "failed" : "completed",
  artifact: `tmp/arc/${id}/resolution-report.md`, artifact_hash: sha256(resolutionReport), phase_sequence: 7
})
```

**Output**: `tmp/arc/{id}/resolution-report.md`
**Failure policy**: Halt if >3 FAILED findings remain. User manually fixes, runs `/rune:arc --resume`.

## Phase 7.5: VERIFY MEND (convergence gate)

Lightweight orchestrator-only check that detects regressions introduced by mend fixes. Compares finding counts, runs a targeted spot-check on modified files, and decides whether to retry mend or proceed to audit.

**Inputs**: resolution report, TOME, committed files
**Outputs**: `tmp/arc/{id}/spot-check-round-{N}.md` (or mini-TOME on retry: `tmp/arc/{id}/tome-round-{N}.md`)
**Error handling**: Non-blocking — halting proceeds to audit with warning. The convergence gate either retries or gives up gracefully.

See [verify-mend.md](../skills/rune-orchestration/references/verify-mend.md) for the full algorithm.

## Phase 8: AUDIT (informational)

Invoke `/rune:audit` logic as a final quality gate. Informational — does not halt the pipeline.

**Team**: `arc-audit-{id}`
**Tools (read-only)**: Read, Glob, Grep, Write (own output file only)
**Team lifecycle**: Delegated to `/rune:audit` — manages its own TeamCreate/TeamDelete with guards (see rune-orchestration/references/team-lifecycle-guard.md).

**Codex Oracle**: Run Codex detection per `roundtable-circle/references/codex-detection.md`. If detected and `audit` is in `talisman.codex.workflows`, include Codex Oracle. Findings use `CDX` prefix.

```javascript
const auditTeamName = /* team name created by /rune:audit logic */
updateCheckpoint({ phase: "audit", status: "in_progress", phase_sequence: 9, team_name: auditTeamName })

updateCheckpoint({
  phase: "audit", status: "completed",
  artifact: `tmp/arc/${id}/audit-report.md`, artifact_hash: sha256(auditReport), phase_sequence: 9
})
```

**Output**: `tmp/arc/{id}/audit-report.md`
**Failure policy**: Report results. Does not halt — informational final gate.

## Phase Transition Contracts (ARC-3)

| From | To | Artifact | Contract |
|------|----|----------|----------|
| FORGE | PLAN REVIEW | `enriched-plan.md` | Markdown plan with enriched sections |
| PLAN REVIEW | PLAN REFINEMENT | `plan-review.md` | 3 reviewer verdicts (PASS/CONCERN/BLOCK) |
| PLAN REFINEMENT | VERIFICATION | `concern-context.md` | Extracted concern list. Plan not modified |
| VERIFICATION | WORK | `verification-report.md` | Deterministic check results (PASS/WARN) |
| WORK | GAP ANALYSIS | Working tree + `work-summary.md` | Git diff of committed changes + task summary |
| GAP ANALYSIS | CODE REVIEW | `gap-analysis.md` | Criteria coverage (ADDRESSED/MISSING/PARTIAL) |
| CODE REVIEW | MEND | `tome.md` | TOME with `<!-- RUNE:FINDING ... -->` markers |
| MEND | VERIFY MEND | `resolution-report.md` | Fixed/FP/Failed finding list |
| VERIFY MEND | MEND (retry) | `tome-round-{N}.md` | Mini-TOME with RUNE:FINDING from spot-check |
| VERIFY MEND | AUDIT | `spot-check-round-{N}.md` | Spot-check results (SPOT:FINDING or SPOT:CLEAN) |
| AUDIT | Done | `audit-report.md` | Final audit report. Pipeline summary to user |

## Failure Policy (ARC-5)

| Phase | On Failure | Recovery |
|-------|-----------|----------|
| FORGE | Proceed with original plan copy + warn. Offer `--no-forge` on retry | `/rune:arc --resume --no-forge` |
| PLAN REVIEW | Halt if any BLOCK verdict | User fixes plan, `/rune:arc --resume` |
| PLAN REFINEMENT | Non-blocking — proceed with deferred concerns | Advisory phase |
| VERIFICATION | Non-blocking — proceed with warnings | Informational |
| WORK | Halt if <50% tasks complete. Partial commits preserved | `/rune:arc --resume` |
| GAP ANALYSIS | Non-blocking — WARN only | Advisory context for code review |
| CODE REVIEW | Does not halt | Produces findings or clean report |
| MEND | Halt if >3 FAILED findings | User fixes, `/rune:arc --resume` |
| VERIFY MEND | Non-blocking — retries up to 2x, then proceeds | Convergence gate is advisory |
| AUDIT | Does not halt — informational | User reviews audit report |

## Completion Report

```
The Tarnished has claimed the Elden Throne.

Plan: {plan_file}
Checkpoint: .claude/arc/{id}/checkpoint.json
Branch: {branch_name}

Phases:
  1.   FORGE:           {status} — enriched-plan.md
  2.   PLAN REVIEW:     {status} — plan-review.md ({verdict})
  2.5  PLAN REFINEMENT: {status} — {concerns_count} concerns extracted
  2.7  VERIFICATION:    {status} — {issues_count} issues
  5.   WORK:            {status} — {tasks_completed}/{tasks_total} tasks
  5.5  GAP ANALYSIS:    {status} — {addressed}/{total} criteria addressed
  6.   CODE REVIEW:     {status} — tome.md ({finding_count} findings)
  7.   MEND:            {status} — {fixed}/{total} findings resolved
  7.5  VERIFY MEND:     {status} — {convergence_verdict} (round {round}/{max_rounds})
  8.   AUDIT:           {status} — audit-report.md

Convergence: {convergence.round + 1} mend pass(es)
  {for each entry in convergence.history:}
  Round {N}: {findings_before} → {findings_after} findings ({verdict})

Commits: {commit_count} on branch {branch_name}
Files changed: {file_count}
Time: {total_duration}

Artifacts: tmp/arc/{id}/
Checkpoint: .claude/arc/{id}/checkpoint.json

Next steps:
1. Review audit report: tmp/arc/{id}/audit-report.md
2. git log --oneline — Review commits
3. Create PR for branch {branch_name}
4. /rune:rest — Clean up tmp/ artifacts when done
```

### Post-Arc Echo Persist

After the completion report, persist arc quality metrics to echoes for cross-session learning:

```javascript
if (exists(".claude/echoes/")) {
  const metrics = {
    plan: checkpoint.plan_file,
    duration_minutes: Math.round(totalDuration / 60),
    phases_completed: Object.values(checkpoint.phases).filter(p => p.status === "completed").length,
    tome_findings: { p1: p1Count, p2: p2Count, p3: p3Count },
    convergence_rounds: checkpoint.convergence.history.length,
    mend_fixed: mendFixedCount,
    gap_addressed: addressedCount,
    gap_missing: missingCount,
  }

  appendEchoEntry(".claude/echoes/planner/MEMORY.md", {
    layer: "inscribed",
    source: `rune:arc ${id}`,
    content: `Arc completed: ${metrics.phases_completed}/10 phases, ` +
      `${metrics.tome_findings.p1} P1 findings, ` +
      `${metrics.convergence_rounds} mend round(s), ` +
      `${metrics.gap_missing} missing criteria. ` +
      `Duration: ${metrics.duration_minutes}min.`
  })
}
```

## Error Handling

| Error | Recovery |
|-------|----------|
| Concurrent arc session active | Abort with warning, suggest `/rune:cancel-arc` |
| Plan file not found | Suggest `/rune:plan` first |
| Checkpoint corrupted | Warn user, offer fresh start or manual fix |
| Artifact hash mismatch on resume | Demote phase to pending, re-run |
| Phase timeout | Halt, preserve checkpoint, suggest `--resume` |
| BLOCK verdict in plan review | Halt, report blocker details |
| All-CONCERN escalation (3x CONCERN) | AskUserQuestion: proceed, halt, or re-run review |
| <50% work tasks complete | Halt, partial commits preserved |
| >3 FAILED mend findings | Halt, resolution report available |
| Worker crash mid-phase | Phase team cleanup, checkpoint preserved |
| Branch conflict | Warn user, suggest manual resolution |
| Total pipeline timeout (90 min) | Halt, preserve checkpoint, suggest `--resume` |
| Phase 2.5 timeout (>3 min) | Proceed with partial concern extraction |
| Phase 2.7 timeout (>30 sec) | Skip verification, log warning, proceed to WORK |
| Plan freshness STALE | AskUserQuestion with Re-plan/Override/Abort | User re-plans or overrides |
| Schema v1/v2/v3/v4 checkpoint on --resume | Auto-migrate to v5 |
| Verify mend spot-check timeout (>4 min) | Skip convergence check, proceed to audit with warning |
| Spot-check agent produces no output | Default to "halted" (fail-closed) |
| Findings diverging after mend | Halt convergence immediately, proceed to audit |
| Convergence circuit breaker (max 2 retries) | Stop retrying, proceed to audit with remaining findings |
