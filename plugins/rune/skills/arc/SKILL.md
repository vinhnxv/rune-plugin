---
name: arc
description: |
  Use when you want to go from plan to merged PR in one command, when running
  the full development pipeline (forge + work + review + mend + ship + merge),
  or when resuming a previously interrupted pipeline. 20-phase automated pipeline
  with checkpoint resume, convergence loops, cross-model verification, Goldmask risk analysis, audit-mend convergence, and auto gap remediation.

  <example>
  user: "/rune:arc plans/feat-user-auth-plan.md"
  assistant: "The Tarnished begins the arc — 20 phases of forge, review, goldmask, test, mend, audit-mend, convergence, ship, and merge..."
  </example>

  <example>
  user: "/rune:arc --resume"
  assistant: "Resuming arc from Phase 5 (WORK) — validating checkpoint integrity..."
  </example>
user-invocable: true
disable-model-invocation: false
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

Chains twenty phases into a single automated pipeline: forge, plan review, plan refinement, verification, semantic verification, work, gap analysis, codex gap analysis, gap remediation, goldmask verification, code review, goldmask correlation, mend, verify mend (convergence controller), test, audit, audit-mend, audit-verify, ship (PR creation), and merge (rebase + auto-merge). Each phase summons its own team with fresh context (except orchestrator-only phases 2.5, 2.7, 9, and 9.5). Phase 5.5 is hybrid: deterministic STEP A + Inspector Ashes STEP B. Phase 7.5 is the convergence controller — it delegates full re-review cycles via dispatcher loop-back. Artifact-based handoff connects phases. Checkpoint state enables resume after failure. Config resolution uses 3 layers: hardcoded defaults → talisman.yml → inline CLI flags.

**Load skills**: `roundtable-circle`, `context-weaving`, `rune-echoes`, `rune-orchestration`, `elicitation`, `codex-cli`, `testing`, `agent-browser`, `polling-guard`, `zsh-compat`

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

**WHY:** Without Agent Teams, agent outputs consume the orchestrator's context window (~200k). With 18 phases spawning agents, the orchestrator hits context limit after 2 phases. Agent Teams give each teammate its own 200k window. The orchestrator only reads artifact files.

**ENFORCEMENT:** The `enforce-teams.sh` PreToolUse hook blocks bare Task calls when a Rune workflow is active. If your Task call is blocked, add `team_name` to it.

## Usage

```
/rune:arc <plan_file.md>              # Full pipeline
/rune:arc <plan_file.md> --no-forge   # Skip research enrichment
/rune:arc <plan_file.md> --approve    # Require human approval for work tasks
/rune:arc --resume                    # Resume from last checkpoint
/rune:arc --resume --no-forge         # Resume, skipping forge on retry
/rune:arc <plan_file.md> --skip-freshness   # Skip freshness validation
/rune:arc <plan_file.md> --confirm          # Pause on all-CONCERN escalation
/rune:arc <plan_file.md> --no-pr           # Skip PR creation (Phase 9)
/rune:arc <plan_file.md> --no-merge        # Skip auto-merge (Phase 9.5)
/rune:arc <plan_file.md> --draft           # Create PR as draft
```

## Flags

| Flag | Description | Default |
|------|-------------|---------|
| `--no-forge` | Skip Phase 1 (research enrichment), use plan as-is | Off |
| `--approve` | Require human approval for each work task (Phase 5 only) | Off |
| `--resume` | Resume from last checkpoint. Plan path auto-detected from checkpoint | Off |
| `--skip-freshness` | Skip plan freshness check (bypass stale-plan detection) | Off |
| `--confirm` | Pause for user input when all plan reviewers raise CONCERN verdicts (Phase 2.5). Without this flag, auto-proceeds with warnings | Off |
| `--no-pr` | Skip Phase 9 (PR creation). Overrides `arc.ship.auto_pr` from talisman | Off |
| `--no-merge` | Skip Phase 9.5 (auto merge). Overrides `arc.ship.auto_merge` from talisman | Off |
| `--no-test` | Skip Phase 7.7 (testing). Skips unit, integration, and E2E test tiers | Off |
| `--draft` | Create PR as draft. Overrides `arc.ship.draft` from talisman | Off |

> **Note**: Worktree mode for `/rune:strive` (Phase 5) is activated via `work.worktree.enabled: true` in talisman.yml, not via a `--worktree` flag on arc. Arc delegates Phase 5 to `/rune:strive`, which reads the talisman setting directly.

## Pipeline Overview

