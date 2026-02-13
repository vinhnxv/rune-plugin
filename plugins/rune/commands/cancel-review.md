---
name: rune:cancel-review
description: |
  Cancel an active Roundtable Circle review and gracefully shutdown all Ash teammates.
  Partial results remain in tmp/reviews/ for manual inspection.

  <example>
  user: "/rune:cancel-review"
  assistant: "The Tarnished dismisses the Roundtable Circle..."
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
  - AskUserQuestion
---

# /rune:cancel-review — Cancel Active Review

Cancel an active Roundtable Circle review and gracefully shutdown all teammates.

## Steps

### 1. Find Active Review

```bash
# Find active review state files, most recent first
ls -t tmp/.rune-review-*.json 2>/dev/null
```

If no state files found: "No active review to cancel."

### 2. Select & Read State

Read each state file and filter to active ones. If multiple active reviews exist, let the user choose which to cancel:

```javascript
// Read each state file, find active ones
const activeStates = stateFiles
  .map(f => ({ path: f, state: Read(f) }))
  .filter(s => s.state.status === "active")
  .sort((a, b) => new Date(b.state.started) - new Date(a.state.started))

if (activeStates.length === 0) {
  return "No active review to cancel."
}

let state, identifier, team_name

if (activeStates.length === 1) {
  // Single active review — auto-select
  state = activeStates[0].state
  identifier = state.team_name.replace("rune-review-", "")
  if (!/^[a-zA-Z0-9_-]+$/.test(identifier)) { warn("Invalid derived identifier: " + identifier); return }
  team_name = state.team_name
} else {
  // Multiple active — ask user which to cancel
  const choice = AskUserQuestion({
    questions: [{
      question: `Multiple active reviews found (${activeStates.length}). Which to cancel?`,
      header: "Session",
      options: activeStates.map(s => ({
        label: s.state.team_name,
        description: `Started: ${s.state.started}, Files: ${s.state.expected_files?.length || '?'}`
      })),
      multiSelect: false
    }]
  })
  const selected = activeStates.find(s => s.state.team_name === choice)
  state = selected.state
  identifier = state.team_name.replace("rune-review-", "")
  if (!/^[a-zA-Z0-9_-]+$/.test(identifier)) { warn("Invalid derived identifier: " + identifier); return }
  team_name = state.team_name
}
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

// NOTE: identifier is derived from team_name via .replace("rune-review-", "").
// The team_name regex guard above implicitly validates identifier (it's a substring).

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
