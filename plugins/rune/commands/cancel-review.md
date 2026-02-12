---
name: rune:cancel-review
description: |
  Cancel an active Roundtable Circle review and gracefully shutdown all Runebearer teammates.
  Partial results remain in tmp/reviews/ for manual inspection.

  <example>
  user: "/rune:cancel-review"
  assistant: "Cancelling active review and shutting down Runebearers..."
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

# /rune:cancel-review — Cancel Active Review

Cancel an active Roundtable Circle review and gracefully shutdown all teammates.

## Steps

### 1. Find Active Review

```bash
# Find active review state files
ls tmp/.rune-review-*.json 2>/dev/null
```

If no active review found: "No active review to cancel."

### 2. Read State

```javascript
state = Read("tmp/.rune-review-{identifier}.json")
team_name = state.team_name
```

### 3. Broadcast Cancellation

```javascript
SendMessage({
  type: "broadcast",
  content: "Review cancelled by user. Please finish current file and shutdown.",
  summary: "Review cancelled"
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
    content: "Review cancelled by user"
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
Write("tmp/.rune-review-{identifier}.json", {
  ...state,
  status: "cancelled",
  cancelled_at: new Date().toISOString()
})
```

### 7. Report

```
Review cancelled.

Partial results (if any) remain in: tmp/reviews/{identifier}/
- {list of files that were written before cancellation}

To re-run: /rune:review
```

## Notes

- Partial results are NOT deleted — they remain for manual inspection
- State file is updated to "cancelled" to prevent conflicts
- Team resources are fully cleaned up
