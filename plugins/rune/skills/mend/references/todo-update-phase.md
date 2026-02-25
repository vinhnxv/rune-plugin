# Todo Update Phase — Mend Integration (v1.101.0+)

Mend updates todos in the **original review/audit session's** todo directory. This is cross-write isolation — mend does not create its own todos directory.

## Phase Position

Runs after each fixer completes a finding (between fix application and resolution report generation).

## Cross-Write Isolation Pattern

```
TOME path: tmp/reviews/{identifier}/TOME.md
                  ↓ extract outputDir
outputDir:  tmp/reviews/{identifier}/
                  ↓ resolveTodosBase()
todos_base: tmp/reviews/{identifier}/todos/
                  ↓ read per-source manifest
manifest:   tmp/reviews/{identifier}/todos/review/todos-review-manifest.json
                  ↓ match finding_id
todo file:  tmp/reviews/{identifier}/todos/review/001-pending-p1-fix-injection.md
```

Mend writes to the **review's** todo directory (not `tmp/mend/{id}/todos/`). This is intentional — mend resolves findings created by the review session, so it updates the review's todos in-place.

## Algorithm

```javascript
// Phase 5.9: Todo Update (runs after each finding is resolved)
// tomePath: string — path to TOME being processed (e.g., "tmp/arc/{id}/tome.md" or "tmp/reviews/{id}/TOME.md")
// fixing: object — { finding_id: string, fixer_name: string, resolution: "fixed"|"wont_fix"|"false_positive" }

function updateTodoForFinding(tomePath: string, fixing: {
  finding_id: string,
  fixer_name: string,
  resolution: string,
  resolution_reason: string
}): void {
  const SAFE_PATH_PATTERN = /^[a-zA-Z0-9._\-\/]+$/

  // 1. Resolve todos_base from TOME path (cross-write isolation)
  // For arc: "tmp/arc/{id}/tome.md" → outputDir = "tmp/arc/{id}/"
  // For standalone review: "tmp/reviews/{id}/TOME.md" → outputDir = "tmp/reviews/{id}/"
  const outputDir = tomePath.replace(/\/[^/]+\.md$/, '/')
  if (!SAFE_PATH_PATTERN.test(outputDir) || outputDir.includes('..')) {
    warn(`Todo update: invalid TOME path for todos_base resolution: ${tomePath}`)
    return
  }

  const todosBase = `${outputDir}todos/`

  // 2. Read per-source manifest to find matching todo
  // Try review first, then audit (mend handles both)
  let matchingTodo: object | null = null
  let todoSource: string = ''

  for (const source of ['review', 'audit']) {
    const manifestPath = `${todosBase}${source}/todos-${source}-manifest.json`
    if (!exists(manifestPath)) continue

    let manifest: { todos: Array<{ finding_id: string, file: string, status: string }> }
    try {
      manifest = JSON.parse(Read(manifestPath))
    } catch (e) {
      warn(`Todo update: failed to parse ${manifestPath}: ${e.message}`)
      continue
    }

    const found = (manifest.todos || []).find(t => t.finding_id === fixing.finding_id)
    if (found) {
      matchingTodo = found
      todoSource = source
      break
    }
  }

  if (!matchingTodo) {
    // No matching todo — todo generation may not have been active, skip silently
    return
  }

  // Reconstruct full path from filename-only manifest field + source directory
  const todoPath = `${todosBase}${todoSource}/${(matchingTodo as any).file}`
  if (!todoPath || !exists(todoPath)) {
    warn(`Todo update: matching todo file not found: ${todoPath}`)
    return
  }

  // 3. Claim lock: set mend_fixer_claim before writing (prevents concurrent edits)
  // MUST be called by orchestrator only — parallel fixer calls would create a
  // TOCTOU race on mend_fixer_claim. Mirrors status-history concurrency rule.
  const content: string = Read(todoPath)
  const fmEnd: number = content.indexOf('---', content.indexOf('---') + 3)
  if (fmEnd === -1) {
    warn(`Todo update: malformed frontmatter in ${todoPath}`)
    return
  }
  const oldFrontmatter: string = content.substring(0, fmEnd + 3)
  const parsedFm = parseFrontmatter(content)

  // Check if another fixer already claimed this todo
  if (parsedFm.mend_fixer_claim && parsedFm.mend_fixer_claim !== fixing.fixer_name) {
    warn(`Todo update: ${todoPath} already claimed by ${parsedFm.mend_fixer_claim} — skipping`)
    return
  }

  // 4. Apply frontmatter updates
  const today = new Date().toISOString().slice(0, 10)
  const nowIso = new Date().toISOString()

  // Build updated frontmatter (section-targeted edit — only modify frontmatter block)
  let newFrontmatter = oldFrontmatter
    // Claim lock
    .replace(/^mend_fixer_claim: .*$/m, `mend_fixer_claim: ${fixing.fixer_name}`)
  // If mend_fixer_claim field doesn't exist, append it before closing ---
  if (!newFrontmatter.includes('mend_fixer_claim:')) {
    newFrontmatter = newFrontmatter.replace(/\n---$/, `\nmend_fixer_claim: ${fixing.fixer_name}\n---`)
  }

  // Status and resolution fields
  newFrontmatter = newFrontmatter
    .replace(/^status: .*$/m, `status: complete`)
    .replace(/^resolution: .*$/m, `resolution: ${fixing.resolution}`)
    .replace(/^resolved_by: .*$/m, `resolved_by: ${fixing.fixer_name}`)
    .replace(/^resolved_at: .*$/m, `resolved_at: "${nowIso}"`)
    .replace(/^completed_by: .*$/m, `completed_by: ${fixing.fixer_name}`)
    .replace(/^completed_at: .*$/m, `completed_at: "${nowIso}"`)
    .replace(/^updated: .*$/m, `updated: "${today}"`)

  // Add missing v2 fields if not present
  if (!newFrontmatter.includes('resolution:')) {
    newFrontmatter = newFrontmatter.replace(/\n---$/, `\nresolution: ${fixing.resolution}\n---`)
  }
  if (!newFrontmatter.includes('resolved_by:')) {
    newFrontmatter = newFrontmatter.replace(/\n---$/, `\nresolved_by: ${fixing.fixer_name}\n---`)
  }
  if (!newFrontmatter.includes('resolved_at:')) {
    newFrontmatter = newFrontmatter.replace(/\n---$/, `\nresolved_at: "${nowIso}"\n---`)
  }
  if (!newFrontmatter.includes('completed_by:')) {
    newFrontmatter = newFrontmatter.replace(/\n---$/, `\ncompleted_by: ${fixing.fixer_name}\n---`)
  }
  if (!newFrontmatter.includes('completed_at:')) {
    newFrontmatter = newFrontmatter.replace(/\n---$/, `\ncompleted_at: "${nowIso}"\n---`)
  }

  // 5. Update resolution_reason (sanitize pipe chars to prevent table corruption)
  const safeReason = (fixing.resolution_reason || '').replace(/\|/g, '\\|').slice(0, 200)
  if (newFrontmatter.includes('resolution_reason:')) {
    newFrontmatter = newFrontmatter.replace(/^resolution_reason: .*$/m, `resolution_reason: "${safeReason}"`)
  } else {
    newFrontmatter = newFrontmatter.replace(/\n---$/, `\nresolution_reason: "${safeReason}"\n---`)
  }

  Edit(todoPath, { old_string: oldFrontmatter, new_string: newFrontmatter })

  // 6. Append workflow_chain entry (mend identifier)
  // Note: workflow_chain is a YAML array in frontmatter, append inline
  const mendEntry = `  - "mend:${fixing.fixer_name}"`
  if (content.includes('workflow_chain:')) {
    // Append to existing workflow_chain array
    // Find last entry of workflow_chain block and append after it
    const afterFm = Read(todoPath)  // Re-read after frontmatter edit
    const wfChainMatch = afterFm.match(/(workflow_chain:\n(?:  - ".*"\n)*)/)
    if (wfChainMatch) {
      Edit(todoPath, {
        old_string: wfChainMatch[0].trimEnd(),
        new_string: `${wfChainMatch[0].trimEnd()}\n${mendEntry}`
      })
    }
  }
  // If no workflow_chain, it was missing from todo template — skip (non-blocking)

  // 7. Append Status History entry
  appendStatusHistory(todoPath, parsedFm.status, 'complete', fixing.fixer_name, `${fixing.resolution}: ${safeReason}`)

  // 8. Mark source dirty for manifest rebuild
  const dirtyPath = `${todosBase}${todoSource}/.dirty`
  Write(dirtyPath, new Date().toISOString())
}
```

