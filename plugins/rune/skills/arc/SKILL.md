---
name: arc
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
disable-model-invocation: true
argument-hint: "[plan-file-path | --resume]"
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

## CRITICAL — Agent Teams Enforcement (ATE-1)

**EVERY phase that summons agents MUST follow this exact pattern. No exceptions.**

```
1. TeamCreate({ team_name: "{phase-prefix}-{id}" })     ← CREATE TEAM FIRST
2. TaskCreate({ subject: ..., description: ... })         ← CREATE TASKS
3. Task({ team_name: "...", name: "...",                  ← SPAWN WITH team_name
     subagent_type: "general-purpose",                    ← ALWAYS general-purpose
     prompt: "You are {agent-name}...", ... })             ← IDENTITY VIA PROMPT
4. Monitor → Shutdown → TeamDelete with fallback          ← CLEANUP
```

**NEVER DO:**
- `Task({ ... })` without `team_name` — bare Task calls bypass Agent Teams entirely. No shared task list, no SendMessage, no context isolation. This is the root cause of context explosion.
- Using named `subagent_type` values (e.g., `"rune:utility:scroll-reviewer"`, `"compound-engineering:research:best-practices-researcher"`, `"rune:review:ward-sentinel"`) — these resolve to non-general-purpose agents. Always use `subagent_type: "general-purpose"` and inject agent identity via the prompt.

**WHY:** Without Agent Teams, agent outputs consume the orchestrator's context window (~200k). With 10 phases spawning agents, the orchestrator hits context limit after 2 phases. Agent Teams give each teammate its own 200k window. The orchestrator only reads artifact files.

**ENFORCEMENT:** The `enforce-teams.sh` PreToolUse hook blocks bare Task calls when a Rune workflow is active. If your Task call is blocked, add `team_name` to it.

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
const MEND_RETRY_TIMEOUT = 780_000   // 13 min (inner 5m polling + 5m setup + 3m ward/cross-file)

// Shared prototype pollution guard — used by prePhaseCleanup (ARC-6) and ORCH-1 resume cleanup.
// BACK-005 FIX: Single definition replaces two duplicate inline Sets.
const FORBIDDEN_PHASE_KEYS = new Set(['__proto__', 'constructor', 'prototype'])
```

See [phase-tool-matrix.md](references/phase-tool-matrix.md) for per-phase tool restrictions and time budget details.

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

  git checkout -b "$branch_name"
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
  # SEC-5 FIX: Place -maxdepth before -name for POSIX portability (BSD find on macOS)
  active=$(find .claude/arc -maxdepth 2 -name checkpoint.json 2>/dev/null | while read f; do
    jq -r 'select(.phases | to_entries | map(.value.status) | any(. == "in_progress")) | .id' "$f" 2>/dev/null
  done)
else
  # NOTE: grep fallback is imprecise — matches "in_progress" anywhere in file, not field-specific.
  # Acceptable as degraded-mode check when jq is unavailable. The jq path above is the robust check.
  active=$(find .claude/arc -maxdepth 2 -name checkpoint.json 2>/dev/null | while read f; do
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
// CDX-005 MITIGATION (P2): Explicit .. rejection — PRIMARY defense against path traversal.
// The regex above intentionally allows . and / for valid paths like "plans/2026-01-01-plan.md".
// This check is the real barrier against ../../../etc/passwd style traversal.
if (planFile.includes('..')) {
  error(`Path traversal detected in plan path: ${planFile}`)
  return
}
// CDX-009 MITIGATION: Reject leading-hyphen paths (option injection in cp, ls, etc.)
if (planFile.startsWith('-')) {
  error(`Plan path starts with hyphen (option injection risk): ${planFile}`)
  return
}
// CDX-009 EXTENSION: Reject internal double-hyphens (option terminator injection)
// A path like "plans/plan--version.md" could be misinterpreted as `--` by downstream
// Bash() calls that don't use `--` argument separators.
if (planFile.includes('--')) {
  error(`Plan path contains double-hyphen (option terminator risk): ${planFile}`)
  return
}
// Reject absolute paths — plan files must be relative to project root
if (planFile.startsWith('/')) {
  error(`Absolute paths not allowed: ${planFile}. Use a relative path from project root.`)
  return
}
// CDX-010 FIX: Reject symlinks — a symlink at plans/evil.md -> /etc/passwd would
// pass all regex/traversal checks above but read arbitrary files via Read().
// Use Bash test -L (not stat) for portability across macOS/Linux.
if (Bash(`test -L "${planFile}" && echo "symlink"`).includes("symlink")) {
  error(`Plan path is a symlink (not following): ${planFile}`)
  return
}
```

