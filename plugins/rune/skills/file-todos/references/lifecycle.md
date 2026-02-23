# Todo Lifecycle — Status Transitions

## Status Definitions

| Status | Meaning | In Filename? | In Frontmatter? |
|--------|---------|:------------:|:---------------:|
| `pending` | Created, awaiting triage | Yes (initial) | Yes |
| `ready` | Triaged and approved for work | Yes (initial) | Yes |
| `in_progress` | Actively being worked on | NEVER | Yes |
| `complete` | Work finished, criteria met | Yes (initial, rare) | Yes |
| `blocked` | Blocked by dependencies | NEVER | Yes |
| `wont_fix` | Rejected during triage | NEVER | Yes |

## Transition Diagram

```
                    ┌──────────────┐
                    │   pending    │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
              ▼            │            ▼
      ┌──────────────┐    │    ┌──────────────┐
      │    ready      │    │    │   wont_fix   │
      └──────┬───────┘    │    └──────────────┘
             │            │
             ▼            │
      ┌──────────────┐    │
      │ in_progress  │    │
      └──────┬───────┘    │
             │            │
        ┌────┼────┐       │
        │         │       │
        ▼         ▼       │
┌────────────┐ ┌────────────┐
│  complete  │ │  blocked   │
└────────────┘ └─────┬──────┘
                     │
                     ▼ (when unblocked)
              ┌──────────────┐
              │ in_progress  │
              └──────────────┘
```

## Transition Rules

### Valid Transitions

| From | To | Triggered By | Action |
|------|----|-------------|--------|
| `pending` | `ready` | Triage approval | Edit frontmatter `status: ready` |
| `pending` | `wont_fix` | Triage rejection | Edit frontmatter `status: wont_fix` |
| `ready` | `in_progress` | Worker claims todo | Edit frontmatter `status: in_progress`, set `assigned_to` |
| `in_progress` | `complete` | Worker finishes | Edit frontmatter `status: complete`, add Work Log |
| `in_progress` | `blocked` | Dependency found | Edit frontmatter `status: blocked`, add to `dependencies` |
| `blocked` | `in_progress` | Dependency resolved | Edit frontmatter `status: in_progress` |
| `pending` | `complete` | Direct resolution (e.g., mend) | Edit frontmatter `status: complete` |

### Invalid Transitions

- `complete` to any other status (final state)
- `wont_fix` to any other status (final state)
- Any status directly to `in_progress` without `assigned_to` being set

## Option A: No File Renames

Filenames encode the INITIAL status at creation time. Files are NEVER renamed when status changes.

**Why**: Renaming files during status transitions creates race conditions when multiple agents read/write concurrently. With Option A, filenames are stable references that never change.

**The frontmatter `status` field is authoritative.** When reading todo status, always parse frontmatter — never infer status from the filename.

**Example**: A file named `001-pending-p1-fix-injection.md` may have frontmatter `status: complete` after being resolved by mend. The filename still says `pending` but the authoritative status is `complete`.

## Status Queries

To find todos by current status, parse frontmatter:

```bash
# Find all in-progress todos (zsh-safe)
for f in todos/*/[0-9][0-9][0-9]-*.md(N); do
  if grep -q '^status: in_progress' "$f"; then
    echo "$f"
  fi
done
```

Do NOT use filename patterns to determine current status. The filename is a creation-time artifact only.

## Stale Detection

Todos can become stale when:

1. **Orphaned work session**: `work_session` references a session that no longer exists
2. **Long-running in_progress**: No Work Log updates for extended period
3. **Unresolved blocked**: Dependencies never resolved

**Prevention**: Include `work_session` in frontmatter for session correlation. Cleanup logic should scope to the current session only — do not modify todos from other sessions.

## Idempotency

Re-running a workflow that generates todos (e.g., re-running review on the same TOME) must not create duplicates. Before creating a todo:

1. Check for existing todo with matching `finding_id` + `source_ref`
2. If match found, skip creation
3. If no match, create new todo with next sequential ID

## Cleanup

Completed and wont_fix todos accumulate over time. Cleanup options:

- **Archive**: Move to `todos/archive/` (manual or via future sub-command)
- **Delete**: Remove completed todos (manual only, with confirmation)
- **Leave**: Keep all todos for historical reference

Cleanup is always manual or orchestrator-initiated, never automatic.
