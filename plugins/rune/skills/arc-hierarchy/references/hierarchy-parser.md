# Hierarchy Parser Reference

Utility pseudocode for parsing and mutating hierarchical plan documents. Used by the `arc-hierarchy` skill orchestration loop.

---

## Artifact Type Enum

```javascript
const ARTIFACT_TYPES = {
  file:      "file",       // Physical file must exist on disk
  export:    "export",     // Named export from a module
  type:      "type",       // TypeScript type or interface
  endpoint:  "endpoint",   // HTTP route must be reachable (e.g., GET /users)
  migration: "migration"   // Database migration applied
}
```

---

## Path Validation (SEC-1)

**Inputs**: `path` — string from plan frontmatter or execution table
**Outputs**: `{ valid: boolean, reason?: string }`
**Error handling**: Returns `{ valid: false, reason: "..." }` — never throws

```javascript
function validatePlanPath(path) {
  if (!path || typeof path !== "string") {
    return { valid: false, reason: "Path must be a non-empty string" }
  }
  // Block absolute paths
  if (path.startsWith("/") || path.startsWith("~")) {
    return { valid: false, reason: "Absolute paths not allowed" }
  }
  // Block path traversal
  if (path.includes("..")) {
    return { valid: false, reason: "Path traversal (..) not allowed" }
  }
  // Allowlist: alphanumeric, dots, slashes, hyphens, underscores only
  if (!/^[a-zA-Z0-9._\/-]+$/.test(path)) {
    return { valid: false, reason: "Path contains disallowed characters" }
  }
  return { valid: true }
}
```

---

## Empty-Dependency Markers (EC-4)

Normalize em-dash `—`, en-dash `–`, and hyphen `-` as empty dependency markers when they appear as the entire dependency field.

```javascript
const EMPTY_DEP_MARKERS = new Set(["—", "–", "-", ""])

function isEmptyDependency(value) {
  return EMPTY_DEP_MARKERS.has(value.trim())
}
```

---

## parseExecutionTable(planContent)

Parse the markdown execution table from a parent plan document.

**Expected table format:**
```markdown
| Seq | Child Plan | Status | Dependencies | Started | Completed |
|-----|-----------|--------|-------------|---------|-----------|
| 01  | plans/children/01-data-layer-plan.md | pending | — | — | — |
| 02  | plans/children/02-api-plan.md | pending | 01 | — | — |
```

**Inputs**: `planContent` — full string content of the parent plan markdown file
**Outputs**: `Array<{ seq: string, path: string, status: string, dependencies: string[], started: string|null, completed: string|null }>`
**Error handling**: Returns `[]` if no table found or table is malformed. Logs a warning.

```javascript
function parseExecutionTable(planContent) {
  // Find the execution table by header row
  const tableRegex = /\|\s*Seq\s*\|.*?Child Plan.*?\|.*?Status.*?\|.*?Dependencies.*?\|[\s\S]*?(?=\n\n|\n#|\Z)/i
  const tableMatch = planContent.match(tableRegex)
  if (!tableMatch) {
    warn("parseExecutionTable: No execution table found in plan content")
    return []
  }

  const rows = tableMatch[0].split("\n").filter(line => line.trim().startsWith("|"))
  // Skip header row and separator row
  const dataRows = rows.filter(row => !row.match(/^\|\s*[-:]+\s*\|/))
    .slice(1) // skip header

  const result = []
  for (const row of dataRows) {
    const cols = row.split("|").map(c => c.trim()).filter((_, i) => i > 0)
    if (cols.length < 6) continue

    const [seq, path, status, depsRaw, started, completed] = cols

    // SEC-1: validate path from table
    const pathValidation = validatePlanPath(path)
    if (!pathValidation.valid) {
      warn(`parseExecutionTable: Skipping row with invalid path "${path}": ${pathValidation.reason}`)
      continue
    }

    // EC-4: normalize dependency markers
    const depsStr = depsRaw ? depsRaw.trim() : ""
    let dependencies = []
    if (!isEmptyDependency(depsStr)) {
      dependencies = depsStr.split(/[,\s]+/)
        .map(d => d.trim())
        .filter(d => d && !isEmptyDependency(d))
    }

    result.push({
      seq: seq.trim(),
      path: path.trim(),
      status: status.trim().toLowerCase(),
      dependencies,
      started: (started === "—" || started === "–" || started === "-" || !started.trim()) ? null : started.trim(),
      completed: (completed === "—" || completed === "–" || completed === "-" || !completed.trim()) ? null : completed.trim()
    })
  }

  return result
}
```

