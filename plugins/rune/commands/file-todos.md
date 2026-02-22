---
name: rune:file-todos
description: |
  Manage file-based todos — create, triage, list, and track structured todo files
  in todos/ with YAML frontmatter and source-aware templates.

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
---

# /rune:file-todos — Manage File-Based Todos

Manage structured file-based todos in `todos/`.

## Usage

```
/rune:file-todos create             # Interactive todo creation
/rune:file-todos triage             # Batch triage pending items
/rune:file-todos status             # Summary: counts by status, priority, source
/rune:file-todos list [--status=pending] [--priority=p1] [--source=review]
/rune:file-todos next               # Highest-priority unblocked ready todo
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

Scan `todos/` and display counts by status, priority, and source. Plain text output.

### list — Filtered Listing

List todos with optional filters. Filters compose as intersection.

### next — Next Ready Todo

Show highest-priority unblocked todo with `status: ready`.