```
Phase 1:   FORGE → Research-enrich plan sections
    ↓ (enriched-plan.md)
Phase 2:   PLAN REVIEW → 3 parallel reviewers + circuit breaker
    ↓ (plan-review.md) — HALT on BLOCK
Phase 2.5: PLAN REFINEMENT → Extract CONCERNs, write concern context (conditional)
    ↓ (concern-context.md) — WARN on all-CONCERN (auto-proceed; --confirm to pause)
Phase 2.7: VERIFICATION GATE → Deterministic plan checks (zero LLM)
    ↓ (verification-report.md)
Phase 2.8: SEMANTIC VERIFICATION → Codex cross-model contradiction detection (v1.39.0)
    ↓ (codex-semantic-verification.md)
Phase 5:   WORK → Swarm implementation + incremental commits
    ↓ (work-summary.md + committed code)
Phase 5.5: GAP ANALYSIS → Check plan criteria vs committed code (deterministic + LLM)
    ↓ (gap-analysis.md) — WARN only, never halts
Phase 5.6: CODEX GAP ANALYSIS → Cross-model plan vs implementation check (v1.39.0)
    ↓ (codex-gap-analysis.md) — WARN only, never halts
Phase 5.8: GAP REMEDIATION → Auto-fix FIXABLE findings from Inspector Ashes VERDICT (v1.51.0)
    ↓ (gap-remediation-report.md) — conditional (needs_remediation flag); WARN only, never halts
Phase 5.7: GOLDMASK VERIFICATION → Blast-radius analysis via investigation agents (v1.47.0)
    ↓ (goldmask-verification.md) — 5 impact tracers + wisdom sage + lore analyst
Phase 6:   CODE REVIEW → Roundtable Circle review
    ↓ (tome.md)
Phase 6.5: GOLDMASK CORRELATION → Synthesize investigation findings into GOLDMASK.md (v1.47.0)
    ↓ (GOLDMASK.md) — orchestrator-only
Phase 7:   MEND → Parallel finding resolution
    ↓ (resolution-report.md) — HALT on >3 FAILED
Phase 7.5: VERIFY MEND → Convergence controller (adaptive review-mend loop)
    ↓ converged → proceed | retry → loop to Phase 6+7 (tier-based max cycles) | halted → warn + proceed
Phase 7.7: TEST → 3-tier QA gate: unit → integration → E2E/browser (v1.43.0)
    ↓ (test-report.md) — WARN only, never halts. Feeds into audit context.
Phase 8:   AUDIT → Final quality gate (informational)
    ↓ (audit-report.md)
Phase 8.5: AUDIT MEND → Fix P1/P2 audit findings (mend-fixer teammates)
    ↓ (audit-mend-report.md)
Phase 8.7: AUDIT VERIFY → Re-audit to confirm fixes (single-pass, max 2 cycles)
    ↓ converged → proceed | retry → loop to Phase 8.5 | halted → warn + proceed
Phase 9:   SHIP → Push branch + create PR (orchestrator-only)
    ↓ (pr-body.md + checkpoint.pr_url)
Phase 9.5: MERGE → Rebase + conflict check + auto-merge (orchestrator-only)
    ↓ (merge-report.md)
Post-arc: PLAN STAMP → Append completion record to plan file (runs FIRST — context-safe)
Post-arc: ECHO PERSIST → Save arc metrics to echoes
Post-arc: COMPLETION REPORT → Display summary to user
Output: Implemented, reviewed, fixed, shipped, and merged feature
```

**Phase numbering note**: Phase numbers (1, 2, 2.5, 2.7, 2.8, 5, 5.5, 5.6, 5.8, 5.7, 6, 6.5, 7, 7.5, 7.7, 8, 8.5, 8.7, 9, 9.5) match the legacy pipeline phases from devise.md and appraise.md for cross-command consistency. Phases 3 and 4 are reserved. Phase 5.8 (GAP REMEDIATION) runs between 5.6 (Codex Gap) and 5.7 (Goldmask) — the non-sequential numbering preserves backward compatibility with older checkpoints. The `PHASE_ORDER` array uses names (not numbers) for validation logic.

## Arc Orchestrator Design (ARC-1)

The arc orchestrator is a **lightweight dispatcher**, not a monolithic agent. Each phase summons a **new team with fresh context** (except Phases 2.5, 2.7, and 5.5 which are orchestrator-only). Phase 7.5 is the convergence controller — it evaluates mend results and may reset Phase 6+7 to trigger re-review cycles. Phase artifacts serve as the handoff mechanism.

Dispatcher loop:
```
1. Read/create checkpoint state
2. Determine current phase (first incomplete in PHASE_ORDER)
3. Invoke phase (delegates to existing commands with their own teams)
   - Phase timing (start/duration) is recorded automatically around invocation
4. Read phase output artifact (SUMMARY HEADER ONLY — Glyph Budget)
5. Update checkpoint state + artifact hash
6. Check total pipeline timeout
7. Proceed to next phase or halt on failure
```

The dispatcher reads only structured summary headers from artifacts, not full content. Full artifacts are passed by file path to the next phase.

