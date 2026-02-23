---
name: file-todos
description: |
  Structured file-based todo tracking for Rune workflows. Each todo is a markdown
  file with YAML frontmatter and lifecycle status. Source-aware templates adapt for
  review findings, work tasks, PR comments, tech debt, and audit findings.
  Use when creating, triaging, or completing todos from any Rune workflow.

  <example>
  user: "/rune:file-todos status"
  assistant: "Scanning todos/ for current state..."
  </example>

  <example>
  user: "/rune:file-todos create"
  assistant: "Creating new todo with source-aware template..."
  </example>
user-invocable: true
disable-model-invocation: false
argument-hint: "[create|triage|status|list|next|search|archive] [--status=pending] [--priority=p1] [--source=review]"
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
  - AskUserQuestion
---

# File-Todos — Structured File-Based Todo Tracking

Persistent, source-aware todo tracking across all Rune workflows. Each todo is a standalone markdown file in `todos/` with YAML frontmatter for structured metadata and lifecycle tracking.

## Architecture

### Directory Structure

Todos are organized into per-source subdirectories under the base directory:

```
todos/
├── work/                                     # source: work (from strive)
│   ├── 001-ready-p2-implement-auth-flow.md
│   └── 002-ready-p3-add-validation.md
├── review/                                   # source: review (from appraise)
│   ├── 001-pending-p1-fix-sql-injection.md
│   └── 002-pending-p2-missing-docs.md
├── audit/                                    # source: audit (from audit)
│   └── 001-pending-p3-dead-code.md
└── archive/                                  # completed todos (via archive command)
    └── review-003-complete-p2-old-finding.md # source prefix preserved
```

**ID sequences are per-subdirectory** — `work/001-*` and `review/001-*` are independent.

### File Naming Convention

```
{issue_id}-{status}-{priority}-{slug}.md
```

| Component | Format | Values |
|-----------|--------|--------|
| `issue_id` | 3-digit padded | `001`, `002`, ... `999` |
| `status` | lowercase | `pending`, `ready`, `complete` |
| `priority` | lowercase | `p1` (critical), `p2` (important), `p3` (nice-to-have) |
| `slug` | kebab-case | Max 40 chars, derived from title |

**Option A (CRITICAL)**: Filename encodes INITIAL status only. Files are NEVER renamed on status transition. The frontmatter `status` field is authoritative. The `in_progress` status exists only in frontmatter, never in the filename.

### Slug Algorithm

The slug algorithm MUST be identical everywhere it is used (orchestrator, workers, integrations):

```
slugify(s):
  1. Convert to lowercase
  2. Replace all non-alphanumeric sequences with a single hyphen
  3. Trim leading/trailing hyphens
  4. Truncate to 40 characters

  Regex: s.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 40)
```

### ID Generation

Sequential 3-digit padded IDs, **independent per source subdirectory**. Use zsh-safe glob for counting existing files:

```bash
# zsh-safe: (N) prevents NOMATCH error on empty directory
# source = "work" | "review" | "audit"
existing=(todos/${source}/[0-9][0-9][0-9]-*.md(N))
next_id=$(printf "%03d" $(( ${#existing[@]} + 1 )))
```

This means `work/001-*` and `review/001-*` are independent sequences.

**Sole-orchestrator pattern**: Only the orchestrator creates todo files. Workers send completion signals; the orchestrator writes. This eliminates TOCTOU race conditions in ID generation.

## YAML Frontmatter Schema

```yaml
---
schema_version: 1
status: pending           # pending | ready | in_progress | complete | blocked | wont_fix
priority: p1              # p1 (critical) | p2 (important) | p3 (nice-to-have)
issue_id: "001"
source: review            # review | work | pr-comment | tech-debt | audit
source_ref: ""            # path or reference back to origin
finding_id: ""            # RUNE:FINDING id (for review/audit sources)
finding_severity: ""      # P1/P2/P3 (for display without re-parsing)
tags: []
dependencies: []          # issue IDs this is blocked by
files: []                 # affected files (from source)
assigned_to: null         # worker claim tracking
work_session: ""          # session correlation for stale detection
created: "YYYY-MM-DD"
updated: "YYYY-MM-DD"
---
```

**Status lifecycle** (full):

```
pending --> ready --> in_progress --> complete
  |           |           |
  |           |           +--> blocked
  |           |
  +-----------+---------------> wont_fix
```

- `pending` — Created, awaiting triage
- `ready` — Triaged and approved for work
- `in_progress` — Actively being worked on (frontmatter-only, NEVER in filename)
- `complete` — Work finished, acceptance criteria met
- `blocked` — Blocked by dependencies
- `wont_fix` — Triaged and rejected

## Opt-In Toggle

