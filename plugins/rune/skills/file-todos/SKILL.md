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

```
todos/
├── 001-pending-p1-fix-sql-injection.md      # source: review
├── 002-ready-p2-implement-auth-flow.md      # source: work
├── 003-pending-p2-update-api-docs.md        # source: pr-comment
├── 004-pending-p1-add-input-validation.md   # source: audit
├── 005-complete-p3-clean-up-imports.md      # source: tech-debt
└── archive/                                  # completed todos (via archive command)
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

Route sub-commands via `$ARGUMENTS`. Parse the first argument as the sub-command name.

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

All user-supplied filter values MUST be validated before use:

```
STATUS_PATTERN  = /^(pending|ready|in_progress|complete|blocked|wont_fix)$/
PRIORITY_PATTERN = /^p[1-3]$/
SOURCE_PATTERN  = /^(review|work|pr-comment|tech-debt|audit)$/
TAG_PATTERN     = /^[a-zA-Z0-9_-]+$/
TODO_ID_PATTERN = /^[0-9]{3,4}$/
```

Invalid values produce a clear error message, NOT an empty list.

### Common Helpers

**parseFrontmatter(content)**: Extract YAML frontmatter from todo file content. Returns object with all frontmatter fields. Matches `^---\n([\s\S]*?)\n---` at the start of the file.

**readTodoDir()**: Scan `todos/` for todo files. Returns list of `{ path, frontmatter, title }` objects. Uses zsh-safe glob `(N)` qualifier:

```bash
for f in todos/[0-9][0-9][0-9]-*.md(N); do
  # parse frontmatter from each file