**Phase invocation model**: Each phase algorithm is a function invoked by the dispatcher. Phase reference files use `return` for early exits — this exits the phase function, and the dispatcher proceeds to the next phase in `PHASE_ORDER`.

### Phase Constants

```javascript
const PHASE_ORDER = ['forge', 'plan_review', 'plan_refine', 'verification', 'semantic_verification', 'work', 'gap_analysis', 'codex_gap_analysis', 'gap_remediation', 'goldmask_verification', 'code_review', 'goldmask_correlation', 'mend', 'verify_mend', 'test', 'audit', 'audit_mend', 'audit_verify', 'ship', 'merge']

// IMPORTANT: checkArcTimeout() runs BETWEEN phases, not during. A phase that exceeds
// its budget will only be detected after it finishes/times out internally.
// NOTE: SETUP_BUDGET (5 min, all delegated phases) and MEND_EXTRA_BUDGET (3 min, mend-only)
// are defined in arc-phase-mend.md.

// Talisman-aware phase timeouts (v1.40.0+): talisman overrides → hardcoded defaults
// CFG-DECREE-002: Clamp each talisman timeout to sane range (10s - 1hr)
const talismanTimeouts = talisman?.arc?.timeouts ?? {}
for (const [key, val] of Object.entries(talismanTimeouts)) {
  if (typeof val === 'number') {
    talismanTimeouts[key] = Math.max(10_000, Math.min(val, 3_600_000))
  }
}

const PHASE_TIMEOUTS = {
  forge:         talismanTimeouts.forge ?? 900_000,    // 15 min (inner 10m + 5m setup)
  plan_review:   talismanTimeouts.plan_review ?? 900_000,    // 15 min (inner 10m + 5m setup)
  plan_refine:   talismanTimeouts.plan_refine ?? 180_000,    //  3 min (orchestrator-only, no team)
  verification:  talismanTimeouts.verification ?? 30_000,    // 30 sec (orchestrator-only, no team)
  semantic_verification: talismanTimeouts.semantic_verification ?? 180_000,  //  3 min (orchestrator-only, inline codex exec — Architecture Rule #1 lightweight inline exception)
  work:          talismanTimeouts.work ?? 2_100_000,    // 35 min (inner 30m + 5m setup)
  gap_analysis:  talismanTimeouts.gap_analysis ?? 720_000,   // 12 min (inner 8m + 2m setup + 2m aggregate — hybrid: deterministic + Inspector Ashes)
  codex_gap_analysis: talismanTimeouts.codex_gap_analysis ?? 660_000,  // 11 min (orchestrator-only, codex teammate — Architecture Rule #1 lightweight inline exception)
  gap_remediation: talismanTimeouts.gap_remediation ?? 900_000,  // 15 min (inner 10m + 5m setup — spawns gap-fixer Ash)
  code_review:   talismanTimeouts.code_review ?? 900_000,    // 15 min (inner 10m + 5m setup)
  mend:          talismanTimeouts.mend ?? 1_380_000,    // 23 min (inner 15m + 5m setup + 3m ward/cross-file)
  verify_mend:   talismanTimeouts.verify_mend ?? 240_000,    //  4 min (orchestrator-only, no team)
  test:          talismanTimeouts.test ?? 900_000,        // 15 min without E2E (inner 10m + 5m setup). Dynamic: 40 min with E2E (2_400_000)
  goldmask_verification: talismanTimeouts.goldmask_verification ?? 900_000,  // 15 min (inner 10m + 5m setup)
  goldmask_correlation:  talismanTimeouts.goldmask_correlation ?? 60_000,    //  1 min (orchestrator-only, no team)
  audit:         talismanTimeouts.audit ?? 1_200_000,    // 20 min (inner 15m + 5m setup)
  audit_mend:    talismanTimeouts.audit_mend ?? 1_380_000,  // 23 min (inner 15m + 8m setup)
  audit_verify:  talismanTimeouts.audit_verify ?? 240_000,  //  4 min (orchestrator-only)
  ship:          talismanTimeouts.ship ?? 300_000,      //  5 min (orchestrator-only, push + PR creation)
  merge:         talismanTimeouts.merge ?? 600_000,     // 10 min (orchestrator-only, rebase + merge + CI wait)
}
// Tier-based dynamic timeout — replaces fixed ARC_TOTAL_TIMEOUT.
// See review-mend-convergence.md for tier selection logic.
// DOC-002 FIX: Base budget sum is ~202.5 min (v1.58.0 audit_mend/verify + v1.51.0 gap_remediation + v1.47.0 goldmask + v1.43.0 test):
//   forge(15) + plan_review(15) + plan_refine(3) + verification(0.5) + semantic_verification(3) +
//   codex_gap_analysis(11) + gap_remediation(15) + goldmask_verification(15) + work(35) + gap_analysis(12) +
//   goldmask_correlation(1) + test(15) + audit(20) + audit_mend(23) + audit_verify(4) + ship(5) + merge(10) = 202.5 min
// With E2E: test grows to 40 min → 227.5 min base
// LIGHT (2 cycles):    202.5 + 42 + 1×26 = 270.5 min → hard cap at 240 min
// STANDARD (3 cycles): 202.5 + 42 + 2×26 = 296.5 min → hard cap at 240 min
// THOROUGH (5 cycles): 202.5 + 42 + 4×26 = 348.5 min → hard cap at 240 min
const ARC_TOTAL_TIMEOUT_DEFAULT = 9_720_000  // 162 min fallback (LIGHT tier minimum — used before tier selection)
const ARC_TOTAL_TIMEOUT_HARD_CAP = 14_400_000  // 240 min (4 hours) — absolute hard cap
const STALE_THRESHOLD = 300_000      // 5 min
const MEND_RETRY_TIMEOUT = 780_000   // 13 min (inner 5m polling + 5m setup + 3m ward/cross-file)

// Convergence cycle budgets for dynamic timeout calculation
const CYCLE_BUDGET = {
  pass_1_review: 900_000,    // 15 min (full Phase 6)
  pass_N_review: 540_000,    //  9 min (60% of full — focused re-review)
  pass_1_mend:   1_380_000,  // 23 min (full Phase 7)
  pass_N_mend:   780_000,    // 13 min (retry mend)
  convergence:   240_000,    //  4 min (Phase 7.5 evaluation)
}

function calculateDynamicTimeout(tier) {
  const basePhaseBudget = PHASE_TIMEOUTS.forge + PHASE_TIMEOUTS.plan_review +
    PHASE_TIMEOUTS.plan_refine + PHASE_TIMEOUTS.verification +
    PHASE_TIMEOUTS.semantic_verification + PHASE_TIMEOUTS.codex_gap_analysis +
    PHASE_TIMEOUTS.gap_remediation +             // v1.51.0: +gap_remediation (15 min)
    PHASE_TIMEOUTS.goldmask_verification + PHASE_TIMEOUTS.goldmask_correlation +
    PHASE_TIMEOUTS.work + PHASE_TIMEOUTS.gap_analysis +
    PHASE_TIMEOUTS.test +                        // v1.43.0: +test (15 min default, 40 min with E2E)
    PHASE_TIMEOUTS.audit +
    PHASE_TIMEOUTS.audit_mend + PHASE_TIMEOUTS.audit_verify +  // v1.58.0: +audit_mend (23 min) + audit_verify (4 min)
    PHASE_TIMEOUTS.ship + PHASE_TIMEOUTS.merge  // ~202.5 min (v1.58.0: +audit_mend/verify + v1.51.0: +gap_remediation + v1.47.0: +goldmask + v1.43.0: +test)
  const cycle1Budget = CYCLE_BUDGET.pass_1_review + CYCLE_BUDGET.pass_1_mend + CYCLE_BUDGET.convergence  // ~42 min
  const cycleNBudget = CYCLE_BUDGET.pass_N_review + CYCLE_BUDGET.pass_N_mend + CYCLE_BUDGET.convergence  // ~26 min
  const maxCycles = tier?.maxCycles ?? 3
  const dynamicTimeout = basePhaseBudget + cycle1Budget + (maxCycles - 1) * cycleNBudget
  return Math.min(dynamicTimeout, ARC_TOTAL_TIMEOUT_HARD_CAP)
}

// Shared prototype pollution guard — used by prePhaseCleanup (ARC-6) and ORCH-1 resume cleanup.
// BACK-005 FIX: Single definition replaces two duplicate inline Sets.
const FORBIDDEN_PHASE_KEYS = new Set(['__proto__', 'constructor', 'prototype'])
```

