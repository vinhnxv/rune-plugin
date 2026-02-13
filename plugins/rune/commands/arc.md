---
name: rune:arc
description: |
  End-to-end orchestration pipeline. Chains forge, plan review, plan refinement,
  verification, work, code review, mend, and audit into a single automated pipeline
  with checkpoint-based resume, per-phase teams, circuit breakers, and artifact-based handoff.

  <example>
  user: "/rune:arc plans/feat-user-auth-plan.md"
  assistant: "The Tarnished begins the arc — 8 phases of forge, review, and mend..."
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

Chains eight phases into a single automated pipeline: forge, plan review, plan refinement, verification, work, code review, mend, and audit. Each phase summons its own team with fresh context (except orchestrator-only phases 2.5 and 2.7). Artifact-based handoff connects phases. Checkpoint state enables resume after failure.

**Load skills**: `roundtable-circle`, `context-weaving`, `rune-echoes`, `rune-orchestration`

## Usage

```
/rune:arc <plan_file.md>                              # Full pipeline
/rune:arc <plan_file.md> --no-forge                 # Skip research enrichment
/rune:arc <plan_file.md> --approve                    # Require human approval for work tasks
/rune:arc --resume                                     # Resume from last checkpoint (plan path auto-detected from checkpoint)
/rune:arc --resume --no-forge                        # Resume, skipping forge on retry
```

## Flags

| Flag | Description | Default |
|------|-------------|---------|
| `--no-forge` | Skip Phase 1 (research enrichment), use plan as-is | Off |
| `--approve` | Require human approval for each work task (Phase 5 only) | Off |
| `--resume` | Resume from last checkpoint, validating artifact integrity. Plan path is auto-detected from checkpoint (no argument required). | Off |

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
Phase 6:   CODE REVIEW → Roundtable Circle review
    ↓ (tome.md)
Phase 7:   MEND → Parallel finding resolution
    ↓ (resolution-report.md) — HALT on >3 FAILED
Phase 8:   AUDIT → Final quality gate (informational)
    ↓ (audit-report.md)
Output: Implemented, reviewed, and fixed feature
```

## Arc Orchestrator Design (ARC-1)

The arc orchestrator is a **lightweight dispatcher**, NOT a monolithic agent. Each phase summons a **new team with fresh context** (except Phases 2.5 and 2.7 which are orchestrator-only). Phase artifacts serve as the handoff mechanism.

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

The dispatcher reads only structured summary headers from artifacts, NOT full content. Full artifacts are passed by file path to the next phase.

### Phase Constants

```javascript
// Canonical phase ordering — used for resume validation, display, and sequence derivation.
// phase_sequence is display-only — NEVER use it for validation logic.
const PHASE_ORDER = ['forge', 'plan_review', 'plan_refine', 'verification', 'work', 'code_review', 'mend', 'audit']

// Phase timeout constants (milliseconds)
// Delegated phases use inner-timeout + 60s buffer. This ensures the delegated
// command handles its own timeout first; the arc timeout is a safety net only.
const PHASE_TIMEOUTS = {
  forge:         600_000,    // 10 min — 5 parallel research agents
  plan_review:   600_000,    // 10 min — 3 parallel reviewers
  plan_refine:   180_000,    //  3 min — orchestrator-only, no agents
  verification:   30_000,    // 30 sec — deterministic checks, no LLM
  work:        1_860_000,    // 31 min — work own timeout (30m) + 60s buffer
  code_review:   660_000,    // 11 min — review own timeout (10m) + 60s buffer
  mend:          960_000,    // 16 min — mend own timeout (15m) + 60s buffer
  audit:         960_000,    // 16 min — audit own timeout (15m) + 60s buffer
}
const ARC_TOTAL_TIMEOUT = 5_400_000  // 90 min — entire pipeline hard ceiling
const STALE_THRESHOLD = 300_000      // 5 min — no progress from any agent
```

## Pre-flight

### Branch Strategy (COMMIT-1)

Before Phase 5 (WORK), create a feature branch if on main:

```bash
current_branch=$(git branch --show-current)
if [ "$current_branch" = "main" ] || [ "$current_branch" = "master" ]; then
  # Extract plan name from filename
  plan_name=$(basename "$plan_file" .md | sed 's/[^a-zA-Z0-9]/-/g')
  plan_name=${plan_name:-unnamed}
  branch_name="rune/arc-${plan_name}-$(date +%Y%m%d-%H%M%S)"
  git checkout -b -- "$branch_name"
