---
name: rune:cancel-arc
description: |
  Cancel an active arc pipeline and gracefully shutdown all phase teammates.
  Completed phase artifacts are preserved. Only the currently-active phase is cancelled.

  <example>
  user: "/rune:cancel-arc"
  assistant: "The Tarnished halts the arc..."
  </example>
user-invocable: true
allowed-tools:
  - TaskList
  - TaskUpdate
  - TaskGet
  - TeamDelete
  - SendMessage
  - Read
  - Write
  - Bash
  - Glob
---

# /rune:cancel-arc — Cancel Active Arc Pipeline

Cancel an active arc pipeline and gracefully shutdown all phase teammates. Completed phase artifacts are preserved.

## Steps

### 0. Cancel Arc-Batch Loop (if active)

```javascript
// Check for active arc-batch loop state file
const batchStateFile = ".claude/arc-batch-loop.local.md"
const batchExists = Bash(`test -f "${batchStateFile}" && echo "yes" || echo "no"`).trim()

if (batchExists === "yes") {
  // Read iteration info before removing
  const batchContent = Read(batchStateFile)
  const iterMatch = batchContent.match(/iteration:\s*(\d+)/)
  const totalMatch = batchContent.match(/total_plans:\s*(\d+)/)
  const iteration = iterMatch ? iterMatch[1] : "?"
  const total = totalMatch ? totalMatch[1] : "?"

  // Remove state file to stop the batch loop
  Bash('rm -f .claude/arc-batch-loop.local.md')
  log(`Arc-batch loop also cancelled (was at iteration ${iteration}/${total})`)
}
```

### 1. Find Active Arc

```bash
# Find active arc checkpoint files
ls .claude/arc/*/checkpoint.json 2>/dev/null
```

If no active arc found: "No active arc pipeline to cancel."

### 2. Read Checkpoint

```javascript
checkpoint = Read(".claude/arc/{id}/checkpoint.json")

// Validate arc id from checkpoint before using in path construction
if (!/^arc-[a-zA-Z0-9_-]+$/.test(id)) throw new Error("Invalid arc id")

// Derive current phase — checkpoint has no `current_phase` field,
// scan phases object for the one with status "in_progress"
const [current_phase, phase_info] = Object.entries(checkpoint.phases)
  .find(([_, v]) => v.status === "in_progress") || [null, null]

phase_status = phase_info?.status

// Resolve team name from checkpoint (set by arc orchestrator when phase started)
let phase_team = phase_info?.team_name
if (!phase_team) {
  // Fallback for older checkpoints without team_name field
  const legacyMap = {
    forge: null,              // Pre-v1.28.2: inline forge had no team. v1.28.2+: checkpoint.team_name preferred; state file fallback at line 74
    plan_review: `arc-plan-review-${id}`,
    plan_refine: null,        // Orchestrator-only phase, no team
    verification: null,       // Orchestrator-only phase, no team
    work: null,               // Delegated (v1.28.0) -- team name from checkpoint
    gap_analysis: null,       // Orchestrator-only phase, no team
    verify_mend: null,        // Orchestrator-only phase, no team (convergence gate)
    code_review: null,        // Delegated (v1.28.0) -- team name from checkpoint
    mend: `arc-mend-${id}`,
    audit: null               // Delegated (v1.28.0) -- team name from checkpoint
  }
  phase_team = legacyMap[current_phase]
}

// Secondary fallback — discover team from state file for all delegated phases
if (phase_team === null && current_phase) {
  const typeMap = {
    forge: "forge", work: "work",
    code_review: "review", mend: "mend", audit: "audit"
  }
  const type = typeMap[current_phase]
  if (type) {
    // BACK-004 FIX: Best-effort fallback — Glob order is arbitrary. First active match is used.
    // Primary team discovery is checkpoint.team_name above; this is degraded-mode recovery.
    const stateFiles = Glob(`tmp/.rune-${type}-*.json`)
    for (const f of stateFiles) {
      try {
        const stateData = JSON.parse(Read(f))
        const teamPattern = new RegExp(`^rune-${type}-[a-zA-Z0-9_-]+$`)
        if (stateData.status === "active" && stateData.team_name && teamPattern.test(stateData.team_name)) {
          phase_team = stateData.team_name
          break
        }
      } catch (e) { /* state file corrupted -- skip */ }
    }
  }
}

// Orchestrator-only phases (plan_refine, verification, gap_analysis, verify_mend) have no team.
// Skip team cancellation (Steps 3a-3d), go directly to Step 4.
if (phase_team === null || phase_team === undefined) {
  // No team to cancel — update checkpoint directly (Step 4)
}
```

If no phase has `status === "in_progress"`: "No active phase to cancel. Arc is idle or completed."

### 3. Cancel Current Phase

Delegate cancellation based on the currently-active phase:

| Phase | Action |
|-------|--------|
| **FORGE** (Phase 1) | Shutdown research team — broadcast cancellation, send shutdown requests |
| **PLAN REVIEW** (Phase 2) | Shutdown decree-arbiter review team |
| **PLAN REFINEMENT** (Phase 2.5) | No-op — orchestrator-only, no team to cancel. Skip to Step 4 |
| **VERIFICATION** (Phase 2.7) | No-op — orchestrator-only, no team to cancel. Skip to Step 4 |
| **WORK** (Phase 5) | Shutdown work team — broadcast cancellation, send shutdown requests to all rune-smith workers |
| **GAP ANALYSIS** (Phase 5.5) | No-op — orchestrator-only, no team to cancel. Skip to Step 4 |
| **CODE REVIEW** (Phase 6) | Delegate to `/rune:cancel-review` logic — broadcast, shutdown Ash, cleanup |
| **MEND** (Phase 7) | Shutdown mend team — broadcast cancellation, send shutdown requests to all mend-fixer workers |
| **VERIFY MEND** (Phase 7.5) | No-op — orchestrator-only, no team to cancel. Skip to Step 4 |
| **AUDIT** (Phase 8) | Delegate to `/rune:cancel-audit` logic — broadcast, shutdown Ash, cleanup |

#### 3a. Broadcast Cancellation

```javascript
SendMessage({
  type: "broadcast",
  content: "Arc pipeline cancelled by user. Please finish current work and shutdown.",
  summary: "Arc cancelled"
})
```

#### 3b. Shutdown All Teammates

```javascript
// Read task list and cancel pending tasks
tasks = TaskList()
for (const task of tasks) {
  if (task.status === "pending" || task.status === "in_progress") {
    TaskUpdate({ taskId: task.id, status: "deleted" })
  }
}

// Read team config to discover active teammates — with fallback if config is missing/corrupt
let allMembers = []
try {
  const teamConfig = Read(`~/.claude/teams/${phase_team}/config.json`)
  const members = Array.isArray(teamConfig.members) ? teamConfig.members : []
  allMembers = members.map(m => m.name).filter(n => n && /^[a-zA-Z0-9_-]+$/.test(n))
} catch (e) {
  warn("Could not read team config — attempting TeamDelete directly")
  allMembers = []
}

for (const member of allMembers) {
  SendMessage({
    type: "shutdown_request",
    recipient: member,
    content: "Arc pipeline cancelled by user"
  })
}
```

#### 3c. Wait for Approvals (Max 30s)

Wait for shutdown responses. After 30 seconds, proceed regardless.

#### 3d. Delete Team

```javascript
// phase_team resolved in Step 2 from checkpoint.phases[current_phase].team_name
// (with legacy fallback for older checkpoints)
// SEC-003 FIX: Validate phase_team early + skip retry loop for null phase_team
if (phase_team && !/^[a-zA-Z0-9_-]+$/.test(phase_team)) throw new Error("Invalid phase_team")
if (phase_team && phase_team.includes('..')) throw new Error('Path traversal detected in phase_team')
if (phase_team) {
  // TeamDelete with retry-with-backoff (3 attempts: 0s, 3s, 8s)
  const RETRY_DELAYS = [0, 3000, 8000]
  for (let attempt = 0; attempt < RETRY_DELAYS.length; attempt++) {
    if (attempt > 0) {
      warn(`Cancel cleanup: TeamDelete attempt ${attempt + 1} failed, retrying in ${RETRY_DELAYS[attempt]/1000}s...`)
      Bash(`sleep ${RETRY_DELAYS[attempt] / 1000}`)
    }
    try {
      TeamDelete()
      break
    } catch (e) {
      if (attempt === RETRY_DELAYS.length - 1) {
        warn(`Cancel cleanup: TeamDelete failed after ${RETRY_DELAYS.length} attempts. Using filesystem fallback.`)
      }
    }
  }
  // Filesystem fallback with CHOME
  // SEC-003: phase_team validated above — contains only [a-zA-Z0-9_-]
  Bash(`CHOME="\${CLAUDE_CONFIG_DIR:-$HOME/.claude}" && rm -rf "$CHOME/teams/${phase_team}/" "$CHOME/tasks/${phase_team}/" 2>/dev/null`)
} // end if (phase_team)
```

### 4. Update Checkpoint

```bash
# Update checkpoint.json — mark current phase as cancelled
# Read current checkpoint, update phase status, write back
```

Update the checkpoint so that:
- `phases[{current_phase}].status` = `"cancelled"` (where `current_phase` is derived from scanning `phases` for `"in_progress"`)
- `phases[{current_phase}].cancelled_at` = ISO timestamp
- Overall arc status remains intact (not "completed")

### 5. Preserve Completed Artifacts

Do NOT delete any files from completed phases:
- `.claude/arc/{id}/` directory is preserved
- `tmp/` output from completed phases is preserved
- Only the in-progress phase's team resources are cleaned up

### 6. Report

```
Arc pipeline cancelled.

Phase {N} ({PHASE_NAME}) was in progress — cancelled.
Completed phases preserved:
- Phase 1 (FORGE): {status}
- Phase 2 (PLAN REVIEW): {status}
- Phase 2.5 (PLAN REFINEMENT): {status}
- Phase 2.7 (VERIFICATION): {status}
- Phase 5 (WORK): {status}
- Phase 5.5 (GAP ANALYSIS): {status}
- Phase 6 (CODE REVIEW): {status}
- Phase 7 (MEND): {status}
- Phase 7.5 (VERIFY MEND): {status}
- Phase 8 (AUDIT): {status}

Artifacts remain in: .claude/arc/{id}/
To resume: /rune:arc --resume
```

## Notes

- Only the currently-active phase is cancelled — completed phases are untouched
- All team resources (Agent Teams) are fully cleaned up
- Checkpoint file is updated to reflect cancellation, enabling `--resume` later
- Pending and in-progress tasks are deleted to prevent orphaned work
- If the arc has multiple active checkpoints, cancel the most recent one
