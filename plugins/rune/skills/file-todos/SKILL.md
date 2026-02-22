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
argument-hint: "[create|triage|status|list|next] [--status=pending] [--priority=p1] [--source=review]"
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

```
todos/
├── 001-pending-p1-fix-sql-injection.md      # source: review
├── 002-ready-p2-implement-auth-flow.md      # source: work
├── 003-pending-p2-update-api-docs.md        # source: pr-comment
├── 004-pending-p1-add-input-validation.md   # source: audit
└── 005-complete-p3-clean-up-imports.md      # source: tech-debt
```

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

Sequential 3-digit padded IDs. Use zsh-safe glob for counting existing files:

```bash
# zsh-safe: (N) prevents NOMATCH error on empty directory
existing=(todos/[0-9][0-9][0-9]-*.md(N))
next_id=$(printf "%03d" $(( ${#existing[@]} + 1 )))
```

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
pending ──► ready ──► in_progress ──► complete
  │           │           │
  │           │           └──► blocked
  │           │
  └───────────┴──────────────► wont_fix
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

## Sub-Commands

Dispatch via `$ARGUMENTS`:

### create — Interactive Todo Creation

```
/rune:file-todos create
```

1. Ask for title, priority, source, and affected files
2. Generate next sequential ID
3. Compute slug from title
4. Write file using [todo-template.md](references/todo-template.md)
5. Report: created `todos/{filename}`

### triage — Batch Triage Pending Items

```
/rune:file-todos triage
```

Process pending todos in batch (capped at 10 per session). See [triage-protocol.md](references/triage-protocol.md) for the full workflow.

### status — Summary Report

```
/rune:file-todos status
```

Scan `todos/` and display counts by status, priority, and source. Output is PLAIN TEXT with no emoji (Rune convention).

**Output format:**

```
File-Todos Status
─────────────────────────
 Pending:     3 (needs triage)
 Ready:       5 (approved)
 In Progress: 2 (active)
 Complete:    12 (done)
 Blocked:     1
 Wont Fix:    0
─────────────────────────
 P1:  2 pending, 1 ready
 P2:  1 pending, 3 ready
 P3:  0 pending, 1 ready
─────────────────────────
 By Source:
   review:     8 (5 complete)
   work:       7 (4 complete)
   pr-comment: 3 (2 complete)
   tech-debt:  2 (1 complete)
```

**Zero-state**: "No todos found. Run `/rune:file-todos create` or enable `file_todos.auto_generate` in talisman.yml."

### list — Filtered Listing

```
/rune:file-todos list [--status=pending] [--priority=p1] [--source=review]
```

List todos with optional filters. Filters compose as intersection. Invalid filter values produce a clear error, not an empty list.

**Validation patterns:**

```
STATUS_PATTERN  = /^(pending|ready|in_progress|complete|blocked|wont_fix)$/
PRIORITY_PATTERN = /^p[1-3]$/
SOURCE_PATTERN  = /^(review|work|pr-comment|tech-debt|audit)$/
TAG_PATTERN     = /^[a-zA-Z0-9_-]+$/
TODO_ID_PATTERN = /^[0-9]{3,4}$/
```

### next — Highest Priority Unblocked Ready Todo

```
/rune:file-todos next
```

Show the highest-priority unblocked todo with status `ready`. Reads frontmatter to check dependencies.

**Zero-state distinctions:**
- No todos at all: "No todos found."
- All complete: "All todos are complete."
- All claimed: "All ready todos are assigned."
- None ready: "No ready todos. Run `/rune:file-todos triage` to approve pending items."

## Integration Points

| Trigger | Flow | Source | Reference |
|---------|------|--------|-----------|
| `/rune:appraise` | TOME findings → per-finding todos | `review` | [integration-guide.md](references/integration-guide.md) |
| `/rune:audit` | TOME findings → per-finding todos | `audit` | [integration-guide.md](references/integration-guide.md) |
| `/rune:strive` | Plan tasks → per-task todos | `work` | [integration-guide.md](references/integration-guide.md) |
| `/rune:mend` | Resolution tracking → todo updates | updates existing | [integration-guide.md](references/integration-guide.md) |
| PR comments | gh API → per-comment todos | `pr-comment` | [integration-guide.md](references/integration-guide.md) |

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
