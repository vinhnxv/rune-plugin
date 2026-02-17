# Phase 2: PLAN REVIEW — Full Algorithm

Three parallel reviewers evaluate the enriched plan. Any BLOCK verdict halts the pipeline.

**Team**: `arc-plan-review-{id}`
**Tools (read-only)**: Read, Glob, Grep, Write (own output file only)
**Timeout**: 15 min (PHASE_TIMEOUTS.plan_review = 900_000 — inner 10m + 5m setup)
**Inputs**: id (string, validated at arc init), enriched plan path (`tmp/arc/{id}/enriched-plan.md`)
**Outputs**: `tmp/arc/{id}/plan-review.md`
**Error handling**: BLOCK verdict halts pipeline. User fixes plan, then `/rune:arc --resume`.
**Consumers**: SKILL.md (Phase 2 stub)

> **Note**: `sha256()`, `updateCheckpoint()`, `exists()`, and `warn()` are dispatcher-provided utilities available in the arc orchestrator context. Phase reference files call these without import.

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

// Pre-create guard (see team-lifecycle-guard.md)
// QUAL-13 FIX: Full regex validation per team-lifecycle-guard.md (defense-in-depth)
if (!/^arc-[a-zA-Z0-9_-]+$/.test(id)) throw new Error('Invalid arc id')
// SEC-3 FIX: Redundant path traversal check — defense-in-depth (matches arc-phase-forge.md pattern)
if (id.includes('..')) throw new Error('Path traversal detected in arc id')
// NOTE: prePhaseCleanup(checkpoint) runs BEFORE this phase (added in v1.28.1),
// clearing SDK leadership state + prior phase team dirs. This inline guard is
// defense-in-depth for the specific team being created (stale same-name team).
// teamTransition — inlined 5-step protocol (see team-lifecycle-guard.md)
// STEP 1: TeamDelete with retry-with-backoff (3 attempts: 0s, 3s, 8s)
const RETRY_DELAYS = [0, 3000, 8000]
for (let attempt = 0; attempt < RETRY_DELAYS.length; attempt++) {
  if (attempt > 0) {
    warn(`arc-plan-review: TeamDelete attempt ${attempt} failed, retrying in ${RETRY_DELAYS[attempt]/1000}s...`)
    Bash(`sleep ${RETRY_DELAYS[attempt] / 1000}`)
  }
  try {
    TeamDelete()
    break
  } catch (e) {
    if (attempt === RETRY_DELAYS.length - 1) {
      warn(`arc-plan-review: TeamDelete failed after ${RETRY_DELAYS.length} attempts. Using filesystem fallback.`)
    }
  }
}
// STEP 2: rm-rf TARGET team dirs (filesystem fallback)
Bash(`CHOME="\${CLAUDE_CONFIG_DIR:-$HOME/.claude}" && rm -rf "$CHOME/teams/arc-plan-review-${id}/" "$CHOME/tasks/arc-plan-review-${id}/" 2>/dev/null`)
// STEP 3: Cross-workflow scan — clean ANY stale rune/arc team dirs
Bash(`CHOME="\${CLAUDE_CONFIG_DIR:-$HOME/.claude}" && find "$CHOME/teams/" -maxdepth 1 -type d \( -name "rune-*" -o -name "arc-*" \) -exec rm -rf {} + && find "$CHOME/tasks/" -maxdepth 1 -type d \( -name "rune-*" -o -name "arc-*" \) -exec rm -rf {} + 2>/dev/null`)
// STEP 4: TeamCreate with "Already leading" catch-and-recover
try {
  TeamCreate({ team_name: `arc-plan-review-${id}` })
} catch (createError) {
  if (/already leading/i.test(createError.message)) {
    warn(`arc-plan-review: "Already leading" detected — clearing stale leadership and retrying...`)
    try { TeamDelete() } catch (_) {}
    Bash(`CHOME="\${CLAUDE_CONFIG_DIR:-$HOME/.claude}" && rm -rf "$CHOME/teams/arc-plan-review-${id}/" "$CHOME/tasks/arc-plan-review-${id}/" 2>/dev/null`)
    try {
      TeamCreate({ team_name: `arc-plan-review-${id}` })
    } catch (finalError) {
      throw new Error(`teamTransition failed: unable to create team after exhausting all cleanup strategies. Run /rune:rest --heal to manually clean up, then retry. (${finalError.message})`)
    }
  } else { throw createError }
}
// STEP 5: Post-create verification
// TOME-3 FIX: Use Bash test -f + CHOME for consistency with command files
Bash(`CHOME="\${CLAUDE_CONFIG_DIR:-$HOME/.claude}" && test -f "$CHOME/teams/arc-plan-review-${id}/config.json" || echo "WARN: config.json not found after TeamCreate"`)


// Delegation checklist: see arc-delegation-checklist.md (Phase 2)
const reviewers = [
  { name: "scroll-reviewer", agent: "agents/utility/scroll-reviewer.md", focus: "Document quality" },
  { name: "decree-arbiter", agent: "agents/utility/decree-arbiter.md", focus: "Technical soundness" },
  { name: "knowledge-keeper", agent: "agents/utility/knowledge-keeper.md", focus: "Documentation coverage" }
]

