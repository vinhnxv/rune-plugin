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
    forge: `arc-forge-${id}`,
    plan_review: `arc-plan-review-${id}`,
    work: `arc-work-${id}`,
    code_review: `arc-review-${id}`,
    mend: `arc-mend-${id}`,
    audit: `arc-audit-${id}`
  }
  phase_team = legacyMap[current_phase]
}
```

If no phase has `status === "in_progress"`: "No active phase to cancel. Arc is idle or completed."

### 3. Cancel Current Phase

Delegate cancellation based on the currently-active phase:

| Phase | Action |
|-------|--------|
| **FORGE** (Phase 1) | Shutdown research team — broadcast cancellation, send shutdown requests |
| **PLAN REVIEW** (Phase 2) | Shutdown decree-arbiter review team |
| **WORK** (Phase 3) | Shutdown work team — broadcast cancellation, send shutdown requests to all rune-smith workers |
| **CODE REVIEW** (Phase 4) | Delegate to `/rune:cancel-review` logic — broadcast, shutdown Ash, cleanup |
| **MEND** (Phase 5) | Shutdown mend team — broadcast cancellation, send shutdown requests to all mend-fixer workers |
| **AUDIT** (Phase 6) | Delegate to `/rune:cancel-audit` logic — broadcast, shutdown Ash, cleanup |

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

// Read team config to discover active teammates
const teamConfig = Read(`~/.claude/teams/${phase_team}/config.json`)
for (const member of teamConfig.members) {
  SendMessage({
    type: "shutdown_request",
    recipient: member.name,
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
try { TeamDelete() } catch (e) {
  if (phase_team && /^[a-zA-Z0-9_-]+$/.test(phase_team)) {
    Bash(`rm -rf ~/.claude/teams/${phase_team}/ ~/.claude/tasks/${phase_team}/ 2>/dev/null`)
  }
}
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
- ...

Artifacts remain in: .claude/arc/{id}/
To resume: /rune:arc --resume
```

## Notes

- Only the currently-active phase is cancelled — completed phases are untouched
- All team resources (Agent Teams) are fully cleaned up
- Checkpoint file is updated to reflect cancellation, enabling `--resume` later
- Pending and in-progress tasks are deleted to prevent orphaned work
- If the arc has multiple active checkpoints, cancel the most recent one