## Manifest Rebuild (End of Mend Phase)

After all fixers complete, rebuild the manifest to reflect updated todo statuses:

```javascript
// Called at end of mend Phase 5.9 (after all fixers complete)
function rebuildMendTodoManifests(todosBase: string): void {
  for (const source of ['review', 'audit']) {
    const dirtyPath = `${todosBase}${source}/.dirty`
    if (!exists(dirtyPath)) continue

    // Rebuild manifest for this source
    buildSourceManifest(todosBase, source)

    // Clear dirty signal after successful rebuild
    try {
      Bash(`rm -f "${dirtyPath}"`)
    } catch (e) {
      warn(`Could not clear dirty signal ${dirtyPath}: ${e.message}`)
    }
  }
}
```

## Existence Check

Only reference todo files in the mend resolution report if they actually exist. Without this guard, the report shows dangling paths when todo generation was not active during the review session:

```javascript
// In resolution report generation:
const todoRef = matchingTodo?.file
const todoExists = todoRef && exists(todoRef)
const todoLine = todoExists ? `[todo](${todoRef})` : '(no todo)'
```

## Integration with Arc Context

When mend runs within arc (TOME at `tmp/arc/{id}/tome.md`), the `outputDir` resolves to `tmp/arc/{id}/`. The cross-write isolation pattern is identical — mend still resolves `todos_base` from the TOME path, but in arc the review todos live at `tmp/arc/{id}/todos/review/` (produced by Phase 6 CODE REVIEW).

```
Arc TOME:    tmp/arc/{id}/tome.md → outputDir = tmp/arc/{id}/
todos_base:  tmp/arc/{id}/todos/
source manifest: tmp/arc/{id}/todos/review/todos-review-manifest.json
```