---

## updateExecutionTable(planContent, seq, updates)

Update a specific row in the execution table. Uses word-boundary regex to prevent `1` matching `10`, `11`, etc. (BUG-3 fix).

**Inputs**:
- `planContent` — full string content of the parent plan
- `seq` — sequence string (e.g., `"01"`, `"02"`) — must match seq column exactly
- `updates` — object with any of: `{ status?, started?, completed? }`

**Outputs**: Updated `planContent` string
**Error handling**: Returns original `planContent` unchanged if row not found. Logs a warning.

```javascript
function updateExecutionTable(planContent, seq, updates) {
  // CRITICAL (BUG-3): Use |\b or pipe-anchored boundary to prevent "1" matching "10", "11"
  // The seq appears in a pipe-delimited table column, so we anchor between pipes.
  // Pattern: `| {seq} |` where seq is exact (leading/trailing spaces trimmed)
  const lines = planContent.split("\n")
  let found = false

  const updatedLines = lines.map(line => {
    if (!line.trim().startsWith("|")) return line

    // Parse columns
    const cols = line.split("|").map(c => c.trim())
    // cols[0] = empty (before first pipe), cols[1] = seq col
    if (cols.length < 2) return line

    const rowSeq = cols[1].trim()
    // Exact match — no substring matching (BUG-3 fix)
    if (rowSeq !== seq.trim()) return line

    found = true
    // Rebuild with updates
    if (updates.status !== undefined) cols[3] = updates.status
    if (updates.started !== undefined) cols[5] = updates.started
    if (updates.completed !== undefined) cols[6] = updates.completed

    // Reconstruct the pipe-delimited row preserving spacing
    return "| " + cols.slice(1, cols.length - 1).join(" | ") + " |"
  })

  if (!found) {
    warn(`updateExecutionTable: Row with seq "${seq}" not found`)
    return planContent
  }

  return updatedLines.join("\n")
}
```

---

## findNextExecutable(executionTable)

Topological sort using Kahn's BFS algorithm. Returns the next child entry whose all dependencies are `completed`. Handles leading-zero seq strings (`"01"` vs `1`).

**CRITICAL (BUG-1)**: `partial` status MUST NOT be treated as completed. Only `"completed"` counts.

**Inputs**: `executionTable` — output from `parseExecutionTable()`
**Outputs**: Entry object `{ seq, path, status, dependencies, ... }` or `null` if none executable
**Error handling**: Returns `null` on empty table, circular dependency, or all blocked. Logs reason.

```javascript
function findNextExecutable(executionTable) {
  if (!executionTable || executionTable.length === 0) return null

  // ONLY "completed" counts — partial, failed, skipped do NOT unblock dependents (BUG-1 fix)
  const completedSeqs = new Set(
    executionTable
      .filter(e => e.status === "completed")
      .map(e => normalizeSeq(e.seq))
  )

  // Skip already-terminal entries
  const terminalStatuses = new Set(["completed", "failed", "skipped", "in-progress"])

  for (const entry of executionTable) {
    if (terminalStatuses.has(entry.status)) continue
    if (entry.status !== "pending") continue

    // Check all dependencies are completed
    const allDepsCompleted = entry.dependencies.every(dep => {
      // Handle leading-zero normalization: "01" and "1" refer to same seq (BUG-1 corollary)
      return completedSeqs.has(normalizeSeq(dep))
    })

    if (allDepsCompleted) return entry
  }

  // Check if we're stuck (non-terminal entries with unmet deps)
  const nonTerminal = executionTable.filter(e => !terminalStatuses.has(e.status) && e.status === "pending")
  if (nonTerminal.length > 0) {
    // Could be circular dependency or predecessor failed
    const failedSeqs = new Set(
      executionTable.filter(e => e.status === "failed").map(e => normalizeSeq(e.seq))
    )
    const hasFailedDeps = nonTerminal.some(e =>
      e.dependencies.some(dep => failedSeqs.has(normalizeSeq(dep)))
    )
    if (hasFailedDeps) {
      warn("findNextExecutable: Some children have failed predecessors — execution blocked")
    } else {
      warn("findNextExecutable: Possible circular dependency detected")
    }
  }

  return null
}

// Normalize seq strings: "01" -> "1", "02" -> "2" for comparison
// But preserve original for display
function normalizeSeq(seq) {
  return String(parseInt(seq, 10))
}
```

