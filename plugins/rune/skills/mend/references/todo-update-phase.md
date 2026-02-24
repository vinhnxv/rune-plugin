# Phase 5.9: Todo Update

Updates corresponding file-todos for resolved findings after all fixes are applied and verified. Runs only when `file_todos.enabled === true` in talisman AND todo files exist with matching `finding_id` values.

**Inputs**: `talisman` (config), `$ARGUMENTS` (for `--todos-dir`), `resolvedFindings` (from Phase 5/5.5/5.6)
**Outputs**: Updated todo file frontmatter (status, updated date) + appended Work Log entries
**Preconditions**: Phase 5.8 (Codex Fix Verification) complete, all fixes applied

**Skip conditions**: `talisman.file_todos.enabled` is not `=== true` (opt-in gate) OR no todo files found in any subdirectory OR no todo files match any resolved finding IDs.

```javascript
// Phase 5.9: Update file-todos for resolved findings
const fileTodosEnabled = talisman?.file_todos?.enabled === true  // opt-in gate (must match strive/orchestration-phases)

// CHANGED: Use resolveTodosBase (not resolveTodosDir) — mend scans ALL source subdirectories
// See integration-guide.md "Cross-Source Scanning (Mend Pattern)" for canonical pattern
const base = resolveTodosBase($ARGUMENTS, talisman)
//   standalone: "todos/"
//   arc:        "tmp/arc/{id}/todos/"  (via --todos-dir)

// CHANGED: Scan ALL subdirectories — mend is a cross-source consumer
const allTodoFiles = Glob(`${base}*/[0-9][0-9][0-9]-*.md`)
//   Matches: todos/work/001-*.md, todos/review/002-*.md, todos/audit/001-*.md
//   Or:      tmp/arc/{id}/todos/work/001-*.md, tmp/arc/{id}/todos/review/001-*.md
const todosExist = fileTodosEnabled && allTodoFiles.length > 0

if (todosExist) {
  const today = new Date().toISOString().slice(0, 10)

  // Build index: finding_id → todo file path (O(N) scan across ALL subdirectories)
  const todoIndex = new Map()
  for (const todoFile of allTodoFiles) {
    const fm = parseFrontmatter(Read(todoFile))
    if (fm.finding_id) {
      todoIndex.set(fm.finding_id, { file: todoFile, frontmatter: fm })
    }
  }

  const phaseFixerName = "mend-orchestrator"  // Phase 5.9 runs in orchestrator context, not a fixer agent
  let updatedCount = 0

  for (const finding of resolvedFindings) {
    const todoEntry = todoIndex.get(finding.id)
    if (!todoEntry) continue  // No todo file for this finding (--todos was not active)

    const { file: todoFile, frontmatter: fm } = todoEntry

    // Skip if already claimed by another mend-fixer
    if (fm.mend_fixer_claim && fm.mend_fixer_claim !== phaseFixerName) continue

    // Claim the todo for this fixer (prevents concurrent editing)
    if (!fm.mend_fixer_claim) {
      Edit(todoFile, {
        old_string: `assigned_to: ${fm.assigned_to || 'null'}`,
        new_string: `assigned_to: ${fm.assigned_to || 'null'}\nmend_fixer_claim: "${phaseFixerName}"`
      })
    }

    // Determine new status based on resolution
    let newStatus
    switch (finding.resolution) {
      case 'FIXED':
      case 'FIXED_CROSS_FILE':
        newStatus = 'complete'
        break
      case 'FALSE_POSITIVE':
        newStatus = 'wont_fix'
        break
      case 'FAILED':
      case 'SKIPPED':
        // Do not change status — leave for manual review
        newStatus = null
        break
    }

    // Update frontmatter status via Edit (NO file rename — Option A)
    if (newStatus && fm.status !== newStatus) {
      Edit(todoFile, {
        old_string: `status: ${fm.status}`,
        new_string: `status: ${newStatus}`
      })
      Edit(todoFile, {
        old_string: `updated: "${fm.updated}"`,
        new_string: `updated: "${today}"`
      })
    }

    // Append Work Log entry
    const workLogEntry = `
### ${today} - Mend Resolution

**By**: ${phaseFixerName}

**Actions**:
- Resolution: ${finding.resolution}
- ${finding.resolution === 'FIXED' ? `Fixed: ${finding.fix_summary}` : `Reason: ${finding.reason}`}
- Files: ${finding.files?.join(', ') || 'N/A'}

**Learnings**:
- ${finding.learnings || 'N/A'}
`
    // Append to end of file
    const todoContent = Read(todoFile)
    Write(todoFile, todoContent + '\n' + workLogEntry.trim() + '\n')

    updatedCount++
  }

  log(`Phase 5.9: Updated ${updatedCount} todo files from ${resolvedFindings.length} resolved findings`)
}
```

## Resolution-to-Status Mapping

| Mend Resolution | Todo Status | Rationale |
|----------------|-------------|-----------|
| `FIXED` | `complete` | Finding resolved |
| `FIXED_CROSS_FILE` | `complete` | Cross-file fix resolved |
| `FALSE_POSITIVE` | `wont_fix` | Not a real issue |
| `FAILED` | (unchanged) | Needs manual intervention |
| `SKIPPED` | (unchanged) | Blocked or deferred |
| `CONSISTENCY_FIX` | (no todo) | Doc-consistency has no todos |

**Claim lock**: The `mend_fixer_claim` frontmatter field prevents concurrent editing when two fixers work on findings in the same todo. The second fixer checks this field and skips if claimed.