File-todos require explicit opt-in via talisman configuration:

```yaml
# .claude/talisman.yml
file_todos:
  enabled: true              # MUST be === true to activate (opt-in)
  dir: "todos/"              # relative to project root
  auto_generate:
    review: false            # default false — opt-in for safety
    audit: false             # default false
    work: false              # default false
  triage:
    auto_approve_p1: false   # auto-approve P1 findings (skip triage)
```

**Check**: `talisman.file_todos.enabled === true` (NOT `!== false`).

## .gitignore Conflict

The Rune `.gitignore` (line 21) ignores `todos/`. This conflicts with persistent file-todos. To persist todos in version control, users must manually remove or comment out the `todos/` line in `.gitignore`. This follows the same opt-in pattern as Rune Echoes (see README.md).

## Sub-Command Dispatch

Route sub-commands via `$ARGUMENTS`. Parse the first argument as the sub-command name. See [subcommands.md](references/subcommands.md) for full implementation details, validation patterns, and helper functions.

```javascript
const args = "$ARGUMENTS".trim()
const subcommand = args.split(/\s+/)[0] || ""
const restArgs = args.slice(subcommand.length).trim()

switch (subcommand) {
  case "create":  // -> create workflow
  case "triage":  // -> triage workflow
  case "status":  // -> status report
  case "list":    // -> filtered listing
  case "next":    // -> next ready todo
  case "search":  // -> full-text search
  case "archive": // -> archive completed
  default:        // -> show usage help
}
```

### Validation Patterns

All user-supplied filter values MUST be validated before use. Invalid values produce a clear error message, NOT an empty list.

```
STATUS_PATTERN  = /^(pending|ready|in_progress|complete|blocked|wont_fix)$/
PRIORITY_PATTERN = /^p[1-3]$/
SOURCE_PATTERN  = /^(review|work|pr-comment|tech-debt|audit)$/
TAG_PATTERN     = /^[a-zA-Z0-9_-]+$/
TODO_ID_PATTERN = /^[0-9]{3,4}$/
```

## Sub-Commands

### create — Interactive Todo Creation

```
/rune:file-todos create
```

1. Prompt for title/priority/source/files via AskUserQuestion (source selection determines subdirectory)
2. Ensure source subdirectory exists: `mkdir -p todos/{source}/`
3. Generate next sequential ID from source subdirectory (zsh-safe `(N)` glob, per-subdirectory sequence)
4. Compute slug, write file using [todo-template.md](references/todo-template.md)
5. Report: "Created `todos/{source}/{filename}`"

**Zero-state**: Auto-creates `todos/{source}/` if missing.

### triage — Batch Triage Pending Items

```
/rune:file-todos triage
```

Scan all source subdirectories (`todos/*/[0-9][0-9][0-9]-*.md`). Process pending todos sorted by priority (P1 first), capped at 10 per session. See [triage-protocol.md](references/triage-protocol.md) for the full workflow.

Options per item: Approve (ready), Defer (keep pending), Reject (wont_fix), Reprioritize.

If `talisman.file_todos.triage.auto_approve_p1 === true`, P1 items auto-approve.

**Zero-state**: "No pending todos found. All items have been triaged."

### status — Summary Report

```
/rune:file-todos status
```

Scan all source subdirectories (`todos/*/[0-9][0-9][0-9]-*.md`) and display counts grouped by source subdirectory, status, and priority. Output is PLAIN TEXT with no emoji.

```
File-Todos Status
------------------------------
 Pending:     3 (needs triage)
 Ready:       5 (approved)
 In Progress: 2 (active)
 Complete:    12 (done)
 Blocked:     1
 Wont Fix:    0
------------------------------
 P1:  2 pending, 1 ready
 P2:  1 pending, 3 ready
 P3:  0 pending, 1 ready
------------------------------
 By Source Subdirectory:
   work/       7 (4 complete, 2 ready, 1 in_progress)
   review/     8 (5 complete, 2 pending, 1 blocked)
   audit/      3 (2 pending, 1 complete)
   pr-comment/ 2 (1 complete, 1 pending)
------------------------------
```

**Scan pattern**: `Glob(\`${base}*/[0-9][0-9][0-9]-*.md\`)` where `base` is `resolveTodosBase($ARGUMENTS, talisman)`. Only scans the project-level `todos/` base — NOT `tmp/arc/*/todos/` (arc todos are ephemeral and excluded from CLI).

**Zero-state**: "No todos found. Run `/rune:file-todos create` or enable `file_todos.auto_generate` in talisman.yml."

### list — Filtered Listing

```
/rune:file-todos list [--status=pending] [--priority=p1] [--source=review] [--tags=security,api]
```