### Plan Freshness Check (FRESH-1)

See [freshness-gate.md](references/freshness-gate.md) for the full algorithm (5 weighted signals, composite score, STALE/WARN/PASS decision).

**Summary**: Zero-LLM-cost structural drift detection. Produces `freshnessResult` object stored in checkpoint + `tmp/arc/{id}/freshness-report.md`. Plans without `git_sha` skip the check (backward compat). STALE plans prompt user: re-plan, override, or abort.

Read and execute the algorithm from `references/freshness-gate.md`. Store `freshnessResult` for checkpoint initialization below.

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

### Inter-Phase Cleanup Guard (ARC-6)

Runs before every delegated phase to ensure no stale team blocks TeamCreate. Idempotent — harmless no-op when no stale team exists. Complements CDX-7 (crash recovery) — this handles normal phase transitions.

```javascript
// prePhaseCleanup(checkpoint): Clean stale teams from prior phases.
// Runs before EVERY delegated phase. See team-lifecycle-guard.md Pre-Create Guard.
// NOTE: Assumes checkpoint schema v5+ where each phase entry has { status, team_name, ... }

function prePhaseCleanup(checkpoint) {
  try {
    // Guard: validate checkpoint.phases exists and is an object
    if (!checkpoint?.phases || typeof checkpoint.phases !== 'object' || Array.isArray(checkpoint.phases)) {
      warn('ARC-6: Invalid checkpoint.phases — skipping inter-phase cleanup')
      return
    }

    // Strategy 1: Clear SDK session leadership state FIRST (while dirs still exist)
    // TeamDelete() targets the CURRENT SESSION's active team. Must run BEFORE rm -rf
    // so the SDK finds the directory and properly clears internal leadership tracking.
    // If dirs are already gone, TeamDelete may not clear state — hence "first" ordering.
    // See team-lifecycle-guard.md "Team Completion Verification" section.
    try { TeamDelete() } catch (e) { warn(`ARC-6: TeamDelete() cleanup: ${e.message}`) }

    // Strategy 2: Checkpoint-aware filesystem cleanup for ALL prior-phase teams
    // rm -rf targets named teams from checkpoint (may include teams this session
    // never led). TeamDelete can't target foreign teams — only rm -rf works here.
    for (const [phaseName, phaseInfo] of Object.entries(checkpoint.phases)) {
      if (FORBIDDEN_PHASE_KEYS.has(phaseName)) continue
      if (!phaseInfo || typeof phaseInfo !== 'object') continue
      if (!phaseInfo.team_name || typeof phaseInfo.team_name !== 'string') continue
      // ARC-6 STATUS GUARD: Denylist approach — only "in_progress" is preserved.
      // All other statuses (completed, failed, skipped, timeout, pending) are eligible for cleanup.
      // If a new active-state status is added to PHASE_ORDER, update this guard.
      if (phaseInfo.status === "in_progress") continue  // Don't clean actively running phase

      const teamName = phaseInfo.team_name

      // SEC-003: Validate BEFORE any filesystem operations — see security-patterns.md
      if (!/^[a-zA-Z0-9_-]+$/.test(teamName)) {
        warn(`ARC-6: Invalid team name for phase ${phaseName}: "${teamName}" — skipping`)
        continue
      }
      // Unreachable after regex — retained as defense-in-depth per SEC-003
      if (teamName.includes('..')) {
        warn('ARC-6: Path traversal detected in team name — skipping')
        continue
      }

      // SEC-002: rm -rf unconditionally — no exists() guard (eliminates TOCTOU window).
      // rm -rf on a nonexistent path is a no-op, so this is safe.
      // ARC-6: teamName validated above — contains only [a-zA-Z0-9_-]
      Bash(`rm -rf ~/.claude/teams/${teamName}/ ~/.claude/tasks/${teamName}/ 2>/dev/null`)

      // Post-removal verification: detect if cleaning happened or if dir persists
      if (exists(`~/.claude/teams/${teamName}/`)) {
        warn(`ARC-6: rm -rf failed for ${teamName} — directory still exists`)
      }
    }

  } catch (e) {
    // Top-level guard: defensive infrastructure must NEVER halt the pipeline.
    warn(`ARC-6: prePhaseCleanup failed (${e.message}) — proceeding anyway`)
  }
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

### Stale Arc Team Scan

CDX-7 Layer 3: Scan for orphaned arc-specific teams from prior sessions. Runs after checkpoint init (where `id` is available) for both new and resumed arcs. Only targets `arc-forge-*` and `arc-plan-review-*` prefixes — phase 5-8 teams use `rune-*` prefixes and are handled by the sub-command's own pre-create guard.

```javascript
// CC-5: Placed after checkpoint init — id is available here
// CC-3: Use find instead of ls -d (SEC-007 compliance)
// SECURITY-CRITICAL: ARC_TEAM_PREFIXES must remain hardcoded string literals.
// These values are interpolated into shell `find -name` commands (line 395).
// If externalized to config (e.g., talisman.yml), shell metacharacter injection becomes possible.
const ARC_TEAM_PREFIXES = ["arc-forge-", "arc-plan-review-"]