// Codex Plan Reviewer (optional 4th reviewer — see arc-delegation-checklist.md Phase 2)
// Detection: canonical codex-detection.md algorithm (9 steps, NOT inline simplified check)
// Arc-mode adaptation: if .codexignore is missing, skip Codex silently (no AskUserQuestion)
// — AskUserQuestion would block the automated arc pipeline indefinitely.
const codexDetected = detectCodexOracle()  // per roundtable-circle/references/codex-detection.md
if (codexDetected && talisman?.codex?.workflows?.includes("plan")) {
  reviewers.push({
    name: "codex-plan-reviewer",
    agent: null,  // CLI-backed reviewer — uses codex exec directly, no agent file
    focus: "Cross-model plan verification (Codex Oracle)"
  })
}

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

// Monitor with timeout — see roundtable-circle/references/monitor-utility.md
const result = waitForCompletion(`arc-plan-review-${id}`, reviewers.length, {
  timeoutMs: PHASE_TIMEOUTS.plan_review, staleWarnMs: STALE_THRESHOLD,
  pollIntervalMs: 30_000, label: "Arc: Plan Review"
})

// Match completed tasks to reviewers by task subject (more reliable than owner name matching)
result.completed.forEach(t => {
  const r = reviewers.find(r => t.subject.includes(r.name) || t.owner === r.name)
  if (r) r.completed = true
})

if (result.timedOut) {
  warn("Phase 2 (PLAN REVIEW) timed out.")
  for (const reviewer of reviewers) {
    if (!reviewer.completed) {
      const outputPath = `tmp/arc/${id}/reviews/${reviewer.name}-verdict.md`
      if (exists(outputPath)) {
        // CDX-3 FIX: Verify file has a VERDICT marker before treating as complete
        const partialOutput = Read(outputPath)
        if (/<!-- VERDICT:/.test(partialOutput)) {
          reviewer.verdict = parseVerdict(reviewer.name, partialOutput)
        } else {
          warn(`${reviewer.name} output file exists but lacks VERDICT marker — treating as incomplete`)
          reviewer.verdict = "CONCERN"
        }
      } else {
        // QUAL-14 FIX: Write synthetic verdict so Phase 2.5 can read it from disk
        reviewer.verdict = "CONCERN"
        Write(outputPath, `# ${reviewer.name} — Timed Out\n\nReviewer did not complete within timeout.\n\n<!-- VERDICT:${reviewer.name}:CONCERN -->`)
      }
    }
  }
}

// Collect verdicts, merge → tmp/arc/{id}/plan-review.md
```

### parseVerdict()

Parse structured verdict markers using anchored regex. Defaults to CONCERN if marker is missing or malformed.

```javascript
// Also duplicated in arc-phase-plan-refine.md for self-containment — keep in sync.
const parseVerdict = (reviewer, output) => {
  const pattern = /^<!-- VERDICT:([a-zA-Z_-]+):(PASS|CONCERN|BLOCK) -->$/m
  const match = output.match(pattern)
  if (!match) { warn(`Reviewer ${reviewer} output lacks verdict marker — defaulting to CONCERN.`); return "CONCERN" }
  if (match[1] !== reviewer) warn(`Verdict marker reviewer mismatch: expected ${reviewer}, found ${match[1]}.`)
  return match[2]
}
```

### Verdict Definitions

| Verdict | Meaning |
|---------|---------|
| **PASS** | Plan is sound and ready for implementation |
| **CONCERN** | Issues worth noting but not blocking — workers should address these during implementation |
| **BLOCK** | Critical flaw that must be fixed before implementation can proceed |

### Circuit Breaker

| Condition | Action |
|-----------|--------|
| Any reviewer returns BLOCK | HALT pipeline, report blocking reviewer + reason |
| No BLOCK verdicts (mix of PASS/CONCERN) | Proceed to Phase 2.5 |

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
  // SEC-4 FIX: Validate member names against safe pattern before use in SendMessage
  allMembers = members.map(m => m.name).filter(n => n && /^[a-zA-Z0-9_-]+$/.test(n))
} catch (e) {
  // FALLBACK: Phase 2 plan review — these are the 3 reviewers summoned in this specific phase
  allMembers = ["scroll-reviewer", "decree-arbiter", "knowledge-keeper"]
}

// Shutdown all discovered members
for (const member of allMembers) { SendMessage({ type: "shutdown_request", recipient: member, content: "Plan review complete" }) }
// SEC-003: id validated at arc init (/^arc-[a-zA-Z0-9_-]+$/) — see Initialize Checkpoint section
// TeamDelete with retry-with-backoff (3 attempts: 0s, 3s, 8s)
const CLEANUP_DELAYS = [0, 3000, 8000]
for (let attempt = 0; attempt < CLEANUP_DELAYS.length; attempt++) {
  if (attempt > 0) Bash(`sleep ${CLEANUP_DELAYS[attempt] / 1000}`)
  try { TeamDelete(); break } catch (e) {
    if (attempt === CLEANUP_DELAYS.length - 1) warn(`arc-plan-review cleanup: TeamDelete failed after ${CLEANUP_DELAYS.length} attempts`)
  }
}
// Filesystem fallback with CHOME
Bash(`CHOME="\${CLAUDE_CONFIG_DIR:-$HOME/.claude}" && rm -rf "$CHOME/teams/arc-plan-review-${id}/" "$CHOME/tasks/arc-plan-review-${id}/" 2>/dev/null`)
```