fi
```

If already on a feature branch, use the current branch.

### Concurrent Arc Prevention

```bash
# Check for active arc sessions (with jq fallback)
if command -v jq >/dev/null 2>&1; then
  active=$(ls .claude/arc/*/checkpoint.json 2>/dev/null | while read f; do
    jq -r 'select(.phases | to_entries | map(.value.status) | any(. == "in_progress")) | .id' "$f" 2>/dev/null
  done)
else
  # Fallback: grep for in_progress status when jq is unavailable
  active=$(ls .claude/arc/*/checkpoint.json 2>/dev/null | while read f; do
    # grep fallback: less precise than jq, matches status fields
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
// Validate plan path: prevent shell injection in Bash calls
if (!/^[a-zA-Z0-9._\/-]+$/.test(planFile)) {
  error(`Invalid plan path: ${planFile}. Path must contain only alphanumeric, dot, slash, hyphen, and underscore characters.`)
  return
}
```

### Total Pipeline Timeout Check

```javascript
// Track total pipeline elapsed time — checked before each phase transition
const arcStart = Date.now()

function checkArcTimeout() {
  const elapsed = Date.now() - arcStart
  if (elapsed > ARC_TOTAL_TIMEOUT) {
    error(`Arc pipeline exceeded total timeout of 90 minutes (elapsed: ${Math.round(elapsed/60000)}min).`)
    updateCheckpoint({ status: "timeout" })
    return true  // signal to halt
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
  id: id,
  schema_version: 2,
  plan_file: planFile,
  flags: { approve: approveFlag, no_forge: noForgeFlag },
  session_nonce: sessionNonce,
  phase_sequence: 0,
  phases: {
    forge:       { status: noForgeFlag ? "skipped" : "pending", artifact: null, artifact_hash: null, team_name: null },
    plan_review: { status: "pending", artifact: null, artifact_hash: null, team_name: null },
    plan_refine: { status: "pending", artifact: null, artifact_hash: null, team_name: null },
    verification:{ status: "pending", artifact: null, artifact_hash: null, team_name: null },
    work:        { status: "pending", artifact: null, artifact_hash: null, team_name: null },
    code_review: { status: "pending", artifact: null, artifact_hash: null, team_name: null },
    mend:        { status: "pending", artifact: null, artifact_hash: null, team_name: null },
    audit:       { status: "pending", artifact: null, artifact_hash: null, team_name: null }
  },
  commits: [],
  started_at: new Date().toISOString(),
  updated_at: new Date().toISOString()
})
```

## --resume Logic

On resume, validate checkpoint integrity before proceeding:

```
1. Find most recent checkpoint: ls -t .claude/arc/*/checkpoint.json | head -1
   (or use explicit plan path argument to match checkpoint by plan_file field)
2. Read .claude/arc/{id}/checkpoint.json — extract plan_file for downstream phases
3. Schema migration: if schema_version < 2 (or missing), migrate v1 → v2:
   a. Add plan_refine: { status: "skipped", artifact: null, artifact_hash: null, team_name: null }
   b. Add verification: { status: "skipped", artifact: null, artifact_hash: null, team_name: null }
   c. Set schema_version: 2
   d. Write migrated checkpoint back
4. Validate phase ordering using PHASE_ORDER array (by name, NOT phase_sequence numbers):
   a. For each "completed" phase, verify no later phase in PHASE_ORDER is "completed" with an earlier timestamp
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

Summon research agents to enrich the plan with current best practices, framework docs, codebase patterns, git history, and past echoes.

**Team**: `arc-forge-{id}`
**Tools (read-only)**: Read, Glob, Grep, Write (own output file only)

```javascript
// Update checkpoint
updateCheckpoint({ phase: "forge", status: "in_progress", phase_sequence: 1, team_name: `arc-forge-${id}` })

// Pre-create guard: cleanup stale team if exists (see team-lifecycle-guard.md)
// id validated at init: /^arc-[a-zA-Z0-9_-]+$/
try { TeamDelete() } catch (e) {
  Bash(`rm -rf ~/.claude/teams/arc-forge-${id}/ ~/.claude/tasks/arc-forge-${id}/ 2>/dev/null`)
}
TeamCreate({ team_name: `arc-forge-${id}` })

// Summon 5 research agents in parallel
const agents = [
  { name: "practice-seeker", task: "External best practices for: {plan_sections}" },
  { name: "lore-scholar", task: "Framework documentation relevant to: {plan_sections}" },
  { name: "repo-surveyor", task: "Codebase patterns relevant to: {plan_sections}" },
  { name: "git-miner", task: "Git history context for: {plan_sections}" },
  { name: "echo-reader", task: "Past learnings from Rune Echoes relevant to: {plan_sections}" }
]

for (const agent of agents) {
  Task({
    team_name: `arc-forge-${id}`,
    name: agent.name,
    subagent_type: "general-purpose",
    prompt: `${agent.task}\n\nWrite findings to tmp/arc/${id}/research/${agent.name}.md`,
    run_in_background: true
  })
}

// Monitor with timeout
const forgeStart = Date.now()
while (true) {
  tasks = TaskList()

  // 1. Check completion FIRST (prevents timeout race)
  if (tasks.every(t => t.status === "completed")) break

  // 2. Then check timeout
  if (Date.now() - forgeStart > PHASE_TIMEOUTS.forge) {
    warn("Phase 1 (FORGE) timed out. Proceeding with partial research.")
    break
  }

  // 3. Stale detection
  for (const task of tasks.filter(t => t.status === "in_progress")) {
    if (task.stale > STALE_THRESHOLD) {
      warn(`Research agent ${task.owner || task.id} may be stalled (${Math.round(task.stale/60000)}min)`)
    }
  }

  sleep(30_000)  // 30 second polling interval
}
// Final sweep: re-read TaskList for last-interval completions
tasks = TaskList()

// Synthesize enriched plan → tmp/arc/{id}/enriched-plan.md

// Cleanup with fallback (see team-lifecycle-guard.md)
// id validated at init: /^arc-[a-zA-Z0-9_-]+$/
try { TeamDelete() } catch (e) {
  Bash(`rm -rf ~/.claude/teams/arc-forge-${id}/ ~/.claude/tasks/arc-forge-${id}/ 2>/dev/null`)
}
updateCheckpoint({
  phase: "forge",
  status: "completed",
  artifact: `tmp/arc/${id}/enriched-plan.md`,
  artifact_hash: sha256(enrichedPlan),
  phase_sequence: 1
})
```

**Output**: `tmp/arc/{id}/enriched-plan.md`

If research times out: proceed with original plan + warn user. Offer `--no-forge` on retry.

## Phase 2: PLAN REVIEW (circuit breaker)

Three parallel reviewers evaluate the enriched plan. ANY BLOCK verdict halts the pipeline.

**Team**: `arc-plan-review-{id}`
**Tools (read-only)**: Read, Glob, Grep, Write (own output file only)

```javascript
updateCheckpoint({ phase: "plan_review", status: "in_progress", phase_sequence: 2, team_name: `arc-plan-review-${id}` })

// Pre-create guard: cleanup stale team if exists (see team-lifecycle-guard.md)
// id validated at init: /^arc-[a-zA-Z0-9_-]+$/
try { TeamDelete() } catch (e) {
  Bash(`rm -rf ~/.claude/teams/arc-plan-review-${id}/ ~/.claude/tasks/arc-plan-review-${id}/ 2>/dev/null`)
}
TeamCreate({ team_name: `arc-plan-review-${id}` })

// Summon 3 reviewers in parallel
const reviewers = [
  { name: "scroll-reviewer", agent: "agents/utility/scroll-reviewer.md", focus: "Document quality" },
  { name: "decree-arbiter", agent: "agents/utility/decree-arbiter.md", focus: "Technical soundness" },
  { name: "knowledge-keeper", agent: "agents/utility/knowledge-keeper.md", focus: "Documentation coverage" }
]

for (const reviewer of reviewers) {
  Task({
    team_name: `arc-plan-review-${id}`,
    name: reviewer.name,
    subagent_type: "general-purpose",
    prompt: `Review plan for: ${reviewer.focus}
      Plan: tmp/arc/${id}/enriched-plan.md
      Output: tmp/arc/${id}/reviews/${reviewer.name}-verdict.md
      Include structured verdict marker: <!-- VERDICT:${reviewer.name}:{PASS|CONCERN|BLOCK} -->`,
    run_in_background: true
  })
}

// Monitor with timeout
const reviewStart = Date.now()
while (true) {
  tasks = TaskList()

  // 1. Check completion FIRST (prevents timeout race)
  if (tasks.every(t => t.status === "completed")) break

  // 2. Then check timeout
  if (Date.now() - reviewStart > PHASE_TIMEOUTS.plan_review) {
    warn("Phase 2 (PLAN REVIEW) timed out.")
    // Handle missing verdicts: double-check output files before defaulting
    for (const reviewer of reviewers) {
      if (!reviewer.completed) {
        const outputPath = `tmp/arc/${id}/reviews/${reviewer.name}-verdict.md`
        if (exists(outputPath)) {
          reviewer.verdict = parseVerdict(reviewer.name, Read(outputPath))
        } else {
          warn(`Reviewer ${reviewer.name} produced no output — defaulting to CONCERN.`)
          reviewer.verdict = "CONCERN"
        }
      }
    }
    break
  }

  sleep(30_000)
}
// Final sweep
tasks = TaskList()

// Parse verdicts using anchored regex
const parseVerdict = (reviewer, output) => {
  const pattern = /^<!-- VERDICT:([a-zA-Z_-]+):(PASS|CONCERN|BLOCK) -->$/m
  const match = output.match(pattern)
  if (!match) {
    warn(`Reviewer ${reviewer} output lacks verdict marker — defaulting to CONCERN.`)
    return "CONCERN"
  }
  if (match[1] !== reviewer) {
    warn(`Verdict marker reviewer mismatch: expected ${reviewer}, found ${match[1]}. Using marker verdict.`)
  }
  return match[2]  // PASS | CONCERN | BLOCK
}

// Collect verdicts
// Grep for <!-- VERDICT:...:BLOCK --> in reviewer outputs
// Merge → tmp/arc/{id}/plan-review.md

// Cleanup with fallback (see team-lifecycle-guard.md)
// id validated at init: /^arc-[a-zA-Z0-9_-]+$/
try { TeamDelete() } catch (e) {
  Bash(`rm -rf ~/.claude/teams/arc-plan-review-${id}/ ~/.claude/tasks/arc-plan-review-${id}/ 2>/dev/null`)
}
```

**CIRCUIT BREAKER**: Parse `<!-- VERDICT:{reviewer}:{verdict} -->` markers from each reviewer output.

| Condition | Action |
|-----------|--------|
| ANY reviewer returns BLOCK | HALT pipeline, report blocking reviewer + reason |
| All PASS (with optional CONCERNs) | Proceed to Phase 2.5 |

```
updateCheckpoint({
  phase: "plan_review",
  status: blocked ? "failed" : "completed",
  artifact: `tmp/arc/${id}/plan-review.md`,
  artifact_hash: sha256(planReview),
  phase_sequence: 2
})
```

**Output**: `tmp/arc/{id}/plan-review.md`

If blocked: user fixes plan, then `/rune:arc --resume`.

## Phase 2.5: PLAN REFINEMENT (conditional)

Extract CONCERN details from reviewer outputs and propagate as context to the work phase. This phase is **orchestrator-only** — no team creation, no agents summoned. The Tarnished reads reviewer outputs directly and writes concern context.

**Team**: None (orchestrator-only)
**Tools**: Read, Write, Glob, Grep
**Duration**: Max 3 minutes

**Trigger**: Any CONCERN verdict exists in plan-review.md. If all verdicts are PASS, this phase is skipped.

```javascript
updateCheckpoint({ phase: "plan_refine", status: "in_progress", phase_sequence: 3, team_name: null })

// 1. Extract CONCERNs from reviewer outputs
const concerns = []
for (const reviewer of reviewers) {
  const outputPath = `tmp/arc/${id}/reviews/${reviewer.name}-verdict.md`
  if (!exists(outputPath)) continue
  const output = Read(outputPath)
  const verdict = parseVerdict(reviewer.name, output)
  if (verdict === "CONCERN") {
    // Extract finding details from reviewer markdown
    concerns.push({
      reviewer: reviewer.name,
      verdict: "CONCERN",
      content: output  // Full reviewer output for worker context
    })
  }
}

if (concerns.length === 0) {
  // No concerns — skip refinement
  updateCheckpoint({ phase: "plan_refine", status: "skipped", phase_sequence: 3, team_name: null })
} else {
  // 2. Write concern context for work phase
  // NOTE: Phase 2.5 is extraction-only. It does NOT modify the plan.
  // Auto-fixing plan text is deferred to v1.12.0+.
  const concernContext = concerns.map(c =>
    `## ${c.reviewer} — CONCERN\n\n${c.content}`
  ).join('\n\n---\n\n')

  Write(`tmp/arc/${id}/concern-context.md`, `# Plan Review Concerns\n\n` +
    `Total concerns: ${concerns.length}\n` +
    `Reviewers with concerns: ${concerns.map(c => c.reviewer).join(', ')}\n\n` +
    `Workers should be aware of these concerns and attempt to address them during implementation.\n\n` +
    concernContext)

  // 3. All-CONCERN escalation (3x CONCERN, 0 PASS)
  const allConcern = reviewers.every(r => parseVerdict(r.name, Read(`tmp/arc/${id}/reviews/${r.name}-verdict.md`)) === "CONCERN")
  if (allConcern) {
    const forgeNote = checkpoint.flags.no_forge
      ? "\n\nNote: Forge enrichment was skipped (--no-forge). CONCERNs may be more likely on a raw plan."
      : ""
    AskUserQuestion({
      question: `All 3 reviewers raised concerns (no PASS verdicts).${forgeNote} Proceed to implementation?`,
      header: "Escalate",
      options: [
        { label: "Proceed with warnings", description: "Implementation will include concern context" },
        { label: "Halt and fix manually", description: "Fix plan, then /rune:arc --resume" },
        { label: "Re-run plan review", description: "Revert to Phase 2 with updated plan" }
      ]
    })
    // If user chooses "Re-run plan review": revert plan_review to "pending", resume from Phase 2
    // If user chooses "Halt": set plan_refine to "failed", exit
  }

  // Compute hash from written file (not in-memory)
  const writtenContent = Read(`tmp/arc/${id}/concern-context.md`)
  updateCheckpoint({
    phase: "plan_refine",
    status: "completed",
    artifact: `tmp/arc/${id}/concern-context.md`,
    artifact_hash: sha256(writtenContent),
    phase_sequence: 3,
    team_name: null
  })
}
```

**Output**: `tmp/arc/{id}/concern-context.md` (or skipped if no CONCERNs)

**Failure policy**: Non-blocking — proceed with unrefined plan + deferred concerns as context. Phase 2.5 is advisory.

## Phase 2.7: VERIFICATION GATE (deterministic)

Zero-LLM-cost deterministic checks on the enriched plan. This phase is **orchestrator-only** — no team, no agents.

**Team**: None (orchestrator-only)
**Tools**: Read, Glob, Grep, Write, Bash (for git history check)
**Duration**: Max 30 seconds

```javascript
updateCheckpoint({ phase: "verification", status: "in_progress", phase_sequence: 4, team_name: null })

const issues = []

// 1. Check plan file references exist
const filePaths = extractFileReferences(enrichedPlanPath)
for (const fp of filePaths) {
  if (!exists(fp)) {
    // Use git history to distinguish deleted files vs forward-references
    const gitExists = Bash(`git log --all --oneline -- "${fp}" 2>/dev/null | head -1`)
    const annotation = gitExists.trim()
      ? `[STALE: was deleted — see git history]`
      : `[PENDING: file does not exist yet — may be created during WORK]`
    issues.push(`File reference: ${fp} — ${annotation}`)
  }
}

// 2. Check internal heading links resolve
const headingLinks = extractHeadingLinks(enrichedPlanPath)
const headings = extractHeadings(enrichedPlanPath)
for (const link of headingLinks) {
  if (!headings.includes(link)) issues.push(`Broken heading link: ${link}`)
}

// 3. Check acceptance criteria present
const hasCriteria = Grep("- \\[ \\]", enrichedPlanPath)
if (!hasCriteria) issues.push("No acceptance criteria found (missing '- [ ]' items)")

// 4. Check no TODO/FIXME in plan prose (outside code blocks)
const todos = extractTodosOutsideCodeBlocks(enrichedPlanPath)
if (todos.length > 0) issues.push(`${todos.length} TODO/FIXME markers in plan prose`)

// 5. Run talisman verification_patterns (if configured)
const talisman = readTalisman()
const customPatterns = talisman?.plan?.verification_patterns || []
const SAFE_PATTERN = /^[a-zA-Z0-9._\-\/ *]+$/
for (const pattern of customPatterns) {
  if (!SAFE_PATTERN.test(pattern.regex) ||
      !SAFE_PATTERN.test(pattern.paths) ||
      (pattern.exclusions && !SAFE_PATTERN.test(pattern.exclusions))) {
    warn(`Skipping pattern "${pattern.description}": unsafe characters`)
    continue
  }
  const result = Bash(`rg --no-messages -- "${pattern.regex}" ${pattern.paths} ${pattern.exclusions || ''}`)
  if (pattern.expect_zero && result.matchCount > 0) {
    issues.push(`Stale reference: ${pattern.description}`)
  }
}

// 6. Write verification report
const verificationReport = `# Verification Gate Report\n\n` +
  `Status: ${issues.length === 0 ? "PASS" : "WARN"}\n` +
  `Issues: ${issues.length}\n` +
  `Checked at: ${new Date().toISOString()}\n\n` +
  (issues.length > 0 ? issues.map(i => `- ${i}`).join('\n') : 'All checks passed.')
Write(`tmp/arc/${id}/verification-report.md`, verificationReport)

// Compute hash from written file
const writtenReport = Read(`tmp/arc/${id}/verification-report.md`)
updateCheckpoint({
  phase: "verification",
  status: "completed",
  artifact: `tmp/arc/${id}/verification-report.md`,
  artifact_hash: sha256(writtenReport),
  phase_sequence: 4,
  team_name: null
})
```

**Output**: `tmp/arc/{id}/verification-report.md`

**Failure policy**: Non-blocking — proceed with warnings. Log issues but don't halt. Verification is informational.

## Phase 5: WORK

Invoke `/rune:work` logic on the enriched plan. Swarm workers implement tasks with incremental commits.

**Team**: `arc-work-{id}`
**Tools (full access)**: Read, Write, Edit, Bash, Glob, Grep (all tools needed for implementation)
**Team lifecycle**: Delegated to `/rune:work` — the work command manages its own TeamCreate/TeamDelete with guards (see team-lifecycle-guard.md). The arc orchestrator invokes the work logic; it does NOT create `arc-work-{id}` directly.

```javascript
// Create feature branch if needed (COMMIT-1)
createFeatureBranchIfNeeded()

// Invoke /rune:work logic
// Input: enriched plan (or original if --no-forge)
// If --approve: propagate to work mode (routes to human via AskUserQuestion)
// Incremental commits after each ward-checked task: [ward-checked] prefix
// If concern-context.md exists, include in work team prompt:
const workContext = exists(`tmp/arc/${id}/concern-context.md`)
  ? `\n\n## Reviewer Concerns\nThe following concerns were raised during plan review. Workers should be aware of deferred concerns and attempt to address them during implementation.\nSee tmp/arc/${id}/concern-context.md for full details.`
  : ""

// Capture team_name from work command for cancel-arc discovery
const workTeamName = /* team name created by /rune:work logic */
updateCheckpoint({ phase: "work", status: "in_progress", phase_sequence: 5, team_name: workTeamName })

// After work completes, produce work summary
Write(`tmp/arc/${id}/work-summary.md`, {
  tasks_completed: completedCount,
  tasks_failed: failedCount,
  files_committed: committedFiles,
  uncommitted_changes: uncommittedList,
  commits: commitSHAs
})

// Record commit SHAs in checkpoint
updateCheckpoint({
  phase: "work",
  status: completedRatio >= 0.5 ? "completed" : "failed",
  artifact: `tmp/arc/${id}/work-summary.md`,
  artifact_hash: sha256(workSummary),
  phase_sequence: 5,
  commits: commitSHAs
})
```

**Output**: Implemented code (committed) + `tmp/arc/{id}/work-summary.md`

**Failure policy**: Halt if <50% tasks complete. Partial work is committed via incremental commits (E5).

**--approve routing**: Routes to human user via AskUserQuestion (not to AI leader). Applies only to Phase 5, NOT Phase 7. The arc orchestrator MUST NOT propagate `--approve` when invoking `/rune:mend` logic in Phase 7 — mend fixers apply deterministic fixes from TOME findings and do not require human approval per fix.

## Phase 6: CODE REVIEW

Invoke `/rune:review` logic on the implemented changes. Summons Ash with Roundtable Circle lifecycle.

**Team**: `arc-review-{id}`
**Tools (read-only)**: Read, Glob, Grep, Write (own output file only)
**Team lifecycle**: Delegated to `/rune:review` — the review command manages its own TeamCreate/TeamDelete with guards (see team-lifecycle-guard.md).

```javascript
// Invoke /rune:review logic
// Scope: changes since arc branch creation (or since Phase 5 start)
// TOME session nonce: use arc session_nonce for marker integrity
// Capture team_name from review command for cancel-arc discovery
const reviewTeamName = /* team name created by /rune:review logic */
updateCheckpoint({ phase: "code_review", status: "in_progress", phase_sequence: 6, team_name: reviewTeamName })

// Move TOME to arc directory
// Copy/move from tmp/reviews/{review-id}/TOME.md → tmp/arc/{id}/tome.md

updateCheckpoint({
  phase: "code_review",
  status: "completed",
  artifact: `tmp/arc/${id}/tome.md`,
  artifact_hash: sha256(tome),
  phase_sequence: 6
})
```

**Output**: `tmp/arc/{id}/tome.md`

**Docs-only work output**: If Phase 5 produced only documentation files (no code), the review still runs correctly. Rune Gaze's docs-only override ensures Knowledge Keeper is summoned even when all doc files fall below the normal 10-line threshold. Ward Sentinel and Pattern Weaver review docs for security and quality patterns regardless. The TOME will contain `DOC-` and `QUAL-` prefixed findings rather than code-specific ones.

**Failure policy**: Never halts. Review always produces findings or a clean report.

## Phase 7: MEND

Invoke `/rune:mend` logic on the TOME. Parallel fixers resolve findings.

**Team**: `arc-mend-{id}` (orchestrator team); fixers get restricted tools
**Tools**: Orchestrator full access. Fixers restricted (see mend-fixer agent).
**Team lifecycle**: Delegated to `/rune:mend` — the mend command manages its own TeamCreate/TeamDelete with guards (see team-lifecycle-guard.md).

```javascript
// Invoke /rune:mend logic
// Input: tmp/arc/{id}/tome.md
// Output directory: tmp/arc/{id}/ (resolution-report.md)
// Capture team_name from mend command for cancel-arc discovery
const mendTeamName = /* team name created by /rune:mend logic */
updateCheckpoint({ phase: "mend", status: "in_progress", phase_sequence: 7, team_name: mendTeamName })

// Check failure threshold
const failedCount = countFindings("FAILED", resolutionReport)

updateCheckpoint({
  phase: "mend",
  status: failedCount > 3 ? "failed" : "completed",
  artifact: `tmp/arc/${id}/resolution-report.md`,
  artifact_hash: sha256(resolutionReport),
  phase_sequence: 7
})
```

**Output**: `tmp/arc/{id}/resolution-report.md`

**Failure policy**: Halt if >3 FAILED findings remain after resolution. User manually fixes, runs `/rune:arc --resume`.

## Phase 8: AUDIT (informational)

Invoke `/rune:audit` logic as a final quality gate. This phase is informational and does NOT halt the pipeline.

**Team**: `arc-audit-{id}`
**Tools (read-only)**: Read, Glob, Grep, Write (own output file only)
**Team lifecycle**: Delegated to `/rune:audit` — the audit command manages its own TeamCreate/TeamDelete with guards (see team-lifecycle-guard.md).

```javascript
// Invoke /rune:audit logic
// Full codebase audit
// Output: tmp/arc/{id}/audit-report.md
// Capture team_name from audit command for cancel-arc discovery
const auditTeamName = /* team name created by /rune:audit logic */
updateCheckpoint({ phase: "audit", status: "in_progress", phase_sequence: 8, team_name: auditTeamName })

updateCheckpoint({
  phase: "audit",
  status: "completed",
  artifact: `tmp/arc/${id}/audit-report.md`,
  artifact_hash: sha256(auditReport),
  phase_sequence: 8
})
```

**Output**: `tmp/arc/{id}/audit-report.md`

**Failure policy**: Report results. Does NOT halt — informational final gate.

## Phase Transition Contracts (ARC-3)

| From | To | Artifact | Contract |
|------|----|----------|----------|
| FORGE | PLAN REVIEW | `enriched-plan.md` | Markdown plan with enriched sections (same structure as input, more content) |
| PLAN REVIEW | PLAN REFINEMENT | `plan-review.md` | 3 reviewer verdicts (PASS/CONCERN/BLOCK). CONCERNs extracted for refinement |
| PLAN REFINEMENT | VERIFICATION | `concern-context.md` | Extracted concern list for worker awareness. Plan NOT modified |
| VERIFICATION | WORK | `verification-report.md` | Deterministic check results (PASS/WARN). Enriched plan is input to WORK |
| WORK | CODE REVIEW | Working tree + `work-summary.md` | Git diff of committed changes (incremental commits) + task completion summary |
| CODE REVIEW | MEND | `tome.md` | TOME with structured `<!-- RUNE:FINDING nonce="..." ... -->` markers |
| MEND | AUDIT | `resolution-report.md` | Fixed/FP/Failed finding list. Working tree updated with fixes |
| AUDIT | Done | `audit-report.md` | Final audit report. Pipeline summary to user |

## Per-Phase Tool Restrictions (F8)

The arc orchestrator passes only phase-appropriate tools when creating each phase's team:

| Phase | Tools | Rationale |
|-------|-------|-----------|
| Phase 1 (FORGE) | Read, Glob, Grep, Write (own output file only) | Research — no codebase modification |
| Phase 2 (PLAN REVIEW) | Read, Glob, Grep, Write (own output file only) | Review — no codebase modification |
| Phase 2.5 (PLAN REFINEMENT) | Read, Write, Glob, Grep | Orchestrator-only — extraction, no team |
| Phase 2.7 (VERIFICATION) | Read, Glob, Grep, Write, Bash (git history) | Orchestrator-only — deterministic checks |
| Phase 5 (WORK) | Full access (Read, Write, Edit, Bash, Glob, Grep) | Implementation requires all tools |
| Phase 6 (CODE REVIEW) | Read, Glob, Grep, Write (own output file only) | Review — no codebase modification |
| Phase 7 (MEND) | Orchestrator: full. Fixers: restricted (see mend-fixer) | Least privilege for fixers |
| Phase 8 (AUDIT) | Read, Glob, Grep, Write (own output file only) | Audit — no codebase modification |

All worker and fixer agent prompts MUST include: "NEVER modify files in `.claude/arc/`". Only the arc orchestrator writes to checkpoint.json.

## Failure Policy (ARC-5)

| Phase | On Failure | Recovery |
|-------|-----------|----------|
| FORGE | Halt + report. Non-critical — offer `--no-forge` | `/rune:arc --resume --no-forge` |
| PLAN REVIEW | Halt if ANY BLOCK verdict. Report which reviewer blocked and why | User fixes plan, `/rune:arc --resume` |
| PLAN REFINEMENT | Non-blocking — proceed with unrefined plan + deferred concerns as context | Phase 2.5 is advisory. Workers still get concern-context.md |
| VERIFICATION | Non-blocking — proceed with warnings. Log issues but don't halt | Verification is informational. Issues logged in verification-report.md |
| WORK | Halt if <50% tasks complete. Partial work is committed (incremental) | `/rune:arc --resume` resumes incomplete tasks |
| CODE REVIEW | Never halts (review always produces findings or clean report) | N/A |
| MEND | Halt if >3 FAILED findings remain after resolution | User manually fixes, `/rune:arc --resume` |
| AUDIT | Report results. Does NOT halt — informational final gate | User reviews audit report |

## Completion Report

```
⚔ The Tarnished has claimed the Elden Throne.

Plan: {plan_file}
Checkpoint: .claude/arc/{id}/checkpoint.json
Branch: {branch_name}

Phases:
  1.   FORGE:           {status} — enriched-plan.md
  2.   PLAN REVIEW:     {status} — plan-review.md ({verdict})
  2.5  PLAN REFINEMENT: {status} — {concerns_count} concerns extracted
  2.7  VERIFICATION:    {status} — {issues_count} issues
  5.   WORK:            {status} — {tasks_completed}/{tasks_total} tasks
  6.   CODE REVIEW:     {status} — tome.md ({finding_count} findings)
  7.   MEND:            {status} — {fixed}/{total} findings resolved
  8.   AUDIT:           {status} — audit-report.md

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
| CONCERN classification parse error | Default to full concern text (conservative) |
| Verification pattern validation failure | Skip unsafe pattern with warning, continue other checks |
| Schema v1 checkpoint on --resume | Auto-migrate to v2 (add plan_refine, verification as "skipped") |
