# Team Lifecycle Guard — Safe TeamCreate/TeamDelete

Defensive patterns for Agent Teams lifecycle management. Prevents "Already leading team" and "Cannot cleanup team with N active members" errors.

## Problem

The Claude Agent SDK has two constraints:
1. **One team per lead** — `TeamCreate` fails if a previous team wasn't cleaned up
2. **TeamDelete requires deregistration** — agents may not deregister in time even after approving shutdown

Both are observed in production and cause workflow failures if not handled.

## Pre-Create Guard

Before every `TeamCreate`, check for and cleanup any lingering team:

```javascript
// Pre-create guard: cleanup stale team if exists
try {
  TeamDelete()
} catch (e) {
  // TeamDelete may fail if members didn't deregister — force cleanup
  Bash("rm -rf ~/.claude/teams/{team_name}/ ~/.claude/tasks/{team_name}/ 2>/dev/null")
}

// Now safe to create
TeamCreate({ team_name: "{team_name}" })
```

**When to use**: Before EVERY `TeamCreate` call. No exceptions.

## Cleanup with Fallback

After workflow completion, use graceful shutdown with filesystem fallback:

```javascript
// 1. Send shutdown requests to all teammates
for (const agent of allAgents) {
  SendMessage({ type: "shutdown_request", recipient: agent.name, content: "Workflow complete" })
}

// 2. Wait for shutdown approvals (max 30s)
// Agents should respond with shutdown_response { approve: true }

// 3. TeamDelete with fallback
try {
  TeamDelete()
} catch (e) {
  // Force cleanup if agents didn't deregister in time
  Bash("rm -rf ~/.claude/teams/{team_name}/ ~/.claude/tasks/{team_name}/ 2>/dev/null")
}
```

**When to use**: At EVERY workflow cleanup point — both normal completion and cancellation.

## Cancel Command Pattern

Cancel commands use the same cleanup-with-fallback but add broadcast + task cancellation:

```javascript
// 1. Broadcast cancellation
SendMessage({ type: "broadcast", content: "Cancelled by user. Shutdown.", summary: "Cancelled" })

// 2. Cancel pending/in-progress tasks
tasks = TaskList()
for (const task of tasks) {
  if (task.status === "pending" || task.status === "in_progress") {
    TaskUpdate({ taskId: task.id, status: "deleted" })
  }
}

// 3. Shutdown all teammates
for (const member of teamMembers) {
  SendMessage({ type: "shutdown_request", recipient: member.name, content: "Cancelled" })
}

// 4. Wait (max 30s)

// 5. TeamDelete with fallback
try {
  TeamDelete()
} catch (e) {
  Bash("rm -rf ~/.claude/teams/{team_name}/ ~/.claude/tasks/{team_name}/ 2>/dev/null")
}
```

## Input Validation

**IMPORTANT**: Always validate team names before interpolating into `rm -rf` commands.

```javascript
// Validate team_name matches safe pattern (alphanumeric, hyphens, underscores only)
if (!/^[a-zA-Z0-9_-]+$/.test(team_name)) {
  throw new Error(`Invalid team_name: ${team_name}`)
}
```

For commands where `team_name` is hardcoded with a known-safe prefix (e.g., `rune-review-{timestamp}`), the risk is low since the prefix anchors the path. For cancel commands where `team_name` is read from a state file, validation is **required** since the state file could be tampered with.

## Team Naming Convention

| Command | Team Name Pattern |
|---------|-------------------|
| `/rune:plan` | `rune-plan-{timestamp}` |
| `/rune:work` | `rune-work-{timestamp}` |
| `/rune:review` | `rune-review-{identifier}` |
| `/rune:audit` | `rune-audit-{audit_id}` |
| `/rune:mend` | `mend-{timestamp}` |
| `/rune:arc` Phase 1 | `arc-forge-{id}` |
| `/rune:arc` Phase 2 | `arc-plan-review-{id}` |
| `/rune:arc` Phases 2.5, 2.7 | Orchestrator-only (no team) |
| `/rune:arc` Phases 5-8 | Delegated to work/review/mend/audit commands |

## Notes

- The filesystem fallback (`rm -rf ~/.claude/teams/...`) is safe — these directories only contain Agent SDK coordination state, not user data
- For additional defense-in-depth, commands that delete user-facing directories (e.g., `/rune:rest`) should use `realpath` containment checks in addition to team name validation
- Callers MUST NOT interpolate unsanitized external input into team names — always validate first
- Always update workflow state files (e.g., `tmp/.rune-review-{id}.json`) AFTER team cleanup, not before
- The 30s wait is a best-effort grace period — some agents may need longer for complex file writes
- Arc pipelines call TeamCreate/TeamDelete per-phase, so each phase transition needs the pre-create guard
