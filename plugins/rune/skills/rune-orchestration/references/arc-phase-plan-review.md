# Phase 2: PLAN REVIEW — Full Algorithm

Three parallel reviewers evaluate the enriched plan. Any BLOCK verdict halts the pipeline.

**Team**: `arc-plan-review-{id}`
**Tools (read-only)**: Read, Glob, Grep, Write (own output file only)
**Duration**: Max 15 minutes (inner 10m + 5m setup)
**Inputs**: id (string, validated at arc init), enriched plan path (`tmp/arc/{id}/enriched-plan.md`)
**Outputs**: `tmp/arc/{id}/plan-review.md`
**Error handling**: BLOCK verdict halts pipeline. User fixes plan, then `/rune:arc --resume`.
**Consumers**: arc.md (Phase 2 stub)

## ATE-1 Compliance

This phase creates a team and spawns agents. It MUST follow the Agent Teams pattern:

```
1. TeamCreate({ team_name: "arc-plan-review-{id}" })     ← CREATE TEAM FIRST
2. TaskCreate({ subject: ..., description: ... })          ← CREATE TASKS
3. Task({ team_name: "arc-plan-review-{id}", name: "...", ← SPAWN WITH team_name
     subagent_type: "general-purpose",                     ← ALWAYS general-purpose
     prompt: "...", ... })                                  ← IDENTITY VIA PROMPT
4. Monitor → Shutdown → TeamDelete with fallback           ← CLEANUP
```

**NEVER** use bare `Task()` calls or named `subagent_type` values in this phase.

## Algorithm

```javascript
updateCheckpoint({ phase: "plan_review", status: "in_progress", phase_sequence: 2, team_name: `arc-plan-review-${id}` })

// Pre-create guard (see rune-orchestration/references/team-lifecycle-guard.md)
// QUAL-13 FIX: Full regex validation per team-lifecycle-guard.md (defense-in-depth)
if (!/^arc-[a-zA-Z0-9_-]+$/.test(id)) throw new Error('Invalid arc id')
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
```

### parseVerdict()

Parse structured verdict markers using anchored regex. Defaults to CONCERN if marker is missing or malformed.

```javascript
const parseVerdict = (reviewer, output) => {
  const pattern = /^<!-- VERDICT:([a-zA-Z_-]+):(PASS|CONCERN|BLOCK) -->$/m
  const match = output.match(pattern)
  if (!match) { warn(`Reviewer ${reviewer} output lacks verdict marker — defaulting to CONCERN.`); return "CONCERN" }
  if (match[1] !== reviewer) warn(`Verdict marker reviewer mismatch: expected ${reviewer}, found ${match[1]}.`)
  return match[2]
}
```

### Circuit Breaker

| Condition | Action |
|-----------|--------|
| Any reviewer returns BLOCK | HALT pipeline, report blocking reviewer + reason |
| All PASS (with optional CONCERNs) | Proceed to Phase 2.5 |

```javascript
updateCheckpoint({
  phase: "plan_review", status: blocked ? "failed" : "completed",
  artifact: `tmp/arc/${id}/plan-review.md`, artifact_hash: sha256(planReview), phase_sequence: 2
})
```

**Output**: `tmp/arc/{id}/plan-review.md`

If blocked: user fixes plan, then `/rune:arc --resume`.

## Cleanup

Dynamic member discovery reads the team config to find ALL teammates (catches teammates summoned in any phase, not just the initial batch):

```javascript
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
// SEC-003: id validated at arc init (/^arc-[a-zA-Z0-9_-]+$/) — see Initialize Checkpoint section
try { TeamDelete() } catch (e) {
  Bash(`rm -rf ~/.claude/teams/arc-plan-review-${id}/ ~/.claude/tasks/arc-plan-review-${id}/ 2>/dev/null`)
}
```
