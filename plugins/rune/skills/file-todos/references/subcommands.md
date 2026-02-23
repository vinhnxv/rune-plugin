# Sub-Command Implementation Details

Detailed implementation reference for file-todos sub-commands. The SKILL.md contains the summary and dispatch logic; this file provides the full implementation details.

## Validation Patterns

All user-supplied filter values MUST be validated before use:

```
STATUS_PATTERN  = /^(pending|ready|in_progress|complete|blocked|wont_fix)$/
PRIORITY_PATTERN = /^p[1-3]$/
SOURCE_PATTERN  = /^(review|work|pr-comment|tech-debt|audit)$/
TAG_PATTERN     = /^[a-zA-Z0-9_-]+$/
TODO_ID_PATTERN = /^[0-9]{3,4}$/
```

Invalid values produce a clear error message, NOT an empty list.

## Common Helpers

**parseFrontmatter(content)**: Extract YAML frontmatter from todo file content. Returns object with all frontmatter fields. Matches `^---\n([\s\S]*?)\n---` at the start of the file.

**readTodoDir()**: Scan all source subdirectories for todo files. Returns list of `{ path, source, frontmatter, title }` objects. Uses zsh-safe glob `(N)` qualifier:

```bash
# Scan all source subdirectories (work/, review/, audit/)
for f in todos/*/[0-9][0-9][0-9]-*.md(N); do
  # parse frontmatter from each file
  # derive source from parent directory name: source=$(basename "$(dirname "$f")")
done
```

**ensureTodosDir(source)**: Create source subdirectory if it does not exist: `mkdir -p todos/${source}`

**getTitle(content)**: Extract the first H1 heading from the markdown body (after frontmatter).

## create — Full Implementation

Interactive workflow for creating a new todo file.

1. Prompt user for todo details via AskUserQuestion (source determines subdirectory):
2. Ensure source subdirectory exists: `mkdir -p todos/${source}/`

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

3. Generate next sequential ID (per-subdirectory sequence):

```bash
# ID sequence is independent per source subdirectory
existing=(todos/${source}/[0-9][0-9][0-9]-*.md(N))
next_id=$(printf "%03d" $(( ${#existing[@]} + 1 )))
```

4. Compute slug from title using the canonical slugify algorithm
5. Write file to source subdirectory using the todo template
6. Set frontmatter fields: `status: pending`, `priority`, `source`, `files`, `created`, `updated` (today's date)
7. Report: "Created `todos/${source}/{filename}`"

**Zero-state**: If `todos/${source}/` does not exist, create it automatically and report the creation.

## triage — Full Implementation

Process pending todos in batch (capped at 10 per session).

1. Scan all source subdirectories: `Glob("todos/*/[0-9][0-9][0-9]-*.md")`
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

## list — Full Implementation

List todos with optional filters composing as intersection.

1. Parse filter flags from arguments:
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

3. Scan all source subdirectories: `Glob("todos/*/[0-9][0-9][0-9]-*.md")`. When `--source` is specified, narrow to `Glob("todos/${sourceFilter}/[0-9][0-9][0-9]-*.md")`

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
 review/001 [P1] fix-sql-injection          pending   review
 audit/001  [P1] add-input-validation       pending   audit
-----------------------------------------------------
 2 todos found
```

**Zero-state**: "No todos match the given filters." (when todos exist but none match) or "No todos found." (when source subdirectories are empty or missing).

## next --auto — Atomic Claim Protocol

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
     "file": "todos/work/002-ready-p2-implement-auth-flow.md",
     "source": "work",
     "source_ref": "plans/feat-auth-plan.md",
     "files": ["src/auth.ts", "src/middleware.ts"]
   }
   ```

## search — Full Implementation

Search across todo titles, problem statements, and work logs for matching text.

1. Validate query:
   - Non-empty: "Search requires a query. Usage: `/rune:file-todos search <query>`"
   - Min length 2 chars: "Query too short. Use at least 2 characters."
   - Max length 200 chars: "Query too long. Use at most 200 characters."
   - No null bytes: reject with error

2. Sanitize query for safe use in Grep patterns:
   - Escape regex metacharacters: `[`, `]`, `(`, `)`, `{`, `}`, `*`, `+`, `?`, `.`, `^`, `$`, `|`, `\`
   - Use the escaped pattern for case-insensitive literal search

3. Search using Grep across all source subdirectories:

```javascript
Grep({
  pattern: sanitizedQuery,
  path: "todos/",
  glob: "*/[0-9][0-9][0-9]-*.md",
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

## archive — Full Implementation

Move completed (and wont_fix) todos to `todos/archive/` with source prefix preserved in the filename.

1. Scan all source subdirectories for todo files with `status: complete` or `status: wont_fix` in frontmatter: `Glob("todos/*/[0-9][0-9][0-9]-*.md")`
2. If `--id=NNN` specified:
   - Validate NNN against `TODO_ID_PATTERN`
   - Search across all subdirectories for file matching that ID
   - If not found: "Todo #NNN not found."
   - Archive that specific todo (regardless of status, with confirmation)
3. If `--all` specified:
   - Archive all complete + wont_fix todos without individual confirmation
4. If `--source` specified:
   - Filter candidates to that source subdirectory only
5. If no flag:
   - Display candidates and ask for confirmation via AskUserQuestion

6. Create `todos/archive/` if it does not exist:
   ```bash
   mkdir -p todos/archive
   ```

7. Move files with source prefix preserved in archive filename:
   ```bash
   # source = basename of parent directory (e.g., "review", "work")
   # review/003-complete-p2-old-finding.md → archive/review-003-complete-p2-old-finding.md
   mv "todos/${source}/${filename}" "todos/archive/${source}-${filename}"
   ```

8. Mark index as dirty if cache exists:
   ```bash
   touch todos/.dirty
   ```

9. Report:

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
1. Parse all `todos/*/[0-9][0-9][0-9]-*.md(N)` files (scan all source subdirectories)
2. Extract frontmatter fields
3. Write to temp file: `todos/.todo-index.json.tmp`
4. Atomic rename: `mv todos/.todo-index.json.tmp todos/.todo-index.json`
5. Remove dirty marker: `rm -f todos/.dirty`

**Fallback**: If cache is missing or corrupt (invalid JSON), fall back to direct file parsing. Cache is an optimization, not a requirement. Never fail a command due to cache issues.
