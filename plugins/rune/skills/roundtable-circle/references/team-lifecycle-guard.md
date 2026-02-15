# Team Lifecycle Guard

Canonical reference for the pre-create guard and cleanup fallback patterns used across all Rune multi-agent commands. Every command that creates an Agent Team MUST follow these patterns.

## Pre-Create Guard

Before `TeamCreate`, clean up stale teams from crashed prior sessions:

```javascript
// 1. Validate identifier (REQUIRED — this is the ONLY barrier against path traversal)
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
