---
name: rune:arc
description: |
  End-to-end orchestration pipeline. Chains forge, plan review, work, code review,
  mend, and audit into a single automated pipeline with checkpoint-based resume,
  per-phase teams, circuit breakers, and artifact-based handoff.

  <example>
  user: "/rune:arc plans/feat-user-auth-plan.md"
  assistant: "The Tarnished begins the arc — 6 phases of forge, review, and mend..."
  </example>

  <example>
  user: "/rune:arc --resume"
  assistant: "Resuming arc from Phase 3 (WORK) — validating checkpoint integrity..."
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

Chains six phases into a single automated pipeline: forge, plan review, work, code review, mend, and audit. Each phase summons its own team with fresh context. Artifact-based handoff connects phases. Checkpoint state enables resume after failure.

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
| `--approve` | Require human approval for each work task (Phase 3 only) | Off |
| `--resume` | Resume from last checkpoint, validating artifact integrity. Plan path is auto-detected from checkpoint (no argument required). | Off |

## Pipeline Overview

```
Phase 1: FORGE → Research-enrich plan sections
    ↓ (enriched-plan.md)
Phase 2: PLAN REVIEW → 3 parallel reviewers + circuit breaker
    ↓ (plan-review.md) — HALT on BLOCK
Phase 3: WORK → Swarm implementation + incremental commits
    ↓ (work-summary.md + committed code)
Phase 4: CODE REVIEW → Roundtable Circle review
    ↓ (tome.md)
Phase 5: MEND → Parallel finding resolution
    ↓ (resolution-report.md) — HALT on >3 FAILED
Phase 6: AUDIT → Final quality gate (informational)
    ↓ (audit-report.md)
Output: Implemented, reviewed, and fixed feature
```

## Arc Orchestrator Design (ARC-1)

The arc orchestrator is a **lightweight dispatcher**, NOT a monolithic agent. Each phase summons a **new team with fresh context**. Phase artifacts serve as the handoff mechanism.

Dispatcher loop:
```
1. Read/create checkpoint state
2. Determine current phase (first incomplete)
3. Invoke phase (delegates to existing commands with their own teams)
4. Read phase output artifact (SUMMARY HEADER ONLY — Glyph Budget)
5. Update checkpoint state + artifact hash
6. Proceed to next phase or halt on failure
```

The dispatcher reads only structured summary headers from artifacts, NOT full content. Full artifacts are passed by file path to the next phase.

## Pre-flight

### Branch Strategy (COMMIT-1)

Before Phase 3 (WORK), create a feature branch if on main:

```bash
current_branch=$(git branch --show-current)
if [ "$current_branch" = "main" ] || [ "$current_branch" = "master" ]; then
  # Extract plan name from filename
  plan_name=$(basename "$plan_file" .md | sed 's/[^a-zA-Z0-9]/-/g')
  plan_name=${plan_name:-unnamed}
  branch_name="rune/arc-${plan_name}-$(date +%Y%m%d)"
  git checkout -b -- "$branch_name"
fi
```

If already on a feature branch, use the current branch.

### Concurrent Arc Prevention

```bash
# Check for active arc sessions
active=$(ls .claude/arc/*/checkpoint.json 2>/dev/null | while read f; do
  jq -r 'select(.phases | to_entries | map(.value.status) | any(. == "in_progress")) | .id' "$f" 2>/dev/null
done)

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

### Initialize Checkpoint (ARC-2)

```javascript
const id = `arc-${Date.now()}`
if (!/^arc-[a-zA-Z0-9_-]+$/.test(id)) throw new Error("Invalid arc identifier")
const sessionNonce = crypto.randomBytes(6).toString('hex')