See [phase-tool-matrix.md](references/phase-tool-matrix.md) for per-phase tool restrictions and time budget details.

## Pre-flight

See [arc-preflight.md](references/arc-preflight.md) for the full pre-flight sequence.

**Inputs**: plan path, git branch state, team registry
**Outputs**: feature branch (if on main), validated plan, clean team state
**Error handling**: abort on validation failure

Read and execute the arc-preflight.md algorithm at dispatcher init.

### Plan Freshness Check (FRESH-1)

See [freshness-gate.md](references/freshness-gate.md) for the full algorithm (5 weighted signals, composite score, STALE/WARN/PASS decision).

**Summary**: Zero-LLM-cost structural drift detection. Produces `freshnessResult` object stored in checkpoint + `tmp/arc/{id}/freshness-report.md`. Plans without `git_sha` skip the check (backward compat). STALE plans prompt user: re-plan, override, or abort.

Read and execute the algorithm from [freshness-gate.md](references/freshness-gate.md). Store `freshnessResult` for checkpoint initialization below.

### Total Pipeline Timeout Check

**Limitation**: `checkArcTimeout()` runs **between phases**, not during a phase. If a phase is stuck internally, arc cannot interrupt it. A phase that exceeds its budget will only be detected after it finishes or times out on its own inner timeout. This is why inner polling timeouts must be derived from outer phase budgets (minus setup overhead) — the inner timeout is the real enforcement mechanism.