for (const prefix of ARC_TEAM_PREFIXES) {
  const dirs = Bash(`find ~/.claude/teams -maxdepth 1 -type d -name "${prefix}*" 2>/dev/null`).split('\n').filter(Boolean)
  for (const dir of dirs) {
    const teamName = basename(dir)

    // SEC-003: Validate team name before any filesystem operations
    if (!/^[a-zA-Z0-9_-]+$/.test(teamName)) continue
    // Defense-in-depth: redundant with regex above, per safeTeamCleanup() contract
    if (teamName.includes('..')) continue

    // Don't clean our own team (current arc session)
    // BACK-002 FIX: Use exact prefix+id match instead of fragile substring includes()
    if (teamName === `${prefix}${id}`) continue

    // This team is from a different arc session — orphaned
    warn(`CDX-7: Stale arc team from prior session: ${teamName} — cleaning`)
    Bash(`rm -rf ~/.claude/teams/${teamName}/ ~/.claude/tasks/${teamName}/ 2>/dev/null`)
  }
}
```

## --resume Logic

On resume, validate checkpoint integrity before proceeding:

```
1. Find most recent checkpoint: find .claude/arc -maxdepth 2 -name checkpoint.json -print0 2>/dev/null | xargs -0 ls -t 2>/dev/null | head -1
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
   b. Extract git_sha from plan frontmatter (use optional chaining: `extractYamlFrontmatter(planContent)?.git_sha` — returns null on parse error if plan was manually edited between sessions)
   c. If frontmatter extraction returns null, skip freshness re-check (plan may be malformed — log warning)
   d. If plan's git_sha differs from checkpoint.freshness?.git_sha, re-run freshness check
   e. If previous status was STALE-OVERRIDE, skip re-asking (preserve override decision)
   f. Store updated freshnessResult in checkpoint
4. Validate phase ordering using PHASE_ORDER array (by name, not phase_sequence numbers):
   a. For each "completed" phase, verify no later phase has an earlier timestamp
   b. Normalize "timeout" status to "failed" (both are resumable)
