# Integration Guide — Rune Workflows and File-Todos

## Overview

File-todos connect to Rune workflows as both producers (creating todos) and consumers (reading/updating todos). This document describes each integration point.

## Opt-In Requirement

All integrations require `talisman.file_todos.enabled === true`. When disabled, workflows use their existing tracking mechanisms (per-worker logs, in-memory TaskCreate, etc.).

```yaml
# .claude/talisman.yml
file_todos:
  enabled: true    # required — opt-in only
```

## .gitignore Conflict

The Rune `.gitignore` includes `todos/` on line 21, which prevents todo files from being version-controlled. This is intentional for temporary/ephemeral use.

**To persist todos in git**: Remove or comment out the `todos/` line in `.gitignore`. This is a manual opt-in step, matching the Echoes pattern where `.claude/echoes/` is gitignored by default.

**Namespace note**: `inscription.todos.dir` (relative to `output_dir`, used by strive per-worker logs) and `talisman.file_todos.dir` (relative to project root, used by file-todos skill) both default to `"todos/"` but resolve to different absolute paths. Do not confuse them.

## Integration: /rune:appraise (Review)

**Direction**: Review TOME -> File-Todos (producer)

**When**: After TOME.md is written and diff-scope tagging is complete (Phase 5.4 in Roundtable Circle).

**Config**: `talisman.file_todos.auto_generate.review` (default: `false`)

**Flow**:
1. Parse TOME.md for structured findings (`RUNE:FINDING` markers)
2. Filter out non-actionable findings:
   - Exclude `interaction="question"` findings
   - Exclude `interaction="nit"` findings
   - Exclude `FALSE_POSITIVE` findings
   - Skip pre-existing scope P2/P3 findings (keep pre-existing P1)
3. Get next sequential ID from `todos/`
4. For each actionable finding:
   - Compute slug from finding title
   - Check for existing todo with matching `finding_id` + `source_ref` (idempotency)
   - Write todo file with `source: review` template
5. Report count of generated todos

**Frontmatter mapping**:
```yaml
source: review
source_ref: "tmp/reviews/{id}/TOME.md"    # full relative path
finding_id: "SEC-001"                      # RUNE:FINDING id attribute
finding_severity: "P1"                     # from finding priority
priority: p1                               # mapped from finding severity
```

## Integration: /rune:audit (Audit)

**Direction**: Audit TOME -> File-Todos (producer)

**When**: After audit TOME.md is written (same phase as review).

**Config**: `talisman.file_todos.auto_generate.audit` (default: `false`)

**Flow**: Identical to review integration, but with `source: audit`.

## Integration: /rune:strive (Work)

**Direction**: Plan tasks -> File-Todos (producer + consumer)

**When**: During plan parsing (Phase 1) and worker execution (Phase 2+).

**Config**: `talisman.file_todos.auto_generate.work` (default: `false`)

**Flow — Production (Phase 1)**:
1. Parse plan for tasks
2. For each task:
   - Create TaskCreate entry (existing behavior, unchanged)
   - Create corresponding todo file with `source: work` template
   - Map risk tier to priority: `critical` -> `p1`, `high` -> `p2`, default -> `p3`
   - Set initial status to `ready` (work tasks are pre-triaged)
   - Include `work_session` for session correlation

**Flow — Consumption (Phase 2+)**:
1. Workers read their assigned todo file for context
2. Workers append Work Log entries as they progress
3. On completion: worker signals orchestrator, orchestrator updates `status: complete`
4. On block: worker signals orchestrator, orchestrator updates `status: blocked`

**Stale prevention**: Include `work_session` in frontmatter. Cleanup logic scopes to current session only. Check for existing `source_ref` match before creating duplicates across re-runs.

**Backward compatibility**: When `talisman.file_todos.enabled !== true`, strive uses the existing per-worker log protocol (`tmp/work/{timestamp}/todos/{worker-name}.md`).

## Integration: /rune:mend (Resolution)

**Direction**: File-Todos <- Mend fixer (consumer + updater)

**When**: After mend-fixer resolves a TOME finding.

**Flow**:
1. After fixer completes a finding, look up corresponding todo:
   - Search `todos/` for file with matching `finding_id` in frontmatter
   - If no match found, skip (todo generation may not have been active)
2. Update todo frontmatter: `status: complete`
3. Update `updated` date
4. Add Work Log entry documenting the fix:
   ```markdown
   ### {date} - Mend Resolution

   **By**: mend-fixer
   **Actions**:
   - Fixed: {fix description}
   - Files: {modified files}

   **Learnings**:
   - {resolution notes}
   ```
5. Set `mend_fixer_claim` in frontmatter to prevent concurrent editing

**Existence check**: Only link todo files in the resolution report if they actually exist. Without this guard, the report shows dangling paths when `--todos` was not active during review.

## Integration: PR Comments

**Direction**: GitHub PR comments -> File-Todos (producer)

**When**: Manual invocation or future automation.

**Flow**:
1. Fetch PR comments via `gh api`
2. Filter to actionable comments (not resolved, not bot-generated)
3. For each comment:
   - Create todo with `source: pr-comment`
   - Include PR number, comment body, file path, and line number
   - Set priority based on comment content (default: `p2`)

## Concurrency Model

### Single-Writer Principle

Only the orchestrator (Tarnished) creates and deletes todo files. Workers only append to Work Log sections of their assigned todo. This eliminates all write coordination issues.

### Claim Protocol

When a worker claims a todo:
1. Orchestrator sets `assigned_to: {worker-name}` in frontmatter
2. Orchestrator sets `status: in_progress`
3. Worker reads and appends to Work Log only
4. On completion, worker signals orchestrator (not direct file update)

### Mend Claim Lock

Mend-fixers set `mend_fixer_claim: {fixer-name}` before updating. If field is already set by another fixer, skip the update.