```javascript
const arcStart = Date.now()

function checkArcTimeout() {
  const elapsed = Date.now() - arcStart
  const effectiveTimeout = checkpoint?.convergence?.tier
    ? calculateDynamicTimeout(checkpoint.convergence.tier)
    : ARC_TOTAL_TIMEOUT_DEFAULT
  if (elapsed > effectiveTimeout) {
    error(`Arc pipeline exceeded ${Math.round(effectiveTimeout / 60_000)}-minute total timeout (elapsed: ${Math.round(elapsed/60000)}min).`)
    updateCheckpoint({ status: "timeout" })
    return true
  }
  return false
}
```

### Inter-Phase Cleanup Guard (ARC-6)

See [arc-preflight.md](references/arc-preflight.md) for the full `prePhaseCleanup()` definition.

Runs before every delegated phase. 4-strategy cleanup: TeamDelete with backoff → checkpoint-aware rm-rf → post-cleanup TeamDelete → SDK leadership nuclear reset. Idempotent — harmless no-op when no stale team exists.

// DISPATCHER INIT: Read arc-preflight.md to load prePhaseCleanup() into context
Read(references/arc-preflight.md)

### Initialize Checkpoint (ARC-2)

See [arc-checkpoint-init.md](references/arc-checkpoint-init.md) for the full initialization.

**Inputs**: plan path, talisman config, arc arguments, `freshnessResult` from Freshness Check above
**Outputs**: checkpoint object (schema v12), resolved arc config
**Error handling**: fail arc if plan file missing or config invalid

// NOTE: Requires `freshnessResult` from the Freshness Check step (inline above).
// The Freshness Check produces freshnessResult which is consumed by checkpoint init
// (checkpoint.freshness = freshnessResult). This cross-stub dependency is by design.
Read and execute the arc-checkpoint-init.md algorithm.

### Stale Arc Team Scan

See [arc-preflight.md](references/arc-preflight.md) for the stale team scan algorithm.

CDX-7 Layer 3: Scan for orphaned arc-specific teams (arc-*, rune-*, goldmask-* prefixes) from prior sessions. Runs after checkpoint init. Validates team names, excludes current session and in-progress teams, cleans orphans.

## Resume (`--resume`)

See [arc-resume.md](references/arc-resume.md) for the full resume algorithm.

**Inputs**: `--resume` flag, checkpoint file path
**Outputs**: restored checkpoint with validated artifacts
**Error handling**: fall back to fresh start if checkpoint corrupted

// Only loaded when --resume flag is passed
if (args.includes("--resume")) {
  // CRITICAL: Resume skips pre-flight, but phase stubs still call prePhaseCleanup().
  // Load arc-preflight.md here so prePhaseCleanup is in context for resumed phases.
  Read(references/arc-preflight.md)
  Read and execute the arc-resume.md algorithm.
}

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

## Phase 2.8: SEMANTIC VERIFICATION (Codex cross-model, v1.39.0)

See [arc-codex-phases.md](references/arc-codex-phases.md) § Phase 2.8 for the full algorithm.

**Team**: `null` (orchestrator-only) | **Output**: `tmp/arc/${id}/codex-semantic-verification.md`
**Failure**: warn and continue — non-blocking phase

Read and execute the arc-codex-phases.md § Phase 2.8 algorithm. Update checkpoint on completion.

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

<!-- v1.57.0: Phase 5.5 STEP A.9 enhancement planned — CLI-backed Ashes can contribute
     to gap analysis by running detectAllCLIAshes() and including their findings
     in the gap-analysis-verdict.md. This extends the existing Inspector Ashes STEP B
     to include external model perspectives alongside the deterministic STEP A checks. -->

## Phase 5.6: CODEX GAP ANALYSIS (Codex cross-model, v1.39.0)

See [arc-codex-phases.md](references/arc-codex-phases.md) § Phase 5.6 for the full algorithm.

**Team**: `arc-gap-{id}` | **Output**: `tmp/arc/{id}/codex-gap-analysis.md`
**Failure**: warn and continue — gap analysis is advisory

<!-- v1.57.0: Phase 5.6 batched claim enhancement planned — when CLI-backed Ashes
     are configured, their gap findings can be batched with Codex gap findings
     into a unified cross-model gap report. CDX-DRIFT is an internal finding ID
     for semantic drift detection, not a custom Ash prefix. -->

// ARC-6: Clean stale teams before phase
prePhaseCleanup(checkpoint)