5. For each phase marked "completed":
   a. Verify artifact file exists at recorded path
   b. Compute SHA-256 of artifact, compare against stored artifact_hash
   c. If hash mismatch → demote phase to "pending" + warn user
6. ### Orphan Cleanup (ORCH-1)
   CDX-7 Layer 1: Clean orphaned teams and stale state files from a prior crashed attempt.
   Runs BEFORE resume dispatch. Resets orphaned phase statuses so phases re-execute cleanly.
   Distinct from ARC-6 (step 8) which only cleans team dirs without status reset.

   ```javascript
   const ORPHAN_STALE_THRESHOLD = 1_800_000  // 30 min — crash recovery staleness

   // Clear SDK leadership state before filesystem cleanup
   // Same rationale as prePhaseCleanup — TeamDelete must run while dirs exist
   // See team-lifecycle-guard.md "Team Completion Verification" section.
   try { TeamDelete() } catch (e) { warn(`ORCH-1: TeamDelete() pre-cleanup: ${e.message}`) }

   for (const [phaseName, phaseInfo] of Object.entries(checkpoint.phases)) {
     if (FORBIDDEN_PHASE_KEYS.has(phaseName)) continue
     if (typeof phaseInfo !== 'object' || phaseInfo === null) continue

     // Skip phases without recorded team_name
     if (!phaseInfo.team_name || typeof phaseInfo.team_name !== 'string') continue

     // SEC-003: Validate team name before any filesystem operations
     if (!/^[a-zA-Z0-9_-]+$/.test(phaseInfo.team_name)) {
       warn(`ORCH-1: Invalid team name for phase ${phaseName}: "${phaseInfo.team_name}" — skipping`)
       continue
     }
     // Defense-in-depth: redundant with regex above, per safeTeamCleanup() contract
     if (phaseInfo.team_name.includes('..')) continue

     if (["completed", "skipped", "cancelled"].includes(phaseInfo.status)) {
       // Defensive: verify team is actually gone — clean if not
       Bash(`rm -rf ~/.claude/teams/${phaseInfo.team_name}/ ~/.claude/tasks/${phaseInfo.team_name}/ 2>/dev/null`)
       continue
     }

     // Phase is "in_progress" or "failed" — team may be orphaned from prior crash
     Bash(`rm -rf ~/.claude/teams/${phaseInfo.team_name}/ ~/.claude/tasks/${phaseInfo.team_name}/ 2>/dev/null`)

     // Clear team_name so phase re-creates a fresh team on retry
     phaseInfo.team_name = null
     phaseInfo.status = "pending"
   }

   // Clean stale state files from crashed sub-commands (CC-4: includes forge)
   // See team-lifecycle-guard.md §Stale State File Scan Contract for canonical type list and threshold
   for (const type of ["work", "review", "mend", "audit", "forge"]) {
     const stateFiles = Glob(`tmp/.rune-${type}-*.json`)
     for (const f of stateFiles) {
       try {
         const state = JSON.parse(Read(f))
         // NaN guard: missing/malformed started → treat as stale (conservative toward cleanup)
         const age = Date.now() - new Date(state.started).getTime()
         if (state.status === "active" && (Number.isNaN(age) || age > ORPHAN_STALE_THRESHOLD)) {
           warn(`ORCH-1: Stale ${type} state file: ${f} — marking crash_recovered`)
           state.status = "completed"
           state.completed = new Date().toISOString()
           state.crash_recovered = true
           Write(f, JSON.stringify(state))
         }
       } catch (e) {
         warn(`ORCH-1: Unreadable state file ${f} — skipping`)
       }
     }
   }

   Write(checkpointPath, checkpoint)  // Save cleaned checkpoint
   ```

7. Resume from first incomplete/failed/pending phase in PHASE_ORDER
8. ARC-6: Clean stale teams from prior session before resuming.
   Unlike CDX-7 Layer 1 (which resets phase status), this only cleans teams
   without changing phase status — the phase dispatching logic handles retries.
   `prePhaseCleanup(checkpoint)`