Write(`.claude/arc/${id}/checkpoint.json`, {
  id: id,
  plan_file: planFile,
  flags: { approve: approveFlag, no_forge: noForgeFlag },
  session_nonce: sessionNonce,
  phase_sequence: 0,
  phases: {
    forge:       { status: noForgeFlag ? "skipped" : "pending", artifact: null, artifact_hash: null, team_name: null },
    plan_review: { status: "pending", artifact: null, artifact_hash: null, team_name: null },
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
3. Validate phase_sequence is monotonically increasing
4. For each phase marked "completed":
   a. Verify artifact file exists at recorded path
   b. Compute SHA-256 of artifact, compare against stored artifact_hash
   c. If hash mismatch → demote phase to "pending" + warn user
5. If enriched-plan.md exists AND hash valid → skip Phase 1
6. If plan-review.md exists AND hash valid AND no BLOCK → skip Phase 2
7. If tome.md exists AND hash valid → skip Phases 3-4
8. If resolution-report.md exists AND hash valid → skip Phase 5
9. Resume from first incomplete/demoted phase
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
// id validated at init (line 144): /^arc-[a-zA-Z0-9_-]+$/
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

// Monitor → collect → synthesize
// Synthesize enriched plan → tmp/arc/{id}/enriched-plan.md

// Cleanup with fallback (see team-lifecycle-guard.md)
// id validated at init (line 144): /^arc-[a-zA-Z0-9_-]+$/
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
// id validated at init (line 144): /^arc-[a-zA-Z0-9_-]+$/
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

// Collect verdicts
// Grep for <!-- VERDICT:...:BLOCK --> in reviewer outputs
// Merge → tmp/arc/{id}/plan-review.md

// Cleanup with fallback (see team-lifecycle-guard.md)
// id validated at init (line 144): /^arc-[a-zA-Z0-9_-]+$/
try { TeamDelete() } catch (e) {
  Bash(`rm -rf ~/.claude/teams/arc-plan-review-${id}/ ~/.claude/tasks/arc-plan-review-${id}/ 2>/dev/null`)
}
```

**CIRCUIT BREAKER**: Parse `<!-- VERDICT:{reviewer}:{verdict} -->` markers from each reviewer output.

| Condition | Action |
|-----------|--------|
| ANY reviewer returns BLOCK | HALT pipeline, report blocking reviewer + reason |
| All PASS (with optional CONCERNs) | Proceed to Phase 3 |

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

## Phase 3: WORK

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
// Capture team_name from work command for cancel-arc discovery
const workTeamName = /* team name created by /rune:work logic */
updateCheckpoint({ phase: "work", status: "in_progress", phase_sequence: 3, team_name: workTeamName })

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
  phase_sequence: 3,
  commits: commitSHAs
})
```

**Output**: Implemented code (committed) + `tmp/arc/{id}/work-summary.md`

**Failure policy**: Halt if <50% tasks complete. Partial work is committed via incremental commits (E5).

**--approve routing**: Routes to human user via AskUserQuestion (not to AI leader). Applies only to Phase 3, NOT Phase 5. The arc orchestrator MUST NOT propagate `--approve` when invoking `/rune:mend` logic in Phase 5 — mend fixers apply deterministic fixes from TOME findings and do not require human approval per fix.

## Phase 4: CODE REVIEW

Invoke `/rune:review` logic on the implemented changes. Summons Ash with Roundtable Circle lifecycle.

**Team**: `arc-review-{id}`
**Tools (read-only)**: Read, Glob, Grep, Write (own output file only)
**Team lifecycle**: Delegated to `/rune:review` — the review command manages its own TeamCreate/TeamDelete with guards (see team-lifecycle-guard.md).

```javascript
// Invoke /rune:review logic
// Scope: changes since arc branch creation (or since Phase 3 start)
// TOME session nonce: use arc session_nonce for marker integrity
// Capture team_name from review command for cancel-arc discovery
const reviewTeamName = /* team name created by /rune:review logic */
updateCheckpoint({ phase: "code_review", status: "in_progress", phase_sequence: 4, team_name: reviewTeamName })

// Move TOME to arc directory
// Copy/move from tmp/reviews/{review-id}/TOME.md → tmp/arc/{id}/tome.md

updateCheckpoint({
  phase: "code_review",
  status: "completed",
  artifact: `tmp/arc/${id}/tome.md`,
  artifact_hash: sha256(tome),
  phase_sequence: 4
})
```

**Output**: `tmp/arc/{id}/tome.md`

**Docs-only work output**: If Phase 3 produced only documentation files (no code), the review still runs correctly. Rune Gaze's docs-only override ensures Knowledge Keeper is summoned even when all doc files fall below the normal 10-line threshold. Ward Sentinel and Pattern Weaver review docs for security and quality patterns regardless. The TOME will contain `DOC-` and `QUAL-` prefixed findings rather than code-specific ones.

**Failure policy**: Never halts. Review always produces findings or a clean report.

## Phase 5: MEND

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
updateCheckpoint({ phase: "mend", status: "in_progress", phase_sequence: 5, team_name: mendTeamName })

// Check failure threshold
const failedCount = countFindings("FAILED", resolutionReport)

updateCheckpoint({
  phase: "mend",
  status: failedCount > 3 ? "failed" : "completed",
  artifact: `tmp/arc/${id}/resolution-report.md`,
  artifact_hash: sha256(resolutionReport),
  phase_sequence: 5
})
```

**Output**: `tmp/arc/{id}/resolution-report.md`

**Failure policy**: Halt if >3 FAILED findings remain after resolution. User manually fixes, runs `/rune:arc --resume`.

## Phase 6: AUDIT (informational)

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
updateCheckpoint({ phase: "audit", status: "in_progress", phase_sequence: 6, team_name: auditTeamName })

updateCheckpoint({
  phase: "audit",
  status: "completed",
  artifact: `tmp/arc/${id}/audit-report.md`,
  artifact_hash: sha256(auditReport),
  phase_sequence: 6
})
```

**Output**: `tmp/arc/{id}/audit-report.md`

**Failure policy**: Report results. Does NOT halt — informational final gate.

## Phase Transition Contracts (ARC-3)

| From | To | Artifact | Contract |
|------|----|----------|----------|
| FORGE | PLAN REVIEW | `enriched-plan.md` | Markdown plan with enriched sections (same structure as input, more content) |
| PLAN REVIEW | WORK | `plan-review.md` | 3 reviewer verdicts (PASS/CONCERN/BLOCK). If all PASS, enriched plan is input to WORK |
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
| Phase 3 (WORK) | Full access (Read, Write, Edit, Bash, Glob, Grep) | Implementation requires all tools |
| Phase 4 (CODE REVIEW) | Read, Glob, Grep, Write (own output file only) | Review — no codebase modification |
| Phase 5 (MEND) | Orchestrator: full. Fixers: restricted (see mend-fixer) | Least privilege for fixers |
| Phase 6 (AUDIT) | Read, Glob, Grep, Write (own output file only) | Audit — no codebase modification |

All worker and fixer agent prompts MUST include: "NEVER modify files in `.claude/arc/`". Only the arc orchestrator writes to checkpoint.json.

## Failure Policy (ARC-5)

| Phase | On Failure | Recovery |
|-------|-----------|----------|
| FORGE | Halt + report. Non-critical — offer `--no-forge` | `/rune:arc --resume --no-forge` |
| PLAN REVIEW | Halt if ANY BLOCK verdict. Report which reviewer blocked and why | User fixes plan, `/rune:arc --resume` |
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
  1. FORGE:       {status} — enriched-plan.md
  2. PLAN REVIEW: {status} — plan-review.md ({verdict})
  3. WORK:        {status} — {tasks_completed}/{tasks_total} tasks
  4. CODE REVIEW: {status} — tome.md ({finding_count} findings)
  5. MEND:        {status} — {fixed}/{total} findings resolved
  6. AUDIT:       {status} — audit-report.md

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
| <50% work tasks complete | Halt, partial commits preserved |
| >3 FAILED mend findings | Halt, resolution report available |
| Worker crash mid-phase | Phase team cleanup, checkpoint preserved |
| Branch conflict | Warn user, suggest manual resolution |