Read and execute the arc-codex-phases.md § Phase 5.6 algorithm. Update checkpoint on completion.

## Phase 5.8: GAP REMEDIATION (conditional, v1.51.0)

<!-- SO-P2-001: Cross-phase checkpoint contract.
     Gate: reads `needs_remediation` from gap_analysis phase checkpoint (written by Phase 5.5 STEP D).
     Phase 5.5 STEP D writes: updateCheckpoint({ needs_remediation: true/false, fixable_count, ... })
     Phase 5.8 reads: checkpoint.needs_remediation === true → proceed, else skip. -->

Auto-fixes FIXABLE findings from the Phase 5.5 Inspector Ashes VERDICT before proceeding to Goldmask Verification. Only runs when Phase 5.5 STEP D sets `needs_remediation: true` in checkpoint AND `arc.gap_analysis.remediation.enabled` is not false in talisman.

**Team**: `arc-gap-fix-{id}` — follows ATE-1 pattern
**Inputs**: `tmp/arc/{id}/gap-analysis-verdict.md` (from Phase 5.5 STEP B), checkpoint `needs_remediation` flag
**Output**: `tmp/arc/{id}/gap-remediation-report.md`
**Failure**: Non-blocking. Skips cleanly if gate fails. Times out → proceeds with partial fixes.

```javascript
// ARC-6: Clean stale teams before creating gap-fix team
prePhaseCleanup(checkpoint)

updateCheckpoint({ phase: "gap_remediation", status: "in_progress", phase_sequence: 5.8, team_name: null })
```

See [gap-remediation.md](references/gap-remediation.md) for the full algorithm. Update checkpoint on completion.

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
**Output**: Round 0: `tmp/arc/{id}/resolution-report.md`, Round N: `tmp/arc/{id}/resolution-report-round-{N}.md`
**Failure**: Halt if >3 FAILED findings remain. User manually fixes, runs `/rune:arc --resume`.

// ARC-6: Clean stale teams before delegating to sub-command
prePhaseCleanup(checkpoint)

Read and execute the arc-phase-mend.md algorithm. Update checkpoint on completion.

## Phase 7.5: VERIFY MEND (review-mend convergence controller)

Adaptive convergence controller that evaluates mend results and decides whether to loop back for another full review-mend cycle (Phase 6→7→7.5) or proceed to audit. Replaces the previous single-pass spot-check with a tier-based multi-cycle loop.

**Team**: None for convergence evaluation. Delegates full re-review via dispatcher loop-back (resets Phase 6+7 to "pending").
**Inputs**: Resolution report (round-aware path), TOME, checkpoint convergence state, talisman config
**Outputs**: Updated checkpoint with convergence verdict. On retry: `review-focus-round-{N}.json` for progressive scope.
**Error handling**: Non-blocking — halting proceeds to audit with warning. The convergence controller either retries or gives up gracefully.

See [verify-mend.md](references/verify-mend.md) for the full algorithm.
See [review-mend-convergence.md](../roundtable-circle/references/review-mend-convergence.md) for shared tier selection and convergence evaluation logic.

## Phase 7.7: TEST (diff-scoped test execution)

See [arc-phase-test.md](references/arc-phase-test.md) for the full algorithm.

**Team**: `arc-test-{id}` — follows ATE-1 pattern
**Output**: `tmp/arc/{id}/test-report.md`
**Failure**: Non-blocking WARN only. Test failures do NOT halt the pipeline — they are recorded in the test report and surfaced in the AUDIT phase. The pipeline proceeds to Phase 8.
**Skip**: `--no-test` flag or `testing.enabled: false` in talisman.

// ARC-6: Clean stale teams before delegating to sub-command
prePhaseCleanup(checkpoint)

```javascript
// Skip gate
if (flags.no_test || talisman?.testing?.enabled === false) {
  checkpoint.phases.test.status = "skipped"
  checkpoint.phases.test.artifact = null
  // Proceed to Phase 8
} else {
  // Read and execute the arc-phase-test.md algorithm
  // Update checkpoint on completion with tiers_run, pass_rate, coverage_pct, has_frontend
}
```

## Phase 8: AUDIT (informational)

See [arc-phase-audit.md](references/arc-phase-audit.md) for the full algorithm.

**Team**: `arc-audit-{id}` — follows ATE-1 pattern
**Output**: `tmp/arc/{id}/audit-report.md`
**Failure**: Does not halt — informational final gate.

// ARC-6: Clean stale teams before delegating to sub-command
prePhaseCleanup(checkpoint)

Read and execute the arc-phase-audit.md algorithm. Update checkpoint on completion.

## Phase 9: SHIP (PR Creation)

See [arc-phase-ship.md](references/arc-phase-ship.md) for the full algorithm.