```

Hash mismatch warning:
```
WARNING: Artifact for Phase 2 (plan-review.md) has been modified since checkpoint.
Hash expected: sha256:abc123...
Hash found: sha256:xyz789...
Demoting Phase 2 to "pending" — will re-run plan review.
```

## Phase 1: FORGE (skippable with --no-forge)

See [arc-phase-forge.md](references/arc-phase-forge.md) for the full algorithm.

**Team**: Delegated to `/rune:forge` — forge manages its own team lifecycle (`rune-forge-{id}`)
**Output**: `tmp/arc/{id}/enriched-plan.md`
**Failure**: Timeout → proceed with original plan copy + warn user. Offer `--no-forge` on retry.

// ARC-6: Clean stale teams before delegating to sub-command
prePhaseCleanup(checkpoint)

Read and execute the arc-phase-forge.md algorithm. Update checkpoint on completion.

## Phase 2: PLAN REVIEW (circuit breaker)

See [arc-phase-plan-review.md](references/arc-phase-plan-review.md) for the full algorithm.

**Team**: `arc-plan-review-{id}` — follows ATE-1 pattern
**Output**: `tmp/arc/{id}/plan-review.md`
**Failure**: BLOCK verdict halts pipeline. User fixes plan, then `/rune:arc --resume`.

// ARC-6: Clean stale teams before creating Phase 2 team
// Previously skipped ("orchestrator-managed phase") but leadership state from Phase 1's
// team must be cleared before Phase 2's TeamCreate. See #42 gap analysis.
prePhaseCleanup(checkpoint)

Read and execute the arc-phase-plan-review.md algorithm. Update checkpoint on completion.

## Phase 2.5: PLAN REFINEMENT (conditional)

See [arc-phase-plan-refine.md](references/arc-phase-plan-refine.md) for the full algorithm.

**Team**: None (orchestrator-only)
**Output**: `tmp/arc/{id}/concern-context.md` (or skipped if no CONCERNs)
**Failure**: Non-blocking — proceed with unrefined plan + deferred concerns as context.

Read and execute the arc-phase-plan-refine.md algorithm. Update checkpoint on completion.

## Phase 2.7: VERIFICATION GATE (deterministic)

Zero-LLM-cost deterministic checks on the enriched plan. Orchestrator-only — no team, no agents. Runs 8 checks + report: file references, heading links, acceptance criteria, TODO/FIXME markers, talisman verification patterns, pseudocode contract headers, undocumented security pattern declarations, and post-forge freshness re-check.

**Inputs**: enrichedPlanPath (string), talisman config
**Outputs**: `tmp/arc/{id}/verification-report.md`
**Error handling**: Non-blocking — proceed with warnings. Log issues but do not halt.

See [verification-gate.md](references/verification-gate.md) for the full algorithm.

## Phase 5: WORK

See [arc-phase-work.md](references/arc-phase-work.md) for the full algorithm.

**Team**: `arc-work-{id}` — follows ATE-1 pattern
**Output**: Implemented code (committed) + `tmp/arc/{id}/work-summary.md`
**Failure**: Halt if <50% tasks complete. Partial work is committed via incremental commits.

// ARC-6: Clean stale teams before delegating to sub-command
prePhaseCleanup(checkpoint)

Read and execute the arc-phase-work.md algorithm. Update checkpoint on completion.

## Phase 5.5: IMPLEMENTATION GAP ANALYSIS

Deterministic, orchestrator-only check that cross-references plan acceptance criteria against committed code changes. Zero LLM cost. Includes doc-consistency cross-checks (STEP 4.5), plan section coverage (STEP 4.7), and evaluator quality metrics (STEP 4.8).

**Inputs**: enriched plan, work summary, git diff
**Outputs**: `tmp/arc/{id}/gap-analysis.md`
**Error handling**: Non-blocking (WARN). Gap analysis is advisory — missing criteria are flagged but do not halt the pipeline. Evaluator quality metrics (docstring coverage, function length, evaluation tests) are informational for Phase 6 reviewers.

See [gap-analysis.md](references/gap-analysis.md) for the full algorithm.

## Phase 6: CODE REVIEW

See [arc-phase-code-review.md](references/arc-phase-code-review.md) for the full algorithm.

**Team**: `arc-review-{id}` — follows ATE-1 pattern
**Output**: `tmp/arc/{id}/tome.md`
**Failure**: Does not halt — produces findings or a clean report.

// ARC-6: Clean stale teams before delegating to sub-command
prePhaseCleanup(checkpoint)

Read and execute the arc-phase-code-review.md algorithm. Update checkpoint on completion.

## Phase 7: MEND

See [arc-phase-mend.md](references/arc-phase-mend.md) for the full algorithm.

**Team**: `arc-mend-{id}` — follows ATE-1 pattern
**Output**: `tmp/arc/{id}/resolution-report.md`
**Failure**: Halt if >3 FAILED findings remain. User manually fixes, runs `/rune:arc --resume`.

// ARC-6: Clean stale teams before delegating to sub-command
prePhaseCleanup(checkpoint)

Read and execute the arc-phase-mend.md algorithm. Update checkpoint on completion.

## Phase 7.5: VERIFY MEND (convergence gate)

Lightweight orchestrator-only check that detects regressions introduced by mend fixes. Compares finding counts, runs a targeted spot-check on modified files, and decides whether to retry mend or proceed to audit.

**Inputs**: resolution report, TOME, committed files
**Outputs**: `tmp/arc/{id}/spot-check-round-{N}.md` (or mini-TOME on retry: `tmp/arc/{id}/tome-round-{N}.md`)
**Error handling**: Non-blocking — halting proceeds to audit with warning. The convergence gate either retries or gives up gracefully.

See [verify-mend.md](references/verify-mend.md) for the full algorithm.

## Phase 8: AUDIT (informational)

See [arc-phase-audit.md](references/arc-phase-audit.md) for the full algorithm.

**Team**: `arc-audit-{id}` — follows ATE-1 pattern
**Output**: `tmp/arc/{id}/audit-report.md`
**Failure**: Does not halt — informational final gate.

// ARC-6: Clean stale teams before delegating to sub-command
prePhaseCleanup(checkpoint)

Read and execute the arc-phase-audit.md algorithm. Update checkpoint on completion.

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
  // CDX-009 FIX: totalDuration is in milliseconds (Date.now() - arcStart), so divide by 60_000 for minutes.
  const totalDuration = Date.now() - arcStart  // milliseconds
  const metrics = {
    plan: checkpoint.plan_file,
    duration_minutes: Math.round(totalDuration / 60_000),
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

## Post-Arc Plan Completion Stamp

See [arc-phase-completion-stamp.md](references/arc-phase-completion-stamp.md) for the full algorithm.

Read and execute the arc-phase-completion-stamp.md algorithm. Appends a persistent completion record to the plan file with phase results, convergence history, and overall status. Runs after echo persist, before the final "Done" output.

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
| Total pipeline timeout (120 min) | Halt, preserve checkpoint, suggest `--resume` |
| Phase 2.5 timeout (>3 min) | Proceed with partial concern extraction |
| Phase 2.7 timeout (>30 sec) | Skip verification, log warning, proceed to WORK |
| Plan freshness STALE | AskUserQuestion with Re-plan/Override/Abort | User re-plans or overrides |
| Schema v1/v2/v3/v4 checkpoint on --resume | Auto-migrate to v5 |
| Verify mend spot-check timeout (>4 min) | Skip convergence check, proceed to audit with warning |
| Spot-check agent produces no output | Default to "halted" (fail-closed) |
| Findings diverging after mend | Halt convergence immediately, proceed to audit |
| Convergence circuit breaker (max 2 retries) | Stop retrying, proceed to audit with remaining findings |