---

## parseDependencyContractMatrix(planContent)

Parse the requires/provides contract table from a parent plan document.

**Expected table format:**
```markdown
| Child | Requires | Provides |
|-------|----------|----------|
| 01-data-layer | — | file:src/models/user.ts, export:UserModel |
| 02-api | file:src/models/user.ts | file:src/routes/users.ts |
```

**Inputs**: `planContent` — full string content of the parent plan
**Outputs**: `Array<{ child: string, requires: Artifact[], provides: Artifact[] }>`
  where `Artifact = { type: string, name: string, optional?: boolean }`
**Error handling**: Returns `[]` if no contract table found. Logs a warning.

```javascript
function parseDependencyContractMatrix(planContent) {
  const tableRegex = /\|\s*Child\s*\|.*?Requires.*?\|.*?Provides.*?\|[\s\S]*?(?=\n\n|\n#|\Z)/i
  const tableMatch = planContent.match(tableRegex)
  if (!tableMatch) {
    warn("parseDependencyContractMatrix: No contract matrix table found")
    return []
  }

  const rows = tableMatch[0].split("\n").filter(line => line.trim().startsWith("|"))
  const dataRows = rows.filter(row => !row.match(/^\|\s*[-:]+\s*\|/)).slice(1)

  return dataRows.map(row => {
    const cols = row.split("|").map(c => c.trim()).filter((_, i) => i > 0)
    if (cols.length < 3) return null

    const [child, requiresRaw, providesRaw] = cols
    return {
      child: child.trim(),
      requires: parseArtifactList(requiresRaw),
      provides: parseArtifactList(providesRaw)
    }
  }).filter(Boolean)
}

// Parse comma-separated artifact list: "file:src/models/user.ts, export:UserModel"
// Optional artifact: "file:src/types/shared.ts?" (trailing ?)
function parseArtifactList(raw) {
  if (!raw || isEmptyDependency(raw)) return []

  return raw.split(",")
    .map(item => item.trim())
    .filter(Boolean)
    .map(item => {
      const optional = item.endsWith("?")
      const cleaned = optional ? item.slice(0, -1) : item
      const colonIdx = cleaned.indexOf(":")
      if (colonIdx === -1) {
        return { type: "file", name: cleaned, optional }
      }
      const type = cleaned.slice(0, colonIdx).trim()
      const name = cleaned.slice(colonIdx + 1).trim()
      if (!ARTIFACT_TYPES[type]) {
        warn(`parseArtifactList: Unknown artifact type "${type}" — treating as file`)
        return { type: "file", name: cleaned, optional }
      }
      return { type, name, optional }
    })
}
```

---

## Artifact Verification Functions

Each artifact type has a dedicated verification function.

**Inputs**: `artifact: Artifact` — from contract matrix
**Outputs**: `{ verified: boolean, reason?: string }`
**Error handling**: Always returns a result object — never throws.