**Team**: None (orchestrator-only)
**Output**: `tmp/arc/{id}/pr-body.md`
**Failure**: Skip PR creation, proceed to completion report. User creates PR manually.

// ARC-6: prePhaseCleanup not needed (orchestrator-only, no team)
// SEC-DECREE-003: Set GH_PROMPT_DISABLED=1 before all `gh` commands to prevent interactive prompts in automation.

Read and execute the arc-phase-ship.md algorithm. Update checkpoint on completion.

## Phase 9.5: MERGE (Rebase + Auto Merge)

See [arc-phase-merge.md](references/arc-phase-merge.md) for the full algorithm.

**Team**: None (orchestrator-only)
**Output**: `tmp/arc/{id}/merge-report.md`
**Failure**: Skip merge, PR remains open. User merges manually.

// ARC-6: prePhaseCleanup not needed (orchestrator-only, no team)
// SEC-DECREE-003: Set GH_PROMPT_DISABLED=1 before all `gh` commands to prevent interactive prompts in automation.

Read and execute the arc-phase-merge.md algorithm. Update checkpoint on completion.

## Phase Transition Contracts (ARC-3)

| From | To | Artifact | Contract |
|------|----|----------|----------|
| FORGE | PLAN REVIEW | `enriched-plan.md` | Markdown plan with enriched sections |
| PLAN REVIEW | PLAN REFINEMENT | `plan-review.md` | 3 reviewer verdicts (PASS/CONCERN/BLOCK) |
| PLAN REFINEMENT | VERIFICATION | `concern-context.md` | Extracted concern list. Plan not modified |
| VERIFICATION | SEMANTIC VERIFICATION | `verification-report.md` | Deterministic check results (PASS/WARN) |
| SEMANTIC VERIFICATION | WORK | `codex-semantic-verification.md` | Codex contradiction findings (or skip) |
| WORK | GAP ANALYSIS | Working tree + `work-summary.md` | Git diff of committed changes + task summary |
| GAP ANALYSIS | CODEX GAP ANALYSIS | `gap-analysis.md` | Criteria coverage (ADDRESSED/MISSING/PARTIAL) |
| CODEX GAP ANALYSIS | GAP REMEDIATION | `codex-gap-analysis.md` | Cross-model gap findings + `needs_remediation` checkpoint flag from Phase 5.5 STEP D |
| GAP REMEDIATION | GOLDMASK VERIFICATION | `gap-remediation-report.md` | Fixed findings list + deferred list. Skips cleanly if gate fails |
| CODE REVIEW | MEND | `tome.md` | TOME with `<!-- RUNE:FINDING ... -->` markers |
| MEND | VERIFY MEND | `resolution-report.md` | Fixed/FP/Failed finding list |
| VERIFY MEND | MEND (retry) | `review-focus-round-{N}.json` | Phase 6+7 reset to pending, progressive focus scope |
| VERIFY MEND | TEST | `resolution-report.md` + checkpoint convergence | Convergence verdict (converged/halted) |
| TEST | AUDIT | `test-report.md` | Test results with pass_rate, coverage_pct, tiers_run (or skipped) |
| AUDIT | SHIP | `audit-report.md` | Audit complete, quality gates passed |
| SHIP | MERGE | `pr-body.md` + `checkpoint.pr_url` | PR created, URL stored |
| MERGE | Done | `merge-report.md` | Merged or auto-merge enabled. Pipeline summary to user |

## Failure Policy (ARC-5)

| Phase | On Failure | Recovery |
|-------|-----------|----------|
| FORGE | Proceed with original plan copy + warn. Offer `--no-forge` on retry | `/rune:arc --resume --no-forge` |
| PLAN REVIEW | Halt if any BLOCK verdict | User fixes plan, `/rune:arc --resume` |
| PLAN REFINEMENT | Non-blocking — proceed with deferred concerns | Advisory phase |
| VERIFICATION | Non-blocking — proceed with warnings | Informational |
| SEMANTIC VERIFICATION | Non-blocking — Codex timeout/unavailable → skip, proceed | Informational (v1.39.0) |
| WORK | Halt if <50% tasks complete. Partial commits preserved | `/rune:arc --resume` |
| GAP ANALYSIS | Non-blocking — WARN only | Advisory context for code review |
| CODEX GAP ANALYSIS | Non-blocking — Codex timeout/unavailable → skip, proceed | Advisory (v1.39.0) |
| GAP REMEDIATION | Non-blocking — gate miss (needs_remediation=false or talisman disabled) → skip cleanly. Fixer timeout → partial fixes, proceed | Advisory (v1.51.0) |
| CODE REVIEW | Does not halt | Produces findings or clean report |
| MEND | Halt if >3 FAILED findings | User fixes, `/rune:arc --resume` |
| VERIFY MEND | Non-blocking — retries up to tier max cycles (LIGHT: 2, STANDARD: 3, THOROUGH: 5), then proceeds | Convergence gate is advisory |
| TEST | Non-blocking WARN only. Test failures recorded in report, surfaced in AUDIT | `--no-test` to skip entirely |
| AUDIT | Does not halt — informational | User reviews audit report |
| SHIP | Skip PR creation, proceed to completion report. Branch was pushed | User creates PR manually: `gh pr create` |
| MERGE | Skip merge, PR remains open. Rebase conflicts → warn with resolution steps | User merges manually: `gh pr merge --squash` |

