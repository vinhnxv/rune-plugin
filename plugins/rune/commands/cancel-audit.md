---
name: rune:cancel-audit
description: |
  Cancel an active Roundtable Circle audit and gracefully shutdown all Tarnished teammates.
  Partial results remain in tmp/audit/ for manual inspection.

  <example>
  user: "/rune:cancel-audit"
  assistant: "The Elden Lord dismisses the audit Circle..."
  </example>
user-invocable: true
allowed-tools:
  - Task
  - TaskCreate
  - TaskList
  - TaskUpdate
  - TaskGet
  - TeamCreate
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
# Find active audit state files
ls tmp/.rune-audit-*.json 2>/dev/null
```

If no active audit found: "No active audit to cancel."

### 2. Read State

```javascript
state = Read("tmp/.rune-audit-{identifier}.json")
team_name = state.team_name
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