```javascript
// file: Check physical file exists on disk
function verifyFileArtifact(artifact) {
  const pathValidation = validatePlanPath(artifact.name)
  if (!pathValidation.valid) {
    return { verified: false, reason: `Invalid path: ${pathValidation.reason}` }
  }
  try {
    const result = Glob(artifact.name)
    const exists = result && result.length > 0
    return { verified: exists, reason: exists ? undefined : `File not found: ${artifact.name}` }
  } catch (e) {
    return { verified: false, reason: `Glob error: ${e.message}` }
  }
}

// export: Named export from a module — check multiple export patterns including barrel re-exports
// Handles: `export { X }`, `export { X } from`, `export * from`, `export const X`, `export class X`
function verifyExportArtifact(artifact) {
  const exportName = artifact.name
  try {
    // Pattern 1: Direct named export
    const directPattern = `export\\s+(const|class|function|interface|type|enum)\\s+${escapeRegex(exportName)}`
    const directResult = Grep(directPattern, { path: "src/", glob: "**/*.{ts,js,tsx,jsx}" })

    // Pattern 2: Re-export from barrel: export { X } from / export { X, Y }
    const barrelPattern = `export\\s*\\{[^}]*\\b${escapeRegex(exportName)}\\b[^}]*\\}`
    const barrelResult = Grep(barrelPattern, { path: "src/", glob: "**/*.{ts,js,tsx,jsx}" })

    const found = (directResult && directResult.length > 0) || (barrelResult && barrelResult.length > 0)
    return {
      verified: found,
      reason: found ? undefined : `Export "${exportName}" not found in src/ (checked direct + barrel patterns)`
    }
  } catch (e) {
    return { verified: false, reason: `Grep error: ${e.message}` }
  }
}

// type: TypeScript type/interface definition
function verifyTypeArtifact(artifact) {
  const typeName = artifact.name
  try {
    const pattern = `(type|interface)\\s+${escapeRegex(typeName)}[\\s<{]`
    const result = Grep(pattern, { path: "src/", glob: "**/*.{ts,tsx}" })
    const found = result && result.length > 0
    return { verified: found, reason: found ? undefined : `Type "${typeName}" not found` }
  } catch (e) {
    return { verified: false, reason: `Grep error: ${e.message}` }
  }
}

// endpoint: HTTP route reachability (static analysis only — no HTTP calls)
// Checks for route registration in framework-agnostic patterns
function verifyEndpointArtifact(artifact) {
  const endpoint = artifact.name  // e.g., "GET /users" or "/users"
  const [method, path] = endpoint.includes(" ") ? endpoint.split(" ") : ["ANY", endpoint]
  try {
    // Check for route registration patterns: router.get('/users'), app.get('/users'), @Get('/users')
    const routePattern = `(app|router|Router)\\.(${method.toLowerCase()}|all|use)\\(['"](${escapeRegex(path)})`
    const decoratorPattern = `@(Get|Post|Put|Delete|Patch|All)\\(['"]${escapeRegex(path)}`
    const routeResult = Grep(routePattern, { path: "src/", glob: "**/*.{ts,js}" })
    const decoratorResult = Grep(decoratorPattern, { path: "src/", glob: "**/*.{ts,js}" })
    const found = (routeResult && routeResult.length > 0) || (decoratorResult && decoratorResult.length > 0)
    return { verified: found, reason: found ? undefined : `Endpoint "${endpoint}" registration not found` }
  } catch (e) {
    return { verified: false, reason: `Grep error: ${e.message}` }
  }
}

// migration: Database migration applied (checks migration file exists)
function verifyMigrationArtifact(artifact) {
  const migrationName = artifact.name
  try {
    const result = Glob(`**/migrations/**/*${migrationName}*`)
    const found = result && result.length > 0
    return { verified: found, reason: found ? undefined : `Migration file "${migrationName}" not found` }
  } catch (e) {
    return { verified: false, reason: `Glob error: ${e.message}` }
  }
}

// Dispatch to the right verifier based on artifact type
function verifyArtifact(artifact) {
  switch (artifact.type) {
    case "file":      return verifyFileArtifact(artifact)
    case "export":    return verifyExportArtifact(artifact)
    case "type":      return verifyTypeArtifact(artifact)
    case "endpoint":  return verifyEndpointArtifact(artifact)
    case "migration": return verifyMigrationArtifact(artifact)
    default:
      warn(`verifyArtifact: Unknown type "${artifact.type}" — skipping verification`)
      return { verified: true, reason: "Unknown type — skipped" }
  }
}

// Escape special regex characters in artifact names
function escapeRegex(str) {
  return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}
```
