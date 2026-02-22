---
name: file-todos
description: |
  Manage file-based todos — create, triage, list, search, archive, and track
  structured todo files in todos/ with YAML frontmatter and source-aware templates.

  <example>
  user: "/rune:file-todos status"
  assistant: "Scanning todos/ for current state..."
  </example>

  <example>
  user: "/rune:file-todos create"
  assistant: "Creating new todo with source-aware template..."
  </example>
user-invocable: true
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
  - AskUserQuestion
argument-hint: "[create|triage|status|list|next|search|archive] [--status=pending] [--priority=p1] [--source=review]"
---

# /rune:file-todos — Manage File-Based Todos

Manage structured file-based todos in `todos/`.

## Usage

```
/rune:file-todos create             # Interactive todo creation
/rune:file-todos triage             # Batch triage pending items
/rune:file-todos status             # Summary: counts by status, priority, source
/rune:file-todos list [--status=pending] [--priority=p1] [--source=review]
/rune:file-todos next [--auto]      # Highest-priority unblocked ready todo
/rune:file-todos search <query>     # Full-text search across titles and notes
/rune:file-todos archive [--all]    # Move completed todos to todos/archive/
```

**Load skills**: `file-todos` for full reference.

## Subcommands

### create — Interactive Todo Creation

1. Ask for title, priority, source, affected files
2. Generate next sequential ID (zsh-safe)
3. Compute slug from title
4. Write file using todo template
5. Report created file path

### triage — Batch Triage Pending Items

Process pending todos sorted by priority (P1 first). Capped at 10 per session.

Options per item:
- Approve (pending -> ready)
- Defer (keep pending)
- Reject (mark wont_fix)
- Reprioritize (change priority)

### status — Summary Report

Scan `todos/` and display counts by status, priority, and source. Plain text output (no emoji).

### list — Filtered Listing

List todos with optional filters. Filters compose as intersection. Invalid filter values produce a clear error, not an empty list.

### next — Next Ready Todo

Show highest-priority unblocked todo with `status: ready`. Use `--auto` for JSON output with atomic claim for programmatic use by workers.

### search — Full-Text Search

Search across todo titles, problem statements, and work logs. Case-insensitive. Results grouped by file with context lines.

### archive — Move Completed Todos

Move completed and wont_fix todos to `todos/archive/`. Supports `--all` for batch archive or `--id=NNN` for specific todo. Requires confirmation unless `--all` is specified.