## Post-Arc Plan Completion Stamp

> **IMPORTANT — Execution order**: This step runs FIRST after Phase 9.5 MERGE completes (or Phase 8 AUDIT
> if ship/merge are skipped), before echo persist and the verbose completion report. The plan stamp writes
> a persistent completion record to the plan file — it MUST execute before context-heavy steps (echo persist,
> completion report) that risk triggering context compaction. If compaction occurs, the stamp is already safely written.

See [arc-phase-completion-stamp.md](references/arc-phase-completion-stamp.md) for the full algorithm.

Read and execute the arc-phase-completion-stamp.md algorithm. Appends a persistent completion record to the plan file with phase results, convergence history, and overall status.

### Post-Arc Echo Persist

See [post-arc.md](references/post-arc.md) for the echo persist algorithm.

Persists arc quality metrics (phases completed, findings, convergence cycles, gap coverage, duration) to `.claude/echoes/planner/MEMORY.md` as inscribed-layer echo entry.

## Completion Report

See [post-arc.md](references/post-arc.md) for the full completion report template.

Displays "The Tarnished has claimed the Elden Throne" with per-phase status, convergence summary, commit count, and next steps.

## Post-Arc Final Sweep (ARC-9)

See [post-arc.md](references/post-arc.md) for the full ARC-9 sweep algorithm.

Catches zombie teammates from the last delegated phase. Uses 3-strategy cleanup: shutdown discovery → TeamDelete with backoff → filesystem fallback.

## Error Handling

| Error | Recovery |
|-------|----------|
| Concurrent arc session active | Abort with warning, suggest `/rune:cancel-arc` |
| Plan file not found | Suggest `/rune:devise` first |
| Checkpoint corrupted | Warn user, offer fresh start or manual fix |
| Artifact hash mismatch on resume | Demote phase to pending, re-run |
| Phase timeout | Halt, preserve checkpoint, suggest `--resume` |
| BLOCK verdict in plan review | Halt, report blocker details |
| All-CONCERN escalation (3x CONCERN) | Auto-proceed with warning (use `--confirm` to pause) |
| <50% work tasks complete | Halt, partial commits preserved |
| >3 FAILED mend findings | Halt, resolution report available |
| Worker crash mid-phase | Phase team cleanup, checkpoint preserved |
| Branch conflict | Warn user, suggest manual resolution |
| Total pipeline timeout (dynamic: 162-240 min based on tier) | Halt, preserve checkpoint, suggest `--resume` |
| Phase 2.5 timeout (>3 min) | Proceed with partial concern extraction |
| Phase 2.7 timeout (>30 sec) | Skip verification, log warning, proceed to WORK |
| Plan freshness STALE | AskUserQuestion with Re-plan/Override/Abort | User re-plans or overrides |
| Schema v1-v8 checkpoint on --resume | Auto-migrate to v9 (adds goldmask + test phases) |
| Concurrent /rune:* command | Warn user (advisory) | No lock — user responsibility |
| Convergence evaluation timeout (>4 min) | Skip convergence check, proceed to audit with warning |
| TOME missing or malformed after re-review | Default to "halted" (fail-closed) |
| Findings diverging after mend | Halt convergence immediately, proceed to audit |
| Convergence circuit breaker (tier max cycles) | Stop retrying, proceed to audit with remaining findings |
| Ship phase: gh CLI not available | Skip PR creation, proceed to completion report |
| Ship phase: Push failed | Skip PR creation, warn with manual push command |
| Ship phase: PR creation failed | Branch pushed, warn user to create PR manually |
| Merge phase: Rebase conflicts | Abort rebase, warn with manual resolution steps |
| Merge phase: Pre-merge checklist CRITICAL | Abort merge, write merge-report.md |
| Merge phase: Merge failed | PR remains open, warn user to merge manually |
| Test phase: No test framework detected | Skip all tiers, produce empty report with WARN |
| Test phase: Service startup failed | Skip integration/E2E tiers, unit tests still run |
| Test phase: E2E browser agent timeout | Record timeout per-route, produce partial report |
| Test phase: All tiers failed | Non-blocking — report recorded, pipeline continues to AUDIT |
| Zombie teammates after arc completion (ARC-9) | Final sweep sends shutdown_request + TeamDelete. Fallback: `/rune:cancel-arc` |
