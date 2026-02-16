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
// Security pattern: SAFE_IDENTIFIER_PATTERN = /^[a-zA-Z0-9_-]+$/ — alphanumeric, hyphens, underscores only
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

> **DEPRECATED**: The static cleanup pattern (hardcoded teammate list) is superseded by the **Dynamic Cleanup with Member Discovery** pattern below. All new code MUST use the dynamic pattern. The static pattern is not shown here to prevent accidental copying — see git history for the old example if needed.

**Always use** the Dynamic Cleanup with Member Discovery pattern at EVERY workflow cleanup point — both normal completion and cancellation.

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

## Dynamic Cleanup with Member Discovery

Static teammate lists in cleanup phases can miss dynamically-added members or leave "zombie" teammates running after cleanup completes. The solution: read the team's `config.json` at cleanup time to discover ALL active members, regardless of how many were spawned or what they're named.

### Why dynamic?

When a workflow spawns teammates, the set of active members may differ from what was originally planned:
- A teammate may have been added mid-workflow (e.g., extra workers spawned for load balancing)
- A teammate may have crashed and been replaced with a differently-named instance
- The orchestrator's local list may be stale after compaction or session resume

Hardcoding teammate names in cleanup logic creates a **zombie teammate problem** — members not in the static list survive shutdown and hold resources indefinitely. Dynamic discovery from `config.json` eliminates this class of bug.

### config.json Schema

The Agent SDK maintains a team config file at `~/.claude/teams/{team_name}/config.json`:

```javascript
// ~/.claude/teams/{team_name}/config.json (managed by Agent SDK)
{
  "team_name": "rune-review-abc123",
  "members": [
    { "name": "ash-iron-abc123", "status": "active" },
    { "name": "ash-silver-abc123", "status": "active" }
    // SDK excludes team-lead from members array
  ]
}
```

Key properties:
- `members` — array of all active teammate entries (team-lead is excluded by the SDK)
- Each member has a `name` field matching the name used in `SendMessage`
- The SDK maintains this file automatically as teammates are spawned/removed

### Dynamic Discovery Pattern

```javascript
// 1. Read team config to discover ALL active teammates
// Read returns file text; Claude interprets JSON structure from the content
let allMembers = []
try {
  const teamConfig = Read(`~/.claude/teams/${team_name}/config.json`)
  const members = Array.isArray(teamConfig.members) ? teamConfig.members : []
  allMembers = members.map(m => m.name).filter(n => n && /^[a-zA-Z0-9_-]+$/.test(n))
  // Defense-in-depth: SDK already excludes team-lead from config.members
} catch (e) {
  // FALLBACK: Config read failed — use known teammate list from command context
  // Each command provides its own fallback (e.g., allWorkers, allFixers, selectedAsh)
  allMembers = [...fallbackList]
}

// 2. Shutdown all discovered members
for (const member of allMembers) {
  SendMessage({ type: "shutdown_request", recipient: member, content: "Workflow complete" })
}

// 3. Wait for shutdown approvals (max 30s)

// 4. TeamDelete with fallback
// SEC-9 FIX: Re-validate team_name before rm -rf (defense-in-depth — team_name was read from config.json)
if (!/^[a-zA-Z0-9_-]+$/.test(team_name)) throw new Error(`Invalid team_name: ${team_name}`)
try { TeamDelete() } catch (e) {
  Bash(`rm -rf ~/.claude/teams/${team_name}/ ~/.claude/tasks/${team_name}/ 2>/dev/null`)
}
```

**When to use**: In ALL cleanup phases — both normal completion and cancellation — where the teammate list may not be statically known. This replaces iterating over a hardcoded array of teammate names.

### Existing Implementations

The cancel commands already use this dynamic discovery pattern:
- `cancel-review.md` — reads `~/.claude/teams/${team_name}/config.json`, iterates `config.members`
- `cancel-audit.md` — same pattern as cancel-review
- `cancel-arc.md` — reads `~/.claude/teams/${phase_team}/config.json`, iterates `teamConfig.members`

These serve as canonical examples of the pattern. All new cleanup logic should follow the same approach.

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
| Phase 1: FORGE | Arc orchestrator (inline since v1.27.1) | `arc-forge-{id}` — ATE-1 compliant |
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

All multi-agent commands: plan.md, work.md, arc.md, mend.md, review.md, audit.md, forge.md, cancel-review.md, cancel-audit.md, cancel-arc.md, plan/references/research-phase.md

Arc phase references (extracted from arc.md): arc-phase-forge.md, arc-phase-plan-review.md, arc-phase-plan-refine.md, arc-phase-work.md, arc-phase-code-review.md, arc-phase-mend.md, arc-phase-audit.md

## Related

- **enforce-teams.sh** (PreToolUse hook): Blocks bare Task calls (without `team_name`) during active Rune workflows. Complements this guard by preventing the _creation_ of teammates outside Agent Teams.

## Notes

- The filesystem fallback (`rm -rf ~/.claude/teams/...`) is safe — these directories only contain Agent SDK coordination state, not user data
- For additional defense-in-depth, commands that delete user-facing directories (e.g., `/rune:rest`) should use `realpath` containment checks in addition to team name validation
- Do not interpolate unsanitized external input into team names — validate first
- Always update workflow state files (e.g., `tmp/.rune-review-{id}.json`) AFTER team cleanup, not before
- The 30s wait is a best-effort grace period — some agents may need longer for complex file writes
- Arc pipelines call TeamCreate/TeamDelete per-phase, so each phase transition needs the pre-create guard