done
```

**ensureTodosDir()**: Create `todos/` directory if it does not exist:

```bash
mkdir -p todos
```

**getTitle(content)**: Extract the first H1 heading from the markdown body (after frontmatter).

## Sub-Commands

### create — Interactive Todo Creation

```
/rune:file-todos create
```

Interactive workflow for creating a new todo file.

**Steps**:

1. Ensure `todos/` directory exists (create if missing)
2. Prompt user for todo details via AskUserQuestion:

```javascript
AskUserQuestion({
  questions: [
    {
      question: "Todo title (brief description of the issue or task)",
      header: "Title"
    },
    {
      question: "Priority level",
      header: "Priority",
      options: [
        { label: "P1 — Critical", description: "Blocking issue, security vulnerability, data loss risk" },
        { label: "P2 — Important", description: "Significant bug, performance issue, missing feature" },
        { label: "P3 — Nice to have", description: "Cosmetic issue, minor improvement, tech debt" }
      ],
      multiSelect: false
    },
    {
      question: "Source of this todo",
      header: "Source",
      options: [
        { label: "review", description: "From code review TOME finding" },
        { label: "work", description: "From implementation plan task" },
        { label: "pr-comment", description: "From PR comment" },
        { label: "tech-debt", description: "Technical debt observation" },
        { label: "audit", description: "From audit TOME finding" }
      ],
      multiSelect: false
    },
    {
      question: "Affected files (comma-separated paths, or leave empty)",
      header: "Files"
    }
  ]
})
```

3. Generate next sequential ID:

```bash
existing=(todos/[0-9][0-9][0-9]-*.md(N))
next_id=$(printf "%03d" $(( ${#existing[@]} + 1 )))
```

4. Compute slug from title using the canonical slugify algorithm
5. Write file using [todo-template.md](references/todo-template.md)
6. Set frontmatter fields: `status: pending`, `priority`, `source`, `files`, `created`, `updated` (today's date)
7. Report: "Created `todos/{filename}`"

**Zero-state**: If `todos/` does not exist, create it automatically and report the creation.

### triage — Batch Triage Pending Items

```
/rune:file-todos triage
```

Process pending todos in batch (capped at 10 per session). See [triage-protocol.md](references/triage-protocol.md) for the full workflow.

**Steps**:

1. Scan `todos/` for all todo files
2. Filter to `status: pending` (from frontmatter, NOT filename)
3. Sort by priority (P1 first), then by `issue_id` (oldest first)
4. If `talisman.file_todos.triage.auto_approve_p1 === true`:
   - Auto-approve all P1 pending todos (set `status: ready`, update `updated` date)
   - Report auto-approved count separately
5. Cap remaining items at 10
6. For each pending todo, present via AskUserQuestion:

```javascript
AskUserQuestion({
  questions: [{
    question: `Todo #${fm.issue_id} [${fm.priority}] -- ${title}\nSource: ${fm.source} | Files: ${fm.files.length} | Created: ${fm.created}`,
    header: "Triage Decision",
    options: [
      { label: "Approve", description: "Move to ready -- available for work" },
      { label: "Defer", description: "Keep pending -- revisit later" },
      { label: "Reject", description: "Mark wont_fix -- not worth pursuing" },
      { label: "Reprioritize", description: "Change priority level" }
    ],
    multiSelect: false
  }]
})
```

7. Apply each decision:
   - Approve: Edit frontmatter `status: ready`, update `updated`
   - Defer: No changes
   - Reject: Edit frontmatter `status: wont_fix`, update `updated`, add Work Log rejection entry
   - Reprioritize: Prompt for new priority, edit `priority` field, update `updated`
8. Report summary (plain text, no emoji):

```
Triage Complete
------------------------------
 Approved:      4 (moved to ready)
 Deferred:      2 (kept pending)
 Rejected:      1 (marked wont_fix)
 Reprioritized: 1 (priority changed)
------------------------------
 Remaining pending: 3
```

**Zero-state**: "No pending todos found. All items have been triaged."

### status — Summary Report

```
/rune:file-todos status
```

Scan `todos/` and display counts by status, priority, and source. Output is PLAIN TEXT with no emoji (Rune convention).

**Steps**:

1. Scan `todos/` for all `[0-9][0-9][0-9]-*.md(N)` files
2. Parse frontmatter from each file to read authoritative `status`, `priority`, `source`
3. Count by status, priority-per-status, and source
4. Display:

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
 By Source:
   review:     8 (5 complete)
   work:       7 (4 complete)
   pr-comment: 3 (2 complete)
   tech-debt:  2 (1 complete)
```

**Zero-state**: "No todos found. Run `/rune:file-todos create` or enable `file_todos.auto_generate` in talisman.yml."

### list — Filtered Listing

```
/rune:file-todos list [--status=pending] [--priority=p1] [--source=review] [--tags=security,api]
```

List todos with optional filters. Filters compose as intersection (all conditions must match).

**Steps**:

1. Parse filter flags from `restArgs`:
   - `--status=VALUE` — validate against `STATUS_PATTERN`
   - `--priority=VALUE` — validate against `PRIORITY_PATTERN`
   - `--source=VALUE` — validate against `SOURCE_PATTERN`
   - `--tags=VALUE[,VALUE]` — validate each tag against `TAG_PATTERN`

2. If any filter value is invalid, report a clear error:
   ```
   Invalid filter: --priority=P5
   Valid values: p1, p2, p3
   ```
   Do NOT return an empty list for invalid filters.

3. Scan `todos/` and parse frontmatter from each file

4. Apply filters as intersection:
   ```javascript
   const matches = todos.filter(t =>
     (!statusFilter || t.frontmatter.status === statusFilter) &&
     (!priorityFilter || t.frontmatter.priority === priorityFilter) &&
     (!sourceFilter || t.frontmatter.source === sourceFilter) &&
     (!tagsFilter || tagsFilter.every(tag => (t.frontmatter.tags || []).includes(tag)))
   )
   ```

5. Sort results: priority (P1 first), then issue_id ascending

6. Display results table (plain text):

```
File-Todos List (filter: status=pending, priority=p1)
-----------------------------------------------------
 #001 [P1] fix-sql-injection          pending   review
 #004 [P1] add-input-validation       pending   audit
-----------------------------------------------------
 2 todos found
```

**Zero-state**: "No todos match the given filters." (when todos exist but none match) or "No todos found." (when `todos/` is empty or missing).

### next — Highest Priority Unblocked Ready Todo

```
/rune:file-todos next [--auto]
```

Show the highest-priority unblocked todo with `status: ready`. Reads frontmatter to check dependencies and assignment.

**Steps**:

1. Scan `todos/` and parse frontmatter
2. Filter to `status: ready` AND `assigned_to` is null or empty (not yet claimed)
3. Check dependencies: exclude todos whose `dependencies` list contains IDs of non-complete todos
4. Sort by priority (P1 first), then issue_id (oldest first)
5. Display the top result:

```
Next Todo
------------------------------
 #002 [P2] implement-auth-flow
 Source: work | Files: 3 | Created: 2026-02-20

 Problem: Authentication flow needs to be implemented for the
 new user registration endpoint...

 Proposed: See Option 1 in todo file
------------------------------
 File: todos/002-ready-p2-implement-auth-flow.md
```

**`--auto` flag** (programmatic use by workers):

When `--auto` is passed, output JSON instead of human-readable text. Also claim the todo atomically:

1. Acquire lock via temp-file-then-rename (atomic on POSIX):
   ```bash
   lockfile="todos/.lock"
   tmplock="todos/.lock.$$"
   echo "$$" > "$tmplock"
   # ln is atomic — fails if lockfile already exists
   if ln "$tmplock" "$lockfile" 2>/dev/null; then
     # acquired lock
   else
     rm -f "$tmplock"
     # lock held by another process — retry or fail
   fi
   ```

2. Set `assigned_to` and `claimed_at` in frontmatter via Edit:
   ```yaml
   assigned_to: "{agent-name}"
   claimed_at: "2026-02-21T10:30:00Z"
   status: in_progress
   ```

3. Release lock:
   ```bash
   rm -f "$lockfile" "$tmplock"
   ```

4. Output JSON:
   ```json
   {
     "issue_id": "002",
     "priority": "p2",
     "title": "implement-auth-flow",
     "file": "todos/002-ready-p2-implement-auth-flow.md",
     "source": "work",
     "source_ref": "plans/feat-auth-plan.md",
     "files": ["src/auth.ts", "src/middleware.ts"]
   }
   ```

**Zero-state distinctions** (specific messages for each case):
- No todos at all: "No todos found."
- All complete: "All todos are complete."
- All claimed: "All ready todos are assigned. Check in-progress items."
- None ready: "No ready todos. Run `/rune:file-todos triage` to approve pending items."
- All blocked: "All ready todos are blocked by unresolved dependencies."

### search — Full-Text Search

```
/rune:file-todos search <query>
```

Search across todo titles, problem statements, and work logs for matching text.

**Steps**:

1. Validate query:
   - Non-empty: "Search requires a query. Usage: `/rune:file-todos search <query>`"
   - Min length 2 chars: "Query too short. Use at least 2 characters."
   - Max length 200 chars: "Query too long. Use at most 200 characters."
   - No null bytes: reject with error

2. Sanitize query for safe use in Grep patterns:
   - Escape regex metacharacters: `[`, `]`, `(`, `)`, `{`, `}`, `*`, `+`, `?`, `.`, `^`, `$`, `|`, `\`
   - Use the escaped pattern for case-insensitive literal search

3. Search using Grep across all todo files:

```javascript
Grep({
  pattern: sanitizedQuery,
  path: "todos/",
  glob: "[0-9][0-9][0-9]-*.md",
  output_mode: "content",
  context: 2,
  "-i": true  // case-insensitive
})
```

4. Parse results and group by file
5. For each matching file, read frontmatter to get metadata (issue_id, priority, status, source)
6. Display matches with context:

```
Search: "sql injection" (3 matches in 2 files)
-----------------------------------------------------
 #001 [P1] fix-sql-injection (pending, review)
   Line 12: Unparameterized query allows SQL injection
   Line 15: Use parameterized query with $1 placeholders

 #007 [P2] sanitize-user-input (ready, audit)
   Line 8: Input validation prevents SQL injection vectors
-----------------------------------------------------
```

**Zero-state**: "No matches found for '{query}' in todos/."

**Error states**:
- Empty query: "Search requires a query. Usage: `/rune:file-todos search <query>`"
- No todos dir: "No todos found. Nothing to search."

### archive — Move Completed Todos

```
/rune:file-todos archive [--all] [--id=NNN]
```

Move completed (and wont_fix) todos to `todos/archive/` for a cleaner working set.

**Steps**:

1. Scan `todos/` for todo files with `status: complete` or `status: wont_fix` in frontmatter
2. If `--id=NNN` specified:
   - Validate NNN against `TODO_ID_PATTERN`
   - Find the specific todo file matching that ID
   - If not found: "Todo #NNN not found."
   - Archive that specific todo (regardless of status, with confirmation)
3. If `--all` specified:
   - Archive all complete + wont_fix todos without individual confirmation
4. If neither flag:
   - Display candidates and ask for confirmation via AskUserQuestion:

```javascript
AskUserQuestion({
  questions: [{
    question: `Archive ${candidates.length} completed todos?\n${candidates.map(c => `  ${c.filename}`).join('\n')}`,
    header: "Archive",
    options: [
      { label: "Archive all", description: `Move ${candidates.length} files to todos/archive/` },
      { label: "Cancel", description: "Keep files in todos/" }
    ],
    multiSelect: false
  }]
})
```

5. Create `todos/archive/` if it does not exist:
   ```bash
   mkdir -p todos/archive
   ```

6. Move files using Bash (mv is atomic on same filesystem):
   ```bash
   mv "todos/${filename}" "todos/archive/${filename}"
   ```

7. Mark index as dirty if cache exists:
   ```bash
   touch todos/.dirty
   ```

8. Report:

```
Archive Complete
------------------------------
 Archived: 5 files
 Location: todos/archive/
------------------------------
 Remaining active: 8 todos
```

**Zero-state**: "No completed or rejected todos to archive."

## Performance: Todo Index Cache

For projects with >100 todos, implement `.todo-index.json` cache to avoid re-parsing all frontmatter on every command.

**Cache structure** (`todos/.todo-index.json`):

```json
{
  "version": 1,
  "generated": "2026-02-21T10:30:00Z",
  "count": 150,
  "entries": {
    "001": { "status": "complete", "priority": "p1", "source": "review", "assigned_to": null, "finding_id": "SEC-001" },
    "002": { "status": "ready", "priority": "p2", "source": "work", "assigned_to": null, "finding_id": "" }
  }
}
```

**Dirty signal**: Any sub-command that modifies a todo file writes `todos/.dirty` marker. On next read operation, if `.dirty` exists, rebuild the index from source files and remove `.dirty`.

**Rebuild protocol**:
1. Parse all `todos/[0-9][0-9][0-9]-*.md(N)` files
2. Extract frontmatter fields
3. Write to temp file: `todos/.todo-index.json.tmp`
4. Atomic rename: `mv todos/.todo-index.json.tmp todos/.todo-index.json`
5. Remove dirty marker: `rm -f todos/.dirty`

**Fallback**: If cache is missing or corrupt (invalid JSON), fall back to direct file parsing. Cache is an optimization, not a requirement. Never fail a command due to cache issues.

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
