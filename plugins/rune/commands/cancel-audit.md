---
name: rune:cancel-audit
description: |
  Cancel an active Roundtable Circle audit and gracefully shutdown all Ash teammates.
  Partial results remain in tmp/audit/ for manual inspection.

  <example>
  user: "/rune:cancel-audit"
  assistant: "The Tarnished dismisses the audit Circle..."
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

# /rune:cancel-audit — Cancel Active Audit

Cancel an active Roundtable Circle audit and gracefully shutdown all teammates.

## Steps

### 1. Find Active Audit

```bash
# Find active audit state files, most recent first
ls -t tmp/.rune-audit-*.json 2>/dev/null
```

If no state files found: "No active audit to cancel."

### 2. Select & Read State

Read each state file and filter to active ones. If multiple active audits exist, cancel the most recent:

```javascript
// Read each state file, find most recent active one
const activeStates = stateFiles
  .map(f => ({ path: f, state: Read(f) }))
  .filter(s => s.state.status === "active")
  .sort((a, b) => new Date(b.state.started) - new Date(a.state.started))

if (activeStates.length === 0) {
  return "No active audit to cancel."
}

// Use most recent active audit (sorted by started timestamp)
state = activeStates[0].state
identifier = state.team_name.replace("rune-audit-", "")
if (!/^[a-zA-Z0-9_-]+$/.test(identifier)) { warn("Invalid derived identifier: " + identifier); continue }
team_name = state.team_name

if (activeStates.length > 1) {
  warn(`Multiple active audits found (${activeStates.length}). Cancelling most recent: ${team_name}`)
}
```

### 3. Broadcast Cancellation

```javascript
SendMessage({
  type: "broadcast",
  content: "Audit cancelled by user. Please finish current file and shutdown.",
  summary: "Audit cancelled"
})
```

### 4. Shutdown All Teammates

```javascript
// Read team config to get member list
config = Read(`~/.claude/teams/${team_name}/config.json`)

for (const member of config.members) {
  SendMessage({
    type: "shutdown_request",
    recipient: member.name,
    content: "Audit cancelled by user"
  })
}
```

### 5. Wait for Approvals (Max 30s)

Wait for shutdown responses. After 30 seconds, proceed regardless.

### 6. Cleanup

```javascript
// Delete team with fallback (see team-lifecycle-guard.md)
// Validate team_name before shell interpolation
if (!/^[a-zA-Z0-9_-]+$/.test(team_name)) throw new Error("Invalid team_name")
try { TeamDelete() } catch (e) {
  Bash(`rm -rf ~/.claude/teams/${team_name}/ ~/.claude/tasks/${team_name}/ 2>/dev/null`)
}

// Update state file
Write("tmp/.rune-audit-{identifier}.json", {
  ...state,
  status: "cancelled",
  cancelled_at: new Date().toISOString()
})
```

### 7. Report

```
Audit cancelled.

Partial results (if any) remain in: tmp/audit/{identifier}/
- {list of files that were written before cancellation}

To re-run: /rune:audit
```

## Notes

- Partial results are NOT deleted — they remain for manual inspection
- State file is updated to "cancelled" to prevent conflicts
- Team resources are fully cleaned up