Scans all source subdirectories (`todos/*/[0-9][0-9][0-9]-*.md`). Filters compose as intersection. The `--source` filter restricts to a specific subdirectory (e.g., `--source=review` scans only `todos/review/`). Invalid filter values produce a clear error, not an empty list. Sort: priority (P1 first), then issue_id ascending. See [subcommands.md](references/subcommands.md) for filter parsing and intersection logic.

**Zero-state**: "No todos match the given filters." or "No todos found."

### next — Highest Priority Unblocked Ready Todo

```
/rune:file-todos next [--auto]
```

Scans all source subdirectories (`todos/*/[0-9][0-9][0-9]-*.md`). Show highest-priority unblocked todo with `status: ready` and no `assigned_to`. Checks `dependencies` against non-complete todos.

**`--auto` flag**: Output JSON, claim atomically via lockfile guard (temp-file-then-rename, NOT flock). Sets `assigned_to`, `claimed_at`, `status: in_progress` in frontmatter. See [subcommands.md](references/subcommands.md) for atomic claim protocol.

**Zero-state distinctions**:
- No todos at all: "No todos found."
- All complete: "All todos are complete."
- All claimed: "All ready todos are assigned. Check in-progress items."
- None ready: "No ready todos. Run `/rune:file-todos triage` to approve pending items."
- All blocked: "All ready todos are blocked by unresolved dependencies."

### search — Full-Text Search

```
/rune:file-todos search <query>
```

Case-insensitive search across all source subdirectories (`todos/*/[0-9][0-9][0-9]-*.md`). Searches todo titles, problem statements, and work logs. Validates query length (2-200 chars), sanitizes regex metacharacters before Grep. Results grouped by file with metadata, showing source subdirectory. See [subcommands.md](references/subcommands.md) for sanitization and display details.

**Zero-state**: "No matches found for '{query}' in todos/."

### archive — Move Completed Todos

```
/rune:file-todos archive [--all] [--id=NNN] [--source=review]
```

Scan all source subdirectories for `status: complete` and `status: wont_fix` todos. Move to `todos/archive/` with source prefix preserved in the filename: `review/003-*.md` becomes `archive/review-003-*.md`. Supports `--all` (batch, no confirmation), `--id=NNN` (specific, with confirmation), `--source` (filter to one subdirectory), or interactive confirmation. Uses `mv` (atomic on same filesystem). Marks index dirty for cache rebuild. See [subcommands.md](references/subcommands.md) for full protocol.

**Zero-state**: "No completed or rejected todos to archive."

## Performance: Todo Index Cache

For projects with >100 todos, `.todo-index.json` cache avoids re-parsing all frontmatter. Cache rebuild glob scans all subdirectories: `todos/*/[0-9][0-9][0-9]-*.md(N)`. Dirty-signal invalidation: any modifying sub-command writes `todos/.dirty`; next read rebuilds via temp-file-then-rename (atomic). Cache is optional — fallback to direct parsing on missing or corrupt cache. See [subcommands.md](references/subcommands.md) for cache schema and rebuild protocol.

## Integration Points

| Trigger | Flow | Source | Reference |
|---------|------|--------|-----------|
| `/rune:appraise` | TOME findings -> per-finding todos | `review` | [integration-guide.md](references/integration-guide.md) |
| `/rune:audit` | TOME findings -> per-finding todos | `audit` | [integration-guide.md](references/integration-guide.md) |
| `/rune:strive` | Plan tasks -> per-task todos | `work` | [integration-guide.md](references/integration-guide.md) |
| `/rune:mend` | Resolution tracking -> todo updates | updates existing | [integration-guide.md](references/integration-guide.md) |
| PR comments | gh API -> per-comment todos | `pr-comment` | [integration-guide.md](references/integration-guide.md) |

## Concurrent Access

| Operation | Who Can Perform | Safe? |
|-----------|----------------|-------|
| Create todo (Write) | Orchestrator only | Yes — single writer |
| Read todo (Read) | Anyone | Yes — reads are safe |
| Append Work Log (Edit) | Worker assigned to task only | Yes — one worker per task |
| Update frontmatter status | Orchestrator or mend-fixer | Conditional — needs claim lock |
| Delete / archive | Orchestrator (cleanup phase) only | Yes — after all workflows complete |

## References

- [todo-template.md](references/todo-template.md) — Source-aware todo template with YAML frontmatter schema
- [lifecycle.md](references/lifecycle.md) — Status transitions and lifecycle rules
- [triage-protocol.md](references/triage-protocol.md) — Batch triage workflow for pending items
- [integration-guide.md](references/integration-guide.md) — How each Rune workflow feeds/consumes todos
- [subcommands.md](references/subcommands.md) — Full sub-command implementation details, helpers, and cache protocol
