# Team Lifecycle Guard — Safe TeamCreate/TeamDelete

Defensive patterns for Agent Teams lifecycle management. Prevents "Already leading team" and "Cannot cleanup team with N active members" errors. Every command that creates an Agent Team MUST follow these patterns.

## Problem

The Claude Agent SDK has two constraints:
1. **One team per lead** — `TeamCreate` fails if a previous team wasn't cleaned up
2. **TeamDelete requires deregistration** — agents may not deregister in time even after approving shutdown

Both are observed in production and cause workflow failures if not handled.

## Pre-Create Guard

Before `TeamCreate`, clean up stale teams from crashed prior sessions:

```javascript
// 1. Validate identifier (REQUIRED — this is the ONLY barrier against path traversal)
// Security pattern: SAFE_IDENTIFIER_PATTERN — see security-patterns.md
if (!/^[a-zA-Z0-9_-]+$/.test(identifier)) throw new Error("Invalid identifier")
// SEC-003: Redundant path traversal check — defense-in-depth
if (identifier.includes('..')) throw new Error('Path traversal detected')

// 2. Attempt TeamDelete (catches most cases)
try { TeamDelete() } catch (e) {
  // 3. Fallback: direct directory removal (handles orphaned state)
  Bash(`rm -rf ~/.claude/teams/${teamPrefix}-${identifier}/ ~/.claude/tasks/${teamPrefix}-${identifier}/ 2>/dev/null`)
}

// 4. Create fresh team
TeamCreate({ team_name: `${teamPrefix}-${identifier}` })
```

**Key safety properties:**
- Identifier validation and `rm -rf` are co-located (same code block)
- The regex `/^[a-zA-Z0-9_-]+$/` prevents shell metacharacters and path traversal
- The `..` check is redundant but provides defense-in-depth
- `TeamDelete` is tried first (clean API path); `rm -rf` is the fallback only

**When to use**: Before EVERY `TeamCreate` call. No exceptions.

## Cleanup Fallback

At session end, after shutting down all teammates:

```javascript
// 1. Shutdown all teammates
for (const teammate of allTeammates) {
  SendMessage({ type: "shutdown_request", recipient: teammate })
}

// 2. Wait for approvals (max 30s)

// 3. Cleanup team with fallback
// NOTE: identifier was validated at team creation time (pre-create guard above)
try { TeamDelete() } catch (e) {
  Bash(`rm -rf ~/.claude/teams/${teamPrefix}-${identifier}/ ~/.claude/tasks/${teamPrefix}-${identifier}/ 2>/dev/null`)
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
try { TeamDelete() } catch (e) {
  Bash(`rm -rf ~/.claude/teams/${teamPrefix}-${identifier}/ ~/.claude/tasks/${teamPrefix}-${identifier}/ 2>/dev/null`)
}
```

## Input Validation

Validate team names before interpolating into `rm -rf` commands.

```javascript
// Validate team_name matches safe pattern (alphanumeric, hyphens, underscores only)
if (!/^[a-zA-Z0-9_-]+$/.test(team_name)) {
  throw new Error(`Invalid team_name: ${team_name}`)
}
```

For commands where `team_name` is hardcoded with a known-safe prefix (e.g., `rune-review-{timestamp}`), the risk is low since the prefix anchors the path. For cancel commands where `team_name` is read from a state file, validation is **required** since the state file could be tampered with.

## Team Naming Conventions

| Command | Team Prefix | Identifier Source |
|---------|------------|-------------------|
| `/rune:review` | `rune-review` | `{identifier}` (git hash or user-provided) |
| `/rune:audit` | `rune-audit` | `{identifier}` |
| `/rune:plan` | `rune-plan` | `{timestamp}` (YYYYMMDD-HHMMSS) |
| `/rune:work` | `rune-work` | `{timestamp}` |
| `/rune:mend` | `rune-mend` | `{id}` (from TOME path or generated) |
| `/rune:forge` | `rune-forge` | `{id}` |
| `/rune:arc` (plan review) | `arc-plan-review` | `{id}` (arc session id) |
| `/rune:arc` (delegated) | per sub-command | per sub-command |

## Arc Phase Teams

| Phase | Team Owner | Lifecycle |
|-------|-----------|-----------|
| Phase 1: FORGE | `/rune:forge` (delegated) | Forge manages own TeamCreate/TeamDelete |
| Phase 2: PLAN REVIEW | Arc orchestrator | `arc-plan-review-{id}` |
| Phase 2.5: REFINE | Orchestrator-only (no team) | N/A |
| Phase 2.7: VERIFY | Orchestrator-only (no team) | N/A |
| Phase 5: WORK | `/rune:work` (delegated) | Work manages own lifecycle |
| Phase 5.5: GAP ANALYSIS | Orchestrator-only (no team) | N/A |
| Phase 6: REVIEW | `/rune:review` (delegated) | Review manages own lifecycle |
| Phase 7: MEND | `/rune:mend` (delegated) | Mend manages own lifecycle |
| Phase 7.5: VERIFY MEND | Orchestrator-only (no team) | N/A |
| Phase 8: AUDIT | `/rune:audit` (delegated) | Audit manages own lifecycle |

## Consumers

All multi-agent commands: plan.md, work.md, arc.md, mend.md, review.md, audit.md, forge.md, cancel-review.md, cancel-audit.md, cancel-arc.md, research-phase.md

## Notes

- The filesystem fallback (`rm -rf ~/.claude/teams/...`) is safe — these directories only contain Agent SDK coordination state, not user data
- For additional defense-in-depth, commands that delete user-facing directories (e.g., `/rune:rest`) should use `realpath` containment checks in addition to team name validation
- Do not interpolate unsanitized external input into team names — validate first
- Always update workflow state files (e.g., `tmp/.rune-review-{id}.json`) AFTER team cleanup, not before
- The 30s wait is a best-effort grace period — some agents may need longer for complex file writes
- Arc pipelines call TeamCreate/TeamDelete per-phase, so each phase transition needs the pre-create guard
